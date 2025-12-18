"""
Unit tests for SSE interface.

Tests for the SSE (Server-Sent Events) interface that handles
real-time communication via HTTP + SSE.
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock

import pytest

from nexus.core.models import Message, Role
from nexus.core.topics import Topics
from nexus.interfaces.sse import SSEInterface


class TestSSEInterface:
    """Tests for SSEInterface class."""

    @pytest.fixture
    def mock_bus(self):
        """Create a mock NexusBus."""
        bus = Mock()
        bus.publish = AsyncMock()
        bus.subscribe = Mock()
        return bus

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock DatabaseService."""
        return Mock()

    @pytest.fixture
    def mock_identity_service(self):
        """Create a mock IdentityService."""
        service = Mock()
        service.get_identity = AsyncMock(return_value=None)
        return service

    @pytest.fixture
    def sse_interface(self, mock_bus, mock_database_service, mock_identity_service):
        """Create an SSEInterface instance with mocked dependencies."""
        return SSEInterface(mock_bus, mock_database_service, mock_identity_service)

    def test_init(self, sse_interface, mock_bus, mock_database_service):
        """Test SSEInterface initialization."""
        assert sse_interface.bus == mock_bus
        assert sse_interface.database_service == mock_database_service
        assert sse_interface.active_chat_streams == {}
        assert sse_interface.active_persistent_streams == {}

    def test_subscribe_to_bus(self, sse_interface, mock_bus):
        """Test bus subscription."""
        sse_interface.subscribe_to_bus()
        
        # Should subscribe to UI_EVENTS and COMMAND_RESULT
        assert mock_bus.subscribe.call_count == 2
        calls = mock_bus.subscribe.call_args_list
        topics = [call[0][0] for call in calls]
        assert Topics.UI_EVENTS in topics
        assert Topics.COMMAND_RESULT in topics

    def test_register_chat_stream(self, sse_interface):
        """Test registering a chat stream."""
        run_id = "test_run_123"
        queue = sse_interface.register_chat_stream(run_id)
        
        assert isinstance(queue, asyncio.Queue)
        assert run_id in sse_interface.active_chat_streams
        assert sse_interface.active_chat_streams[run_id] == queue

    def test_unregister_chat_stream(self, sse_interface):
        """Test unregistering a chat stream."""
        run_id = "test_run_123"
        sse_interface.register_chat_stream(run_id)
        assert run_id in sse_interface.active_chat_streams
        
        sse_interface.unregister_chat_stream(run_id)
        assert run_id not in sse_interface.active_chat_streams

    def test_unregister_nonexistent_chat_stream(self, sse_interface):
        """Test unregistering a non-existent stream doesn't raise error."""
        sse_interface.unregister_chat_stream("nonexistent_run")
        # Should not raise

    def test_register_persistent_stream(self, sse_interface):
        """Test registering a persistent stream."""
        public_key = "0xABC123"
        queue = sse_interface.register_persistent_stream(public_key)
        
        assert isinstance(queue, asyncio.Queue)
        assert public_key in sse_interface.active_persistent_streams
        assert sse_interface.active_persistent_streams[public_key] == queue

    def test_unregister_persistent_stream(self, sse_interface):
        """Test unregistering a persistent stream."""
        public_key = "0xABC123"
        sse_interface.register_persistent_stream(public_key)
        assert public_key in sse_interface.active_persistent_streams
        
        sse_interface.unregister_persistent_stream(public_key)
        assert public_key not in sse_interface.active_persistent_streams

    @pytest.mark.asyncio
    async def test_handle_ui_event_routes_to_chat_stream(self, sse_interface):
        """Test UI event routing to chat stream."""
        run_id = "test_run_123"
        queue = sse_interface.register_chat_stream(run_id)
        
        # Create a UI event message
        ui_event = {
            "event": "text_chunk",
            "run_id": run_id,
            "payload": {"chunk": "Hello", "is_final": False}
        }
        message = Message(
            run_id=run_id,
            owner_key="0xABC",
            role=Role.SYSTEM,
            content=ui_event
        )
        
        await sse_interface.handle_ui_event(message)
        
        # Event should be in the queue
        assert not queue.empty()
        received = await queue.get()
        assert received == ui_event

    @pytest.mark.asyncio
    async def test_handle_ui_event_no_active_stream(self, sse_interface):
        """Test UI event handling when no active stream exists."""
        run_id = "test_run_123"
        
        ui_event = {"event": "text_chunk", "payload": {"chunk": "Hello"}}
        message = Message(
            run_id=run_id,
            owner_key="0xABC",
            role=Role.SYSTEM,
            content=ui_event
        )
        
        # Should not raise error
        await sse_interface.handle_ui_event(message)

    @pytest.mark.asyncio
    async def test_handle_command_result_routes_to_persistent_stream(self, sse_interface):
        """Test command result routing to persistent stream."""
        public_key = "0xABC123"
        queue = sse_interface.register_persistent_stream(public_key)
        
        # Create a command result message
        result = {"status": "success", "message": "pong"}
        message = Message(
            run_id="cmd_run_123",
            owner_key=public_key,
            role=Role.SYSTEM,
            content=result,
            metadata={"command": "/ping"}
        )
        
        await sse_interface.handle_command_result(message)
        
        # Event should be in the queue
        assert not queue.empty()
        received = await queue.get()
        assert received["event"] == "command_result"
        assert received["payload"]["command"] == "/ping"
        assert received["payload"]["result"] == result

    @pytest.mark.asyncio
    async def test_create_run_and_publish(self, sse_interface, mock_bus):
        """Test run creation and publishing."""
        owner_key = "0xABC123"
        user_input = "Hello, how are you?"
        
        run_id = await sse_interface.create_run_and_publish(
            owner_key=owner_key,
            user_input=user_input,
            client_timestamp_utc="2025-12-11T03:00:00Z",
            client_timezone_offset=-480
        )
        
        # Should return a run_id
        assert run_id is not None
        assert run_id.startswith("run_")
        
        # Should publish to RUNS_NEW topic
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        assert call_args[0][0] == Topics.RUNS_NEW
        
        # Verify the published message
        published_message = call_args[0][1]
        assert published_message.run_id == run_id
        assert published_message.owner_key == owner_key

    def test_format_sse_event(self):
        """Test SSE event formatting."""
        event_type = "text_chunk"
        data = {"chunk": "Hello", "is_final": False}
        
        formatted = SSEInterface.format_sse_event(event_type, data)
        
        assert formatted.startswith("event: text_chunk\n")
        assert "data: " in formatted
        assert formatted.endswith("\n\n")
        
        # Parse the data back
        lines = formatted.strip().split("\n")
        data_line = [l for l in lines if l.startswith("data: ")][0]
        parsed_data = json.loads(data_line[6:])
        assert parsed_data == data

    def test_format_sse_event_with_string_data(self):
        """Test SSE event formatting with string data."""
        event_type = "message"
        data = "Simple string message"
        
        formatted = SSEInterface.format_sse_event(event_type, data)
        
        assert "event: message\n" in formatted
        assert f"data: {data}\n" in formatted

    def test_format_sse_keepalive(self):
        """Test SSE keepalive formatting."""
        keepalive = SSEInterface.format_sse_keepalive()
        
        assert keepalive == ": keepalive\n\n"


class TestSSEEventRouting:
    """Tests for SSE event routing logic."""

    @pytest.fixture
    def mock_bus(self):
        bus = Mock()
        bus.publish = AsyncMock()
        bus.subscribe = Mock()
        return bus

    @pytest.fixture
    def sse_interface(self, mock_bus):
        return SSEInterface(mock_bus, Mock(), Mock())

    @pytest.mark.asyncio
    async def test_multiple_chat_streams(self, sse_interface):
        """Test routing events to correct chat streams."""
        run_id_1 = "run_1"
        run_id_2 = "run_2"
        
        queue_1 = sse_interface.register_chat_stream(run_id_1)
        queue_2 = sse_interface.register_chat_stream(run_id_2)
        
        # Send event to run_1
        event_1 = {"event": "text_chunk", "payload": {"chunk": "For run 1"}}
        message_1 = Message(
            run_id=run_id_1,
            owner_key="0xABC",
            role=Role.SYSTEM,
            content=event_1
        )
        await sse_interface.handle_ui_event(message_1)
        
        # Send event to run_2
        event_2 = {"event": "text_chunk", "payload": {"chunk": "For run 2"}}
        message_2 = Message(
            run_id=run_id_2,
            owner_key="0xABC",
            role=Role.SYSTEM,
            content=event_2
        )
        await sse_interface.handle_ui_event(message_2)
        
        # Verify correct routing
        assert not queue_1.empty()
        assert not queue_2.empty()
        
        received_1 = await queue_1.get()
        received_2 = await queue_2.get()
        
        assert received_1["payload"]["chunk"] == "For run 1"
        assert received_2["payload"]["chunk"] == "For run 2"

    @pytest.mark.asyncio
    async def test_command_result_with_structured_command(self, sse_interface):
        """Test command result with structured command in metadata."""
        public_key = "0xABC123"
        queue = sse_interface.register_persistent_stream(public_key)
        
        # Command as dict in metadata
        result = {"status": "success", "message": "Identity verified"}
        message = Message(
            run_id="cmd_123",
            owner_key=public_key,
            role=Role.SYSTEM,
            content=result,
            metadata={"command": {"command": "identity"}}
        )
        
        await sse_interface.handle_command_result(message)
        
        received = await queue.get()
        assert received["payload"]["command"] == "/identity"
