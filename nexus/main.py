"""
NEXUS engine launcher.

Initializes the NexusBus and core services, wires up subscriptions, and runs
long-lived tasks concurrently.
"""

import asyncio
import logging
from typing import List

from nexus.core.bus import NexusBus
from nexus.interfaces.websocket import WebsocketInterface
from nexus.services.config import ConfigService
from nexus.services.database.service import DatabaseService
from nexus.services.llm.service import LLMService
from nexus.services.tool_executor import ToolExecutorService
from nexus.services.context import ContextService
from nexus.services.orchestrator import OrchestratorService
from nexus.services.persistence import PersistenceService
from nexus.tools.registry import ToolRegistry


def _setup_logging() -> None:
    """Configure baseline logging for the engine."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main() -> None:
    """Main entrypoint: initialize bus, services, subscriptions, and run tasks."""
    _setup_logging()
    logger = logging.getLogger("nexus.main")

    # 1) Instantiate the bus first
    bus = NexusBus()
    logger.info("NexusBus instantiated")

    # 2) Initialize core infrastructure services in dependency order
    # Create a temporary config service for database initialization
    temp_config = ConfigService()
    await temp_config.initialize()
    logger.info("Temporary ConfigService initialized")

    # 3) Initialize database service with temporary config
    database_service = DatabaseService(bus, temp_config)
    logger.info("DatabaseService initialized")

    # 4) Initialize main config service with database service
    config_service = ConfigService(database_service)
    await config_service.initialize()
    logger.info("Main ConfigService initialized with database")

    # 5) Initialize and configure tool registry
    tool_registry = ToolRegistry()

    # Auto-discover and register all tools
    tool_registry.discover_and_register('nexus.tools.definition')
    logger.info("Tools auto-discovery and registration completed")

    # 6) Instantiate services and interfaces with proper dependency injection
    # Order matters: dependencies must be created before dependents

    # Persistence service depends on database service
    persistence_service = PersistenceService(database_service)

    # Other services
    llm_service = LLMService(bus, config_service)
    tool_executor_service = ToolExecutorService(bus, tool_registry)

    # Context service now depends on config and persistence services
    context_service = ContextService(bus, tool_registry, config_service, persistence_service)

    # Orchestrator and interface services
    orchestrator_service = OrchestratorService(bus, config_service)
    websocket_interface = WebsocketInterface(bus, database_service)

    services: List[object] = [
        database_service,
        persistence_service,
        llm_service,
        tool_executor_service,
        context_service,
        orchestrator_service,
        websocket_interface,
    ]

    # 7) Wire subscriptions
    for svc in services:
        subscribe = getattr(svc, "subscribe_to_bus", None)
        if callable(subscribe):
            subscribe()
            logger.info("%s subscribed to bus", svc.__class__.__name__)

    # 8) Get server configuration from config service
    server_host = config_service.get("server.host", "127.0.0.1")
    server_port = config_service.get_int("server.port", 8000)

    # 9) Get FastAPI app from WebSocket interface
    app = await websocket_interface.run_forever(host=server_host, port=server_port)

    # 10) Long-running tasks (bus listeners)
    bus_task = asyncio.create_task(bus.run_forever(), name="nexusbus.run_forever")

    logger.info(f"NEXUS engine configured with FastAPI app at {server_host}:{server_port}")

    # 11) Import uvicorn and run the FastAPI app
    import uvicorn

    # Create a task for the uvicorn server
    config = uvicorn.Config(app, host=server_host, port=server_port, log_level="info")
    server = uvicorn.Server(config)

    # Run bus and server concurrently
    try:
        await asyncio.gather(
            bus_task,
            server.serve()
        )
    except asyncio.CancelledError:
        logger.info("Shutdown requested; cancelling tasks...")
        bus_task.cancel()
        await server.shutdown()
        # Best-effort wait for cancellations
        await asyncio.gather(bus_task, return_exceptions=True)
        logger.info("All tasks cancelled. Exiting.")


if __name__ == "__main__":
    asyncio.run(main())
