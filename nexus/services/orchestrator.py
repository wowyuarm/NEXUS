"""
Orchestrator service for NEXUS.

Coordinates the high-level conversational flow across context building, LLM
calls, and tool execution via the NexusBus. Manages the state machine for Runs
and implements the complete Agentic Loop with tool calling capabilities.

Key responsibilities:
- Run lifecycle management and state transitions
- Tool call detection and orchestration
- Safety valve enforcement (max iterations)
- Real-time UI event broadcasting
- History management for multi-turn tool interactions
"""

import logging
import json
from typing import Dict, List
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Run, RunStatus, Role
from nexus.core.topics import Topics
from nexus.services.config import ConfigService

logger = logging.getLogger(__name__)

# Constants for UI event standardization
UI_EVENT_TEXT_CHUNK = "text_chunk"
CONTEXT_STATUS_SUCCESS = "success"

# Constants for LLM message roles
LLM_ROLE_ASSISTANT = "assistant"
LLM_ROLE_TOOL = "tool"
LLM_ROLE_USER = "user"


class OrchestratorService:
    def __init__(self, bus: NexusBus, config_service: ConfigService):
        self.bus = bus
        self.config_service = config_service
        # Track active runs by run_id
        self.active_runs: Dict[str, Run] = {}
        # Get max tool iterations from config
        self.max_tool_iterations = config_service.get_int("system.max_tool_iterations", 5)
        logger.info("OrchestratorService initialized")

    def _extract_user_input_from_run(self, run: Run) -> str:
        """Extract user input from the first message in run history."""
        if run.history and isinstance(run.history[0].content, str):
            return run.history[0].content
        return ""

    def _parse_tool_arguments(self, raw_args) -> Dict:
        """Parse tool arguments, handling both string and dict formats."""
        if isinstance(raw_args, str):
            try:
                return json.loads(raw_args)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse tool arguments as JSON: {raw_args}")
                return {}
        return raw_args if isinstance(raw_args, dict) else {}

    def _convert_history_to_llm_messages(self, run: Run) -> List[Dict]:
        """Convert run history to LLM-compatible message format."""
        messages = []
        for hist_msg in run.history:
            if hist_msg.role == Role.AI:
                # AI message with potential tool calls
                msg_dict = {
                    "role": LLM_ROLE_ASSISTANT,
                    "content": hist_msg.content
                }
                if "tool_calls" in hist_msg.metadata:
                    msg_dict["tool_calls"] = hist_msg.metadata["tool_calls"]
                messages.append(msg_dict)
            elif hist_msg.role == Role.TOOL:
                # Tool result message
                messages.append({
                    "role": LLM_ROLE_TOOL,
                    "content": hist_msg.content,
                    "tool_call_id": hist_msg.metadata.get("call_id", ""),
                    "name": hist_msg.metadata.get("tool_name", "")
                })
            elif hist_msg.role == Role.HUMAN:
                # User message
                messages.append({
                    "role": LLM_ROLE_USER,
                    "content": hist_msg.content
                })
        return messages

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
        self.bus.subscribe(Topics.TOOLS_RESULTS, self.handle_tool_result)
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

            # Get messages and tools from context
            messages = content.get("messages", [])
            tools = content.get("tools", [])

            # Store tools in the run object
            run.tools = tools

            # Request LLM completion
            llm_request = Message(
                run_id=run_id,
                session_id=run.session_id,
                role=Role.SYSTEM,
                content={
                    "messages": messages,
                    "tools": tools
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

            # Check if there are tool calls
            if tool_calls:
                logger.info(f"Tool calls detected for run_id={run_id}: {len(tool_calls)} calls")

                # Safety valve: check iteration count
                if run.iteration_count >= self.max_tool_iterations:
                    logger.warning(f"Max tool iterations ({self.max_tool_iterations}) exceeded for run_id={run_id}")
                    run.status = RunStatus.TIMED_OUT

                    # Send error message to UI
                    error_event = Message(
                        run_id=run_id,
                        session_id=run.session_id,
                        role=Role.SYSTEM,
                        content={
                            "event": "error",
                            "run_id": run_id,
                            "payload": {
                                "message": f"Maximum tool iterations ({self.max_tool_iterations}) exceeded"
                            }
                        }
                    )
                    await self.bus.publish(Topics.UI_EVENTS, error_event)

                    # Remove timed out run
                    del self.active_runs[run_id]
                    return

                # Update run status and increment iteration count
                run.status = RunStatus.AWAITING_TOOL_RESULT
                run.iteration_count += 1

                # Record AI intent: add the LLM message with tool_calls to history
                ai_message = Message(
                    run_id=run_id,
                    session_id=run.session_id,
                    role=Role.AI,
                    content=llm_content,
                    metadata={"tool_calls": tool_calls}
                )
                run.history.append(ai_message)

                # Publish UI events for each tool call
                for tool_call in tool_calls:
                    tool_name = tool_call.get("function", {}).get("name", "unknown")
                    tool_args = tool_call.get("function", {}).get("arguments", {})

                    ui_event = Message(
                        run_id=run_id,
                        session_id=run.session_id,
                        role=Role.SYSTEM,
                        content={
                            "event": "tool_call_started",
                            "run_id": run_id,
                            "payload": {
                                "tool_name": tool_name,
                                "args": tool_args
                            }
                        }
                    )
                    await self.bus.publish(Topics.UI_EVENTS, ui_event)

                # Publish tool requests
                for tool_call in tool_calls:
                    # Parse arguments using extracted method
                    raw_args = tool_call.get("function", {}).get("arguments", {})
                    parsed_args = self._parse_tool_arguments(raw_args)

                    tool_request = Message(
                        run_id=run_id,
                        session_id=run.session_id,
                        role=Role.SYSTEM,
                        content={
                            "name": tool_call.get("function", {}).get("name"),
                            "args": parsed_args,
                            "call_id": tool_call.get("id")
                        }
                    )
                    await self.bus.publish(Topics.TOOLS_REQUESTS, tool_request)
                    logger.info(f"Published tool request for {tool_call.get('function', {}).get('name')} in run_id={run_id}")

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

    async def handle_tool_result(self, message: Message) -> None:
        """
        Handle tool execution results.

        Args:
            message: Message containing tool execution results
        """
        try:
            run_id = message.run_id
            logger.info(f"Handling tool result for run_id={run_id}")

            run = self.active_runs.get(run_id)
            if not run:
                logger.error(f"No active run found for run_id={run_id}")
                return

            content = message.content
            tool_name = content.get("tool_name", "unknown")
            tool_result = content.get("result", "")
            tool_status = content.get("status", "unknown")

            # Record tool result: add the tool message to history
            tool_message = Message(
                run_id=run_id,
                session_id=run.session_id,
                role=Role.TOOL,
                content=tool_result,
                metadata={"tool_name": tool_name, "status": tool_status}
            )
            run.history.append(tool_message)

            # Publish UI event for tool completion
            ui_event = Message(
                run_id=run_id,
                session_id=run.session_id,
                role=Role.SYSTEM,
                content={
                    "event": "tool_call_finished",
                    "run_id": run_id,
                    "payload": {
                        "tool_name": tool_name,
                        "status": tool_status,
                        "result": tool_result
                    }
                }
            )
            await self.bus.publish(Topics.UI_EVENTS, ui_event)
            logger.info(f"Published tool completion UI event for {tool_name} in run_id={run_id}")

            # Convert run history to messages format for LLM
            messages = self._convert_history_to_llm_messages(run)

            # Call LLM again with complete history
            run.status = RunStatus.AWAITING_LLM_DECISION

            llm_request = Message(
                run_id=run_id,
                session_id=run.session_id,
                role=Role.SYSTEM,
                content={
                    "messages": messages,
                    "tools": run.tools
                }
            )

            await self.bus.publish(Topics.LLM_REQUESTS, llm_request)
            logger.info(f"Published follow-up LLM request for run_id={run_id}")

        except Exception as e:
            logger.error(f"Error handling tool result for run_id={message.run_id}: {e}")
