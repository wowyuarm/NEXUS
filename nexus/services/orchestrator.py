"""
Orchestrator service skeleton for NEXUS.

Coordinates the high-level conversational flow across context building, LLM
calls, and tool execution via the NexusBus.
"""

import logging
from nexus.core.bus import NexusBus

logger = logging.getLogger(__name__)


class OrchestratorService:
    def __init__(self, bus: NexusBus):
        self.bus = bus
        logger.info("OrchestratorService Initialized")

    def subscribe_to_bus(self) -> None:
        # self.bus.subscribe("topics.runs.new", self.handle_new_run)
        # self.bus.subscribe("topics.context.build_response", self.handle_context_ready)
        # self.bus.subscribe("topics.llm.results", self.handle_llm_result)
        # self.bus.subscribe("topics.tools.results", self.handle_tool_result)
        logger.info("OrchestratorService subscribed to NexusBus")
