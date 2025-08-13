"""
LLM service skeleton for NEXUS.

This service will interact with pluggable LLM providers to process requests.
It registers interest in LLM request topics on the NexusBus and exposes an
async handler for future implementation.
"""

import logging
from nexus.core.bus import NexusBus
from nexus.core.models import Message

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, bus: NexusBus):
        self.bus = bus
        logger.info("LLMService Initialized")

    def subscribe_to_bus(self) -> None:
        # Example: self.bus.subscribe("topics.llm.requests", self.handle_llm_request)
        logger.info("LLMService subscribed to NexusBus")

    async def handle_llm_request(self, message: Message) -> None:
        # Future: perform LLM API invocation and publish results
        _ = message  # placeholder to avoid unused variable warnings
        return
