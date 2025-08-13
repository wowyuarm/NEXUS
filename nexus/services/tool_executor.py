"""
Tool Executor service skeleton for NEXUS.

Responsible for executing registered tools upon request messages received via
NexusBus. The concrete tool registry and execution will be added later.
"""

import logging
from nexus.core.bus import NexusBus

logger = logging.getLogger(__name__)


class ToolExecutorService:
    def __init__(self, bus: NexusBus):
        self.bus = bus
        logger.info("ToolExecutorService Initialized")

    def subscribe_to_bus(self) -> None:
        # Example: self.bus.subscribe("topics.tools.requests", self.handle_tool_request)
        logger.info("ToolExecutorService subscribed to NexusBus")

    async def handle_tool_request(self, message) -> None:
        # Future: dispatch to tool registry and publish results
        _ = message  # placeholder to avoid unused variable warnings
        return
