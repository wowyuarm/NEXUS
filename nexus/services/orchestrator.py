"""
Orchestrator service for NEXUS.

Coordinates the high-level conversational flow across context building, LLM
calls, and tool execution via the NexusBus. Manages the state machine for Runs.
"""

import logging
from typing import Dict
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Run, RunStatus, Role
from nexus.core.topics import Topics

logger = logging.getLogger(__name__)

# Constants for UI event standardization
UI_EVENT_TEXT_CHUNK = "text_chunk"
CONTEXT_STATUS_SUCCESS = "success"


class OrchestratorService:
    def __init__(self, bus: NexusBus):
        self.bus = bus
        # Track active runs by run_id
        self.active_runs: Dict[str, Run] = {}
        logger.info("OrchestratorService initialized")

    def _extract_user_input_from_run(self, run: Run) -> str:
        """Extract user input from the first message in run history."""
        if run.history and isinstance(run.history[0].content, str):
            return run.history[0].content
        return ""

    def _create_standardized_ui_event(self, run_id: str, session_id: str, content: str) -> Message:
        """Create a standardized UI event message."""
        return Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.AI,
            content={
                "event": UI_EVENT_TEXT_CHUNK,
                "run_id": run_id,
                "payload": {
                    "chunk": content
                }
            }
        )

    def subscribe_to_bus(self) -> None:
        """Subscribe to orchestration topics."""
        self.bus.subscribe(Topics.RUNS_NEW, self.handle_new_run)
        self.bus.subscribe(Topics.CONTEXT_BUILD_RESPONSE, self.handle_context_ready)
        self.bus.subscribe(Topics.LLM_RESULTS, self.handle_llm_result)
        logger.info("OrchestratorService subscribed to NexusBus")

    async def handle_new_run(self, message: Message) -> None:
        """
        Handle new run requests.

        Args:
            message: Message containing Run object
        """
        try:
            logger.info(f"Handling new run for run_id={message.run_id}")

            # Extract Run object directly from message content
            run = message.content
            if not isinstance(run, Run):
                logger.error(f"Expected Run object in message content, got {type(run)}")
                return

            # Update run status to building context
            run.status = RunStatus.BUILDING_CONTEXT

            # Store the run
            self.active_runs[run.id] = run

            # Extract current input from the first message in run history
            current_input = self._extract_user_input_from_run(run)

            # Request context building
            context_request = Message(
                run_id=run.id,
                session_id=run.session_id,
                role=Role.SYSTEM,
                content={
                    "current_input": current_input,
                    "session_id": run.session_id
                }
            )

            await self.bus.publish(Topics.CONTEXT_BUILD_REQUEST, context_request)
            logger.info(f"Published context build request for run_id={run.id}")

        except Exception as e:
            logger.error(f"Error handling new run for run_id={message.run_id}: {e}")

    async def handle_context_ready(self, message: Message) -> None:
        """
        Handle context build responses.

        Args:
            message: Message containing context build results
        """
        try:
            run_id = message.run_id
            logger.info(f"Handling context ready for run_id={run_id}")

            run = self.active_runs.get(run_id)
            if not run:
                logger.error(f"No active run found for run_id={run_id}")
                return

            content = message.content
            if content.get("status") != CONTEXT_STATUS_SUCCESS:
                logger.error(f"Context build failed for run_id={run_id}")
                run.status = RunStatus.FAILED
                return

            # Update run status
            run.status = RunStatus.AWAITING_LLM_DECISION

            # Get messages from context
            messages = content.get("messages", [])

            # Request LLM completion
            llm_request = Message(
                run_id=run_id,
                session_id=run.session_id,
                role=Role.SYSTEM,
                content={
                    "messages": messages
                }
            )

            await self.bus.publish(Topics.LLM_REQUESTS, llm_request)
            logger.info(f"Published LLM request for run_id={run_id}")

        except Exception as e:
            logger.error(f"Error handling context ready for run_id={message.run_id}: {e}")

    async def handle_llm_result(self, message: Message) -> None:
        """
        Handle LLM completion results.

        Args:
            message: Message containing LLM results
        """
        try:
            run_id = message.run_id
            logger.info(f"Handling LLM result for run_id={run_id}")

            run = self.active_runs.get(run_id)
            if not run:
                logger.error(f"No active run found for run_id={run_id}")
                return

            content = message.content
            llm_content = content.get("content", "")
            tool_calls = content.get("tool_calls")

            # Check if there are tool calls (simplified logic - no tool calls for now)
            if tool_calls:
                logger.info(f"Tool calls detected for run_id={run_id}, but not implemented yet")
                # Future: handle tool calls
                run.status = RunStatus.AWAITING_TOOL_RESULT
            else:
                # No tool calls, complete the run
                run.status = RunStatus.COMPLETED

                # Create standardized UI event message
                ui_event = self._create_standardized_ui_event(
                    run_id=run_id,
                    session_id=run.session_id,
                    content=llm_content
                )

                # Publish UI event
                await self.bus.publish(Topics.UI_EVENTS, ui_event)
                logger.info(f"Published UI event for run_id={run_id}")

                # Remove completed run from active runs
                del self.active_runs[run_id]
                logger.info(f"Completed and removed run_id={run_id}")

        except Exception as e:
            logger.error(f"Error handling LLM result for run_id={message.run_id}: {e}")
