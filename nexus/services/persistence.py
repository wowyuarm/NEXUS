"""
Persistence service for NEXUS.

This service subscribes to key events on the NexusBus and persists 
messages to the database for conversation history. It acts as the bridge between
the event-driven system and the persistent storage layer.

Key features:
- Selective persistence: Only persists messages from validated members (users who
  passed the identity gatekeeper in OrchestratorService)
- Multi-role message handling: Persists human inputs, AI responses, and tool results
- Context build integration: Listens to CONTEXT_BUILD_REQUEST (post-gatekeeper)
  to ensure only member messages are saved
- Streaming-aware: Skips intermediate streaming events and only persists final
  AI responses and tool results
- History retrieval: Provides async interface for loading recent conversation
  history for context building (short-term memory)

Key classes:
- PersistenceService: Main service handling message persistence
"""

import logging
from typing import Dict, Any

from nexus.core.models import Message, Role
from nexus.core.topics import Topics
from nexus.services.database.service import DatabaseService

logger = logging.getLogger(__name__)


class PersistenceService:
    """Service responsible for persisting messages for conversation history.

    This service subscribes to key topics on the NexusBus and automatically
    persists important messages (user inputs, AI responses, tool results) to
    the database for future context building and conversation history.
    """

    def __init__(self, database_service: DatabaseService):
        """Initialize PersistenceService.

        Args:
            database_service: The DatabaseService instance for data operations
        """
        self.database_service = database_service
        logger.info("PersistenceService initialized")

    def subscribe_to_bus(self) -> None:
        """Subscribe to relevant topics on the NexusBus."""
        bus = self.database_service.bus

        # Subscribe to context build requests (only triggered for validated members)
        # This ensures we only persist messages from users who passed the identity gate
        bus.subscribe(Topics.CONTEXT_BUILD_REQUEST, self.handle_context_build_request)

        # Subscribe to LLM results (captures AI responses and tool call intents)
        bus.subscribe(Topics.LLM_RESULTS, self.handle_llm_result)

        # Subscribe to tool results (captures tool execution outcomes)
        bus.subscribe(Topics.TOOLS_RESULTS, self.handle_tool_result)

        logger.info("PersistenceService subscribed to NexusBus topics")

    async def _persist_message(self, message: Message, message_type: str) -> None:
        """Common method to persist a message and log the result.

        Args:
            message: The Message object to persist
            message_type: Type description for logging (e.g., "human", "AI", "tool")
        """
        success = await self.database_service.insert_message_async(message)
        if success:
            logger.info(f"Successfully persisted {message_type} message: msg_id={message.id}")
        else:
            logger.error(f"Failed to persist {message_type} message: msg_id={message.id}")

    def _extract_user_input_from_run(self, run_obj) -> tuple[str, str]:
        """Extract user input and status from Run object or dict.

        Args:
            run_obj: Run object or dictionary containing run data

        Returns:
            Tuple of (user_input, run_status)

        Raises:
            ValueError: If run_obj format is invalid
        """
        if hasattr(run_obj, 'history') and run_obj.history:
            # It's a Run object, extract the first human message from history
            first_message = run_obj.history[0]
            user_input = first_message.content
            run_status = run_obj.status.value if hasattr(run_obj.status, 'value') else str(run_obj.status)
            return user_input, run_status
        elif isinstance(run_obj, dict):
            # It's a dict format
            user_input = run_obj.get("user_input", "")
            run_status = run_obj.get("status", "unknown")
            return user_input, run_status
        else:
            raise ValueError(f"Invalid run data format: {type(run_obj)}")

    async def handle_context_build_request(self, message: Message) -> None:
        """Handle context build requests and persist the initial human message.
        
        This method is triggered only for validated members who passed the identity gate,
        ensuring we don't persist messages from unregistered visitors.

        Args:
            message: Message containing the Run object with user input
        """
        try:
            logger.info(f"Persisting human message for validated member: run_id={message.run_id}")

            # Extract user input and status from run data
            try:
                user_input, run_status = self._extract_user_input_from_run(message.content)
            except ValueError as e:
                logger.error(f"Invalid run data format in new run message: {e}")
                return

            # Trust OrchestratorService gatekeeper - if we received this message, user is a verified member
            # No identity check needed here as Orchestrator already validated member status

            # Create a message representing the human input
            human_message = Message(
                run_id=message.run_id,
                owner_key=message.owner_key,
                role=Role.HUMAN,
                content=user_input,
                metadata={
                    "source": "new_run",
                    "run_status": run_status
                }
            )

            # Persist the human message
            await self._persist_message(human_message, "human")

        except Exception as e:
            logger.error(f"Error handling new run for persistence: {e}")

    async def handle_llm_result(self, message: Message) -> None:
        """Handle LLM result events and persist AI responses.

        Args:
            message: Message containing LLM response data
        """
        try:
            logger.info(f"Handling LLM result for persistence: run_id={message.run_id}")

            # Skip SYSTEM role messages (these are streaming events, not final results)
            if message.role == Role.SYSTEM:
                logger.debug(f"Skipping SYSTEM role message (streaming event): run_id={message.run_id}")
                return

            content = message.content
            if not isinstance(content, dict):
                logger.error(f"Invalid LLM result format: {type(content)}")
                return

            # Create a message representing the AI response
            ai_content = content.get("content", "")
            # Handle None content (when LLM only makes tool calls)
            if ai_content is None:
                ai_content = ""

            # Skip empty content messages (these are intermediate streaming chunks)
            if not ai_content and not content.get("tool_calls"):
                logger.debug(f"Skipping empty content message: run_id={message.run_id}")
                return

            ai_message = Message(
                run_id=message.run_id,
                owner_key=message.owner_key,
                role=Role.AI,
                content=ai_content,
                metadata={
                    "source": "llm_result",
                    "tool_calls": content.get("tool_calls", []),
                    "has_tool_calls": bool(content.get("tool_calls"))
                }
            )

            # Persist the AI message
            await self._persist_message(ai_message, "AI")

        except Exception as e:
            logger.error(f"Error handling LLM result for persistence: {e}")

    async def handle_tool_result(self, message: Message) -> None:
        """Handle tool result events and persist tool execution outcomes.

        Args:
            message: Message containing tool execution result
        """
        try:
            logger.info(f"Handling tool result for persistence: run_id={message.run_id}")

            content = message.content
            if not isinstance(content, dict):
                logger.error(f"Invalid tool result format: {type(content)}")
                return

            # Skip empty tool results
            tool_result = content.get("result", "")
            if not tool_result:
                logger.debug(f"Skipping empty tool result: run_id={message.run_id}, tool={content.get('tool_name', 'unknown')}")
                return

            # Create a message representing the tool result
            tool_message = Message(
                run_id=message.run_id,
                owner_key=message.owner_key,
                role=Role.TOOL,
                content=tool_result,
                metadata={
                    "source": "tool_result",
                    "tool_name": content.get("tool_name", "unknown"),
                    "status": content.get("status", "unknown"),
                    "execution_success": content.get("status") == "success",
                    "call_id": content.get("call_id", "")
                }
            )

            # Persist the tool message
            await self._persist_message(tool_message, "tool")

        except Exception as e:
            logger.error(f"Error handling tool result for persistence: {e}")

    async def get_history(self, owner_key: str, limit: int = 20) -> list[Dict[str, Any]]:
        """Retrieve recent conversation history for an owner (user identity).

        This method provides a convenient interface for other services
        to access recent conversation history (short-term memory) for context building.
        It retrieves the most recent messages up to the specified limit.

        Args:
            owner_key: The owner's public key to retrieve history for
            limit: Maximum number of recent messages to return (default: 20)

        Returns:
            List of message dictionaries sorted by timestamp (newest first)
        """
        try:
            messages = await self.database_service.get_history_by_owner_key(owner_key, limit)
            logger.info(f"Retrieved {len(messages)} messages for owner_key={owner_key}")
            return messages

        except Exception as e:
            logger.error(f"Error retrieving history for owner_key={owner_key}: {e}")
            return []

    async def run_forever(self) -> None:
        """Run background tasks if any (idle for now)."""
        # PersistenceService is event-driven and doesn't need background tasks
        return