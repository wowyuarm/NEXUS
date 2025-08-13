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

    # 1) Instantiate the bus
    bus = NexusBus()
    logger.info("NexusBus instantiated")

    # 2) Instantiate services and interfaces with the bus
    database_service = DatabaseService(bus)
    llm_service = LLMService(bus)
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

    # 4) Long-running tasks (bus listeners + interfaces)
    tasks = [
        asyncio.create_task(bus.run_forever(), name="nexusbus.run_forever"),
        asyncio.create_task(
            websocket_interface.run_forever(host="127.0.0.1", port=8765),
            name="websocket_interface.run_forever",
        ),
    ]

    logger.info("NEXUS engine running with %d background tasks", len(tasks))

    # 5) Run indefinitely until cancelled
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Shutdown requested; cancelling tasks...")
        for t in tasks:
            t.cancel()
        # Best-effort wait for cancellations
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All tasks cancelled. Exiting.")


if __name__ == "__main__":
    asyncio.run(main())
