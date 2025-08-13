"""
Context service skeleton for NEXUS.

Responsible for building conversational context prior to LLM calls. It subscribes
for context build requests and will publish the build outputs when ready.
"""

import logging
from nexus.core.bus import NexusBus

logger = logging.getLogger(__name__)


class ContextService:
    def __init__(self, bus: NexusBus):
        self.bus = bus
        logger.info("ContextService Initialized")

    def subscribe_to_bus(self) -> None:
        # Example: self.bus.subscribe("topics.context.build_request", self.handle_build_request)
        logger.info("ContextService subscribed to NexusBus")

    async def handle_build_request(self, message) -> None:
        # Future: assemble context from history, memory, tools
        _ = message  # placeholder to avoid unused variable warnings
        return
