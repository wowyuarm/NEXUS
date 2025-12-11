"""
SSE (Server-Sent Events) interface for NEXUS.

Provides HTTP + SSE endpoints for real-time communication.
This interface handles:
- Chat streaming responses via POST /chat
- Persistent event stream via GET /stream/{public_key}
- Command execution via POST /commands/execute (in rest.py)

Architecture:
- Chat requests return SSE streams directly from the POST response
- Persistent streams are used for connection_state and proactive events
- All UI events flow through the NexusBus subscription system
"""

import asyncio
import json
import logging
import uuid
from typing import Any

from nexus.core.bus import NexusBus
from nexus.core.models import Message, Role, Run, RunStatus
from nexus.core.topics import Topics

logger = logging.getLogger(__name__)


class SSEInterface:
    """
    Server-Sent Events interface for NEXUS.

    Handles real-time communication between AURA frontend and NEXUS backend
    using HTTP + SSE instead of WebSocket.

    Key responsibilities:
    - Subscribe to UI_EVENTS and route them to active SSE streams
    - Manage active chat streams (one per run_id)
    - Manage persistent streams (one per public_key) for connection_state
    """

    def __init__(
        self, bus: NexusBus, database_service: Any, identity_service: Any | None = None
    ):
        """
        Initialize SSE interface.

        Args:
            bus: NexusBus instance for event communication
            database_service: Database service for persistence
            identity_service: Identity service for visitor/member detection
        """
        self.bus = bus
        self.database_service = database_service
        self.identity_service = identity_service

        # Active chat streams: run_id -> asyncio.Queue
        # Each chat request creates a queue that receives UI events for that run
        self.active_chat_streams: dict[str, asyncio.Queue] = {}

        # Active persistent streams: public_key -> asyncio.Queue
        # Used for connection_state and proactive events
        self.active_persistent_streams: dict[str, asyncio.Queue] = {}

        logger.info("SSEInterface initialized")

    def subscribe_to_bus(self) -> None:
        """Subscribe to relevant bus topics for UI event routing."""
        self.bus.subscribe(Topics.UI_EVENTS, self.handle_ui_event)
        self.bus.subscribe(Topics.COMMAND_RESULT, self.handle_command_result)
        logger.info("SSEInterface subscribed to UI_EVENTS and COMMAND_RESULT")

    async def handle_ui_event(self, message: Message) -> None:
        """
        Handle UI events and route them to the appropriate SSE stream.

        UI events are routed to the chat stream for the specific run_id.

        Args:
            message: Message containing UI event data
        """
        try:
            run_id = message.run_id
            content = message.content

            logger.debug(f"SSE: Handling UI event for run_id={run_id}")

            # Route to active chat stream if exists
            if run_id in self.active_chat_streams:
                await self.active_chat_streams[run_id].put(content)
                logger.debug(f"SSE: Routed UI event to chat stream for run_id={run_id}")
            else:
                logger.debug(f"SSE: No active chat stream for run_id={run_id}")

        except Exception as e:
            logger.error(f"SSE: Error handling UI event: {e}")

    async def handle_command_result(self, message: Message) -> None:
        """
        Handle command results and route them to the appropriate SSE stream.

        Command results are sent to the persistent stream for the owner.

        Args:
            message: Message containing command result data
        """
        try:
            owner_key = message.owner_key
            run_id = message.run_id
            content = message.content

            logger.debug(f"SSE: Handling command result for owner_key={owner_key}")

            # Get original command from metadata
            meta = getattr(message, "metadata", {}) or {}
            raw_cmd = meta.get("command")
            if isinstance(raw_cmd, dict):
                cmd_str = raw_cmd.get("command", "")
            else:
                cmd_str = str(raw_cmd or "")
            if cmd_str and not cmd_str.startswith("/"):
                cmd_str = "/" + cmd_str

            # Wrap payload
            event = {
                "event": "command_result",
                "run_id": run_id,
                "payload": {"command": cmd_str, "result": content},
            }

            # Route to persistent stream if exists
            if owner_key in self.active_persistent_streams:
                await self.active_persistent_streams[owner_key].put(event)
                logger.debug(
                    f"SSE: Routed command result to persistent stream for owner_key={owner_key}"
                )
            else:
                logger.debug(
                    f"SSE: No active persistent stream for owner_key={owner_key}"
                )

        except Exception as e:
            logger.error(f"SSE: Error handling command result: {e}")

    def register_chat_stream(self, run_id: str) -> asyncio.Queue:
        """
        Register a new chat stream for a run.

        Args:
            run_id: The run ID for this chat stream

        Returns:
            asyncio.Queue that will receive UI events for this run
        """
        queue: asyncio.Queue = asyncio.Queue()
        self.active_chat_streams[run_id] = queue
        logger.info(f"SSE: Registered chat stream for run_id={run_id}")
        return queue

    def unregister_chat_stream(self, run_id: str) -> None:
        """
        Unregister a chat stream when the run completes.

        Args:
            run_id: The run ID to unregister
        """
        if run_id in self.active_chat_streams:
            del self.active_chat_streams[run_id]
            logger.info(f"SSE: Unregistered chat stream for run_id={run_id}")

    def register_persistent_stream(self, public_key: str) -> asyncio.Queue:
        """
        Register a persistent stream for a user.

        Args:
            public_key: The user's public key

        Returns:
            asyncio.Queue that will receive events for this user
        """
        queue: asyncio.Queue = asyncio.Queue()
        self.active_persistent_streams[public_key] = queue
        logger.info(
            f"SSE: Registered persistent stream for public_key={public_key[:10]}..."
        )
        return queue

    def unregister_persistent_stream(self, public_key: str) -> None:
        """
        Unregister a persistent stream.

        Args:
            public_key: The user's public key
        """
        if public_key in self.active_persistent_streams:
            del self.active_persistent_streams[public_key]
            logger.info(
                f"SSE: Unregistered persistent stream for public_key={public_key[:10]}..."
            )

    async def create_run_and_publish(
        self,
        owner_key: str,
        user_input: str,
        client_timestamp_utc: str = "",
        client_timezone_offset: int = 0,
    ) -> str:
        """
        Create a new Run and publish it to the bus.

        This is called when a chat request comes in via POST /chat.

        Args:
            owner_key: The user's public key
            user_input: The chat message content
            client_timestamp_utc: Client timestamp in UTC
            client_timezone_offset: Client timezone offset in minutes

        Returns:
            The run_id for tracking this conversation turn
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        # Create user message with metadata
        user_message_metadata = {}
        if client_timestamp_utc:
            user_message_metadata["client_timestamp_utc"] = client_timestamp_utc
        if client_timezone_offset != 0:
            user_message_metadata["client_timezone_offset"] = str(client_timezone_offset)

        user_message = Message(
            run_id=run_id,
            owner_key=owner_key,
            role=Role.HUMAN,
            content=user_input,
            metadata=user_message_metadata,
        )

        # Create Run object
        run_metadata = {}
        if client_timestamp_utc:
            run_metadata["client_timestamp_utc"] = client_timestamp_utc
        if client_timezone_offset != 0:
            run_metadata["client_timezone_offset"] = str(client_timezone_offset)

        run = Run(
            id=run_id,
            owner_key=owner_key,
            status=RunStatus.PENDING,
            metadata=run_metadata,
        )
        run.history.append(user_message)

        # Create envelope message
        envelope_message = Message(
            run_id=run_id, owner_key=owner_key, role=Role.SYSTEM, content=run
        )

        # Publish to bus
        await self.bus.publish(Topics.RUNS_NEW, envelope_message)
        logger.info(
            f"SSE: Published new run for owner_key={owner_key[:10]}..., run_id={run_id}"
        )

        return run_id

    @staticmethod
    def format_sse_event(event_type: str, data: Any) -> str:
        """
        Format data as an SSE event string.

        Args:
            event_type: The event type (e.g., 'text_chunk', 'run_finished')
            data: The event data (will be JSON serialized)

        Returns:
            Formatted SSE event string
        """
        json_data = json.dumps(data) if not isinstance(data, str) else data
        return f"event: {event_type}\ndata: {json_data}\n\n"

    @staticmethod
    def format_sse_keepalive() -> str:
        """
        Format an SSE keepalive comment.

        Returns:
            SSE comment string for keepalive
        """
        return ": keepalive\n\n"
