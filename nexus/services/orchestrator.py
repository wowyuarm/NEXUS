"""
Orchestrator service for NEXUS.

Coordinates the high-level conversational flow across context building, LLM
calls, and tool execution via the NexusBus. Manages the state machine for Runs
and implements the complete Agentic Loop with tool calling capabilities.

Key responsibilities:
- Run lifecycle management and state transitions
- Tool call detection and orchestration with multi-tool synchronization
- Safety valve enforcement (max iterations)
- History management for multi-turn tool interactions
- Synchronization of multiple concurrent tool executions

Note: During streaming, LLMService publishes interim events (text_chunk,
tool_call_started) to Topics.LLM_RESULTS. Orchestrator forwards them to
Topics.UI_EVENTS to preserve ordering and a single UI gateway.
"""

import logging
import os
import json
from typing import Dict, List
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Run, RunStatus, Role
from nexus.core.topics import Topics
from nexus.services.config import ConfigService

logger = logging.getLogger(__name__)

# Constants for UI event standardization
UI_EVENT_TEXT_CHUNK = "text_chunk"
UI_EVENT_RUN_STARTED = "run_started"
UI_EVENT_RUN_FINISHED = "run_finished"
UI_EVENT_TOOL_CALL_STARTED = "tool_call_started"
UI_EVENT_TOOL_CALL_FINISHED = "tool_call_finished"
CONTEXT_STATUS_SUCCESS = "success"

# Constants for LLM message roles
LLM_ROLE_ASSISTANT = "assistant"
LLM_ROLE_TOOL = "tool"
LLM_ROLE_USER = "user"


class OrchestratorService:
    def __init__(self, bus: NexusBus, config_service: ConfigService, identity_service=None):
        self.bus = bus
        self.config_service = config_service
        self.identity_service = identity_service
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
                # Coerce content to a string (empty string if None) per OpenAI-compatible schema
                assistant_content = hist_msg.content
                if not isinstance(assistant_content, str):
                    assistant_content = "" if assistant_content is None else str(assistant_content)
                msg_dict = {
                    "role": LLM_ROLE_ASSISTANT,
                    "content": assistant_content
                }
                # Normalize tool_calls schema: ensure function.arguments is a JSON string
                if "tool_calls" in hist_msg.metadata:
                    normalized_tool_calls = []
                    for tc in hist_msg.metadata["tool_calls"] or []:
                        function_obj = tc.get("function", {}) if isinstance(tc, dict) else {}
                        args = function_obj.get("arguments")
                        # arguments must be a JSON string per OpenAI-compatible schema
                        if isinstance(args, (dict, list)):
                            try:
                                args_str = json.dumps(args, ensure_ascii=False)
                            except Exception:
                                args_str = json.dumps({"_raw": str(args)})
                        elif isinstance(args, str):
                            args_str = args
                        else:
                            args_str = json.dumps({})

                        normalized_tool_calls.append({
                            "id": tc.get("id", "") if isinstance(tc, dict) else "",
                            "type": tc.get("type", "function") if isinstance(tc, dict) else "function",
                            "function": {
                                "name": function_obj.get("name", ""),
                                "arguments": args_str,
                            },
                        })
                    msg_dict["tool_calls"] = normalized_tool_calls
                messages.append(msg_dict)
            elif hist_msg.role == Role.TOOL:
                # Tool result message
                content_value = hist_msg.content
                if not isinstance(content_value, str):
                    try:
                        content_value = json.dumps(content_value, ensure_ascii=False)
                    except Exception:
                        content_value = str(content_value)

                # Per OpenAI-compatible schema for tool messages, include content and tool_call_id only
                # Note: Some providers (e.g., Google's OpenAI-compatible endpoint) also require the tool 'name'
                # to properly map to their native function_response schema. We include it when available.
                messages.append({
                    "role": LLM_ROLE_TOOL,
                    "content": content_value,
                    "tool_call_id": hist_msg.metadata.get("call_id", ""),
                    "name": hist_msg.metadata.get("tool_name", "unknown") or "unknown"
                })
            elif hist_msg.role == Role.HUMAN:
                # User message
                messages.append({
                    "role": LLM_ROLE_USER,
                    "content": hist_msg.content
                })
        return messages

    def _create_standardized_ui_event(self, run_id: str, owner_key: str, content: str) -> Message:
        """Create a standardized UI event message."""
        return Message(
            run_id=run_id,
            owner_key=owner_key,
            role=Role.AI,
            content={
                "event": UI_EVENT_TEXT_CHUNK,
                "run_id": run_id,
                "payload": {
                    "chunk": content
                }
            }
        )

    def _create_ui_event(self, run_id: str, owner_key: str, event_type: str, payload: dict) -> Message:
        """
        Create a generic UI event message with specified event type and payload.

        Args:
            run_id: The run identifier
            owner_key: The owner's public key (user identity)
            event_type: The UI event type (e.g., 'run_started', 'tool_call_finished')
            payload: The event-specific payload data

        Returns:
            Message: A properly formatted UI event message
        """
        return Message(
            run_id=run_id,
            owner_key=owner_key,
            role=Role.SYSTEM,
            content={
                "event": event_type,
                "run_id": run_id,
                "payload": payload
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
        Handle new run requests with identity-based gatekeeper logic.

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

            # === GATEKEEPER LOGIC: Identity Verification ===
            # Check if user is registered (member) or unregistered (visitor)
            if self.identity_service:
                identity = await self.identity_service.get_identity(run.owner_key)
                
                if identity is None:
                    # Visitor flow: Send guidance message and halt
                    logger.info(f"Unregistered user (visitor) detected for owner_key={run.owner_key}, sending guidance")
                    
                    guidance_message = self._create_ui_event(
                        run_id=run.id,
                        owner_key=run.owner_key,
                        event_type=UI_EVENT_TEXT_CHUNK,
                        payload={
                            # Use standardized key expected by frontend protocol
                            "chunk": "欢迎！您当前处于访客模式。要创建您的专属身份并启用个性化功能，请执行 `/identity` 指令。",
                            "is_final": True,
                            # Hint UI to render this as a system message
                            "role": "SYSTEM"
                        }
                    )
                    await self.bus.publish(Topics.UI_EVENTS, guidance_message)
                    
                    # Publish run_finished event to close the run
                    run_finished_event = self._create_ui_event(
                        run_id=run.id,
                        owner_key=run.owner_key,
                        event_type=UI_EVENT_RUN_FINISHED,
                        payload={"status": "visitor_guidance_sent"}
                    )
                    await self.bus.publish(Topics.UI_EVENTS, run_finished_event)
                    logger.info(f"Visitor guidance sent for run_id={run.id}, halting normal flow")
                    return
                
                logger.info(f"Registered user (member) verified for owner_key={run.owner_key}")
            
            # === MEMBER FLOW: Continue normal processing ===
            # Publish run_started UI event
            run_started_event = self._create_ui_event(
                run_id=run.id,
                owner_key=run.owner_key,
                event_type=UI_EVENT_RUN_STARTED,
                payload={
                    "owner_key": run.owner_key,
                    "user_input": self._extract_user_input_from_run(run)
                }
            )
            await self.bus.publish(Topics.UI_EVENTS, run_started_event)
            logger.info(f"Published run_started UI event for run_id={run.id}")

            # Update run status to building context
            run.status = RunStatus.BUILDING_CONTEXT

            # Store the run
            self.active_runs[run.id] = run

            # Extract current input from the first message in run history
            current_input = self._extract_user_input_from_run(run)

            # Extract client timestamp from run metadata
            client_timestamp_utc = run.metadata.get("client_timestamp_utc", "") if run.metadata else ""
            client_timezone_offset = run.metadata.get("client_timezone_offset", 0) if run.metadata else 0

            # Request context building
            context_request = Message(
                run_id=run.id,
                owner_key=run.owner_key,
                role=Role.SYSTEM,
                content={
                    "current_input": current_input,
                    "owner_key": run.owner_key,
                    "client_timestamp_utc": client_timestamp_utc,
                    "client_timezone_offset": client_timezone_offset,
                    "run_id": run.id
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
                owner_key=run.owner_key,
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

            # Forward interim streaming events (text_chunk, tool_call_started) to UI as-is
            if isinstance(content, dict) and content.get("event") in {UI_EVENT_TEXT_CHUNK, UI_EVENT_TOOL_CALL_STARTED}:
                ui_event = Message(
                    run_id=run_id,
                    owner_key=run.owner_key,
                    role=Role.SYSTEM,
                    content=content,
                )
                await self.bus.publish(Topics.UI_EVENTS, ui_event)
                logger.info(f"Forwarded streaming event '{content.get('event')}' for run_id={run_id} to UI")
                return

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
                        owner_key=run.owner_key,
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

                    # Publish run_finished UI event for timed out run
                    run_finished_event = self._create_ui_event(
                        run_id=run_id,
                        owner_key=run.owner_key,
                        event_type=UI_EVENT_RUN_FINISHED,
                        payload={"status": "timed_out"}
                    )
                    await self.bus.publish(Topics.UI_EVENTS, run_finished_event)
                    logger.info(f"Published run_finished UI event for timed out run_id={run_id}")

                    # Remove timed out run
                    del self.active_runs[run_id]
                    return

                # Record pending tool calls count for synchronization
                run.metadata['pending_tool_calls'] = len(tool_calls)
                logger.info(f"Set pending_tool_calls to {len(tool_calls)} for run_id={run_id}")

                # Update run status and increment iteration count
                run.status = RunStatus.AWAITING_TOOL_RESULT
                run.iteration_count += 1

                # Record AI intent: add the LLM message with tool_calls to history
                ai_message = Message(
                    run_id=run_id,
                    owner_key=run.owner_key,
                    role=Role.AI,
                    content=llm_content,
                    metadata={"tool_calls": tool_calls}
                )
                run.history.append(ai_message)

                # Note: LLMService already sent text_chunk events AND tool_call_started events during streaming
                # No need to publish tool_call_started events here - they were already sent in real-time

                # Publish tool requests
                for tool_call in tool_calls:
                    # Parse arguments using extracted method
                    raw_args = tool_call.get("function", {}).get("arguments", {})
                    parsed_args = self._parse_tool_arguments(raw_args)

                    tool_request = Message(
                        run_id=run_id,
                        owner_key=run.owner_key,
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

                # Note: LLMService already sent text_chunk events for llm_content during streaming
                # Just publish run_finished UI event
                run_finished_event = self._create_ui_event(
                    run_id=run_id,
                    owner_key=run.owner_key,
                    event_type=UI_EVENT_RUN_FINISHED,
                    payload={"status": "completed"}
                )
                await self.bus.publish(Topics.UI_EVENTS, run_finished_event)
                logger.info(f"Published run_finished UI event for run_id={run_id}")

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
            call_id = content.get("call_id", "")

            # Publish tool_call_finished UI event
            tool_finished_event = self._create_ui_event(
                run_id=run_id,
                owner_key=run.owner_key,
                event_type=UI_EVENT_TOOL_CALL_FINISHED,
                payload={
                    "tool_name": tool_name,
                    "status": "success" if tool_status == "success" else "error",
                    "result": tool_result
                }
            )
            await self.bus.publish(Topics.UI_EVENTS, tool_finished_event)
            logger.info(f"Published tool_call_finished UI event for {tool_name} in run_id={run_id}")

            # Record tool result: add the tool message to history
            tool_message = Message(
                run_id=run_id,
                owner_key=run.owner_key,
                role=Role.TOOL,
                content=tool_result,
                metadata={"tool_name": tool_name, "status": tool_status, "call_id": call_id}
            )
            run.history.append(tool_message)



            # Synchronization logic: decrement pending tool calls count
            current_pending_count = run.metadata.get('pending_tool_calls', 0)
            if current_pending_count > 0:
                run.metadata['pending_tool_calls'] = current_pending_count - 1
                remaining_tool_calls = run.metadata['pending_tool_calls']
                logger.info(f"Decremented pending_tool_calls to {remaining_tool_calls} for run_id={run_id}")

                # Only proceed to call LLM when all tools have completed
                if remaining_tool_calls > 0:
                    logger.info(f"Waiting for {remaining_tool_calls} more tool results for run_id={run_id}")
                    return

            # All tools completed, proceed with LLM call
            logger.info(f"All tools completed for run_id={run_id}, calling LLM")

            # Convert run history to messages format for LLM
            messages = self._convert_history_to_llm_messages(run)

            # Call LLM again with complete history
            run.status = RunStatus.AWAITING_LLM_DECISION

            # 当处于 E2E 假 LLM（NEXUS_E2E_FAKE_LLM=1）时，为避免循环，只传空工具列表；
            # 否则在正常环境保留可用工具以支持连续工具调用。
            tools_for_followup = [] if os.getenv("NEXUS_E2E_FAKE_LLM", "0") == "1" else run.tools

            llm_request = Message(
                run_id=run_id,
                owner_key=run.owner_key,
                role=Role.SYSTEM,
                content={
                    "messages": messages,
                    "tools": tools_for_followup
                }
            )

            await self.bus.publish(Topics.LLM_REQUESTS, llm_request)
            logger.info(f"Published follow-up LLM request for run_id={run_id}")

        except Exception as e:
            logger.error(f"Error handling tool result for run_id={message.run_id}: {e}")
