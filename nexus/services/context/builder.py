"""
Context builder for NEXUS.

Responsible for constructing the multi-message context for LLM calls.
Implements async building with parallel data fetching.

Message structure:
1. system: CORE_IDENTITY
2. user: [CAPABILITIES]
3. user: [SHARED_MEMORY]
4. user: [FRIENDS_INFO]
5. user: [THIS_MOMENT]
"""

import logging
from typing import Any

from nexus.core.bus import NexusBus
from nexus.core.models import Message, Role, Run
from nexus.core.topics import Topics
from nexus.services.context.formatters import (
    FriendsInfoFormatter,
    MemoryFormatter,
    MomentFormatter,
)
from nexus.services.context.prompts import PromptManager
from nexus.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Default history limit
DEFAULT_HISTORY_LIMIT = 20
CONFIG_HISTORY_SIZE_KEY = "memory.history_context_size"


class ContextBuilder:
    """
    Async context builder for LLM calls.

    Constructs a multi-message context with [TAG] delimiters:
    - system: CORE_IDENTITY (NEXUS's essence)
    - user: [CAPABILITIES] (available tools)
    - user: [SHARED_MEMORY] (conversation history)
    - user: [FRIENDS_INFO] (user profile)
    - user: [THIS_MOMENT] (current input)
    """

    def __init__(
        self,
        bus: NexusBus,
        tool_registry: ToolRegistry,
        config_service=None,
        persistence_service=None,
    ):
        """
        Initialize ContextBuilder.

        Args:
            bus: NexusBus for pub/sub communication
            tool_registry: ToolRegistry for tool definitions
            config_service: Optional ConfigService for configuration
            persistence_service: Optional PersistenceService for history
        """
        self.bus = bus
        self.tool_registry = tool_registry
        self.config_service = config_service
        self.persistence_service = persistence_service
        self.prompt_manager = PromptManager(config_service)
        logger.info("ContextBuilder initialized")

    def subscribe_to_bus(self) -> None:
        """Subscribe to context build request topics."""
        self.bus.subscribe(Topics.CONTEXT_BUILD_REQUEST, self.handle_build_request)
        logger.info("ContextBuilder subscribed to NexusBus")

    async def handle_build_request(self, message: Message) -> None:
        """
        Handle context build requests from orchestrator.

        Args:
            message: Message containing Run object as content
        """
        try:
            logger.info(f"Handling context build request for run_id={message.run_id}")

            # Extract Run object from message content
            run = message.content
            if not isinstance(run, Run):
                logger.error(
                    f"Expected Run object in context build request for run_id={message.run_id}"
                )
                await self._publish_error_response(message)
                return

            # Extract user_profile from Run.metadata
            user_profile = run.metadata.get("user_profile", {}) if run.metadata else {}

            # Extract current input from Run.history (first message)
            current_input = self._extract_user_input_from_run(run)
            if not current_input:
                logger.error(
                    f"No current_input found in Run.history for run_id={run.id}"
                )
                await self._publish_error_response(message)
                return

            # Extract client timestamp from run metadata
            client_timestamp_utc = (
                run.metadata.get("client_timestamp_utc", "") if run.metadata else ""
            )
            client_timezone_offset = (
                run.metadata.get("client_timezone_offset", 0) if run.metadata else 0
            )

            # Build context messages
            messages = await self.build_context(
                owner_key=message.owner_key,
                user_profile=user_profile,
                current_input=current_input,
                current_run_id=run.id,
                timestamp_utc=client_timestamp_utc,
                timezone_offset=client_timezone_offset,
            )

            # Get tool definitions
            tools = self.tool_registry.get_all_tool_definitions()

            # Create and publish response
            response_message = Message(
                run_id=run.id,
                owner_key=message.owner_key,
                role=Role.SYSTEM,
                content={"status": "success", "messages": messages, "tools": tools},
            )

            await self.bus.publish(Topics.CONTEXT_BUILD_RESPONSE, response_message)
            logger.info(f"Published context build response for run_id={run.id}")

        except Exception as e:
            logger.error(
                f"Error handling context build request for run_id={message.run_id}: {e}"
            )
            await self._publish_error_response(message)

    async def build_context(
        self,
        owner_key: str,
        user_profile: dict[str, Any],
        current_input: str,
        current_run_id: str = "",
        timestamp_utc: str = "",
        timezone_offset: int = 0,
    ) -> list[dict[str, str]]:
        """
        Build complete context message list.

        Args:
            owner_key: User's public key for history lookup
            user_profile: User profile dict from identities
            current_input: The current human input
            current_run_id: Current run ID for deduplication
            timestamp_utc: UTC timestamp in ISO 8601 format
            timezone_offset: Client timezone offset in minutes

        Returns:
            List of message dicts for LLM:
            [
                {"role": "system", "content": CORE_IDENTITY},
                {"role": "user", "content": "[CAPABILITIES]..."},
                {"role": "user", "content": "[SHARED_MEMORY]..."},
                {"role": "user", "content": "[FRIENDS_INFO]..."},
                {"role": "user", "content": "[THIS_MOMENT]..."},
            ]
        """
        # Parallel fetch: history
        history = await self._get_history(owner_key, current_run_id)

        # Get tool definitions (sync call, wrapped if needed)
        tools = self.tool_registry.get_all_tool_definitions()

        # Build each section
        messages = [
            {"role": "system", "content": self.prompt_manager.get_core_identity()},
            {
                "role": "user",
                "content": self.prompt_manager.get_capabilities_prompt(tools),
            },
            {"role": "user", "content": MemoryFormatter.format_shared_memory(history)},
            {
                "role": "user",
                "content": FriendsInfoFormatter.format_friends_info(user_profile),
            },
            {
                "role": "user",
                "content": MomentFormatter.format_this_moment(
                    current_input=current_input,
                    timestamp_utc=timestamp_utc,
                    timezone_offset=timezone_offset,
                ),
            },
        ]

        logger.info(
            f"Built context with {len(messages)} messages for owner_key={owner_key}"
        )
        return messages

    async def _get_history(
        self, owner_key: str, current_run_id: str = ""
    ) -> list[dict[str, Any]]:
        """
        Get conversation history from persistence service.

        Args:
            owner_key: User's public key
            current_run_id: Current run ID to exclude from history

        Returns:
            List of message dicts (newest first)
        """
        if not self.persistence_service:
            logger.debug("No persistence service, returning empty history")
            return []

        try:
            # Get history limit from config
            history_limit = DEFAULT_HISTORY_LIMIT
            if self.config_service:
                history_limit = self.config_service.get_int(
                    CONFIG_HISTORY_SIZE_KEY, DEFAULT_HISTORY_LIMIT
                )

            # Retrieve historical messages
            history = await self.persistence_service.get_history(
                owner_key, history_limit
            )
            history_list: list[dict[str, Any]] = (
                history if isinstance(history, list) else []
            )

            # Filter out current run messages to prevent duplication
            if current_run_id:
                history_list = [
                    msg
                    for msg in history_list
                    if msg.get("run_id") != current_run_id
                ]

            logger.info(
                f"Retrieved {len(history_list)} history messages for owner_key={owner_key}"
            )
            return history_list

        except Exception as e:
            logger.error(f"Failed to load history for owner_key={owner_key}: {e}")
            return []

    def _extract_user_input_from_run(self, run: Run) -> str:
        """Extract user input from the first message in run history."""
        if run.history and isinstance(run.history[0].content, str):
            return run.history[0].content
        return ""

    async def _publish_error_response(self, message: Message) -> None:
        """Publish error response for failed context build."""
        error_message = Message(
            run_id=message.run_id,
            owner_key=message.owner_key,
            role=Role.SYSTEM,
            content={"status": "error", "messages": [], "tools": []},
        )
        await self.bus.publish(Topics.CONTEXT_BUILD_RESPONSE, error_message)
