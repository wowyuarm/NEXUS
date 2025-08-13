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

    # 1) Initialize configuration service first
    config_service = ConfigService()
    config_service.initialize()
    logger.info("ConfigService initialized")

    # 2) Instantiate the bus
    bus = NexusBus()
    logger.info("NexusBus instantiated")

    # 3) Instantiate services and interfaces with the bus and config
    database_service = DatabaseService(bus)
    llm_service = LLMService(bus, config_service)
    tool_executor_service = ToolExecutorService(bus)
    context_service = ContextService(bus)
    orchestrator_service = OrchestratorService(bus)
    websocket_interface = WebsocketInterface(bus)

    services: List[object] = [
        database_service,
        llm_service,
        tool_executor_service,
        context_service,
        orchestrator_service,
        websocket_interface,
    ]

    # 3) Wire subscriptions
    for svc in services:
        subscribe = getattr(svc, "subscribe_to_bus", None)
        if callable(subscribe):
            subscribe()
            logger.info("%s subscribed to bus", svc.__class__.__name__)

    # 4) Get server configuration from config service
    server_host = config_service.get("server.host", "127.0.0.1")
    server_port = config_service.get_int("server.port", 8765)

    # 5) Get FastAPI app from WebSocket interface
    app = await websocket_interface.run_forever(host=server_host, port=server_port)

    # 6) Long-running tasks (bus listeners)
    bus_task = asyncio.create_task(bus.run_forever(), name="nexusbus.run_forever")

    logger.info(f"NEXUS engine configured with FastAPI app at {server_host}:{server_port}")

    # 7) Import uvicorn and run the FastAPI app
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
