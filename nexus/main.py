"""
NEXUS engine launcher.

Initializes the NexusBus and core services, wires up subscriptions, and runs
long-lived tasks concurrently.
"""

import asyncio
import logging
import os
from typing import List

from nexus.core.bus import NexusBus
from nexus.interfaces.websocket import WebsocketInterface
from nexus.services.config import ConfigService
from nexus.services.database.service import DatabaseService
from dotenv import load_dotenv
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

    # 2) Load environment variables from .env file
    load_dotenv()
    logger.info("Environment variables loaded from .env file")

    # 3) Get database configuration from environment
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("MONGO_DB_NAME", "NEXUS_DB_DEV")
    
    if not mongo_uri:
        logger.error("MONGO_URI not found in environment variables. Please check your .env file.")
        return
    
    logger.info(f"Database configuration loaded - URI: {mongo_uri[:20]}..., DB: {db_name}")

    # 4) Initialize and connect to database
    logger.info("Initializing database service...")
    database_service = DatabaseService(bus, mongo_uri, db_name)
    
    logger.info("Connecting to database...")
    if not database_service.connect():
        logger.error("Failed to connect to database. Please check your MongoDB instance and MONGO_URI configuration.")
        return
    logger.info("Database connection established successfully")

    # 5) Initialize config service with database service
    logger.info("Initializing configuration service...")
    config_service = ConfigService(database_service)
    await config_service.initialize()
    logger.info("Configuration service initialized successfully")

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
