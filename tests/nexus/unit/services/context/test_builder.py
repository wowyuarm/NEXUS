"""Unit tests for ContextBuilder."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from nexus.core.models import Message, Role, Run
from nexus.services.context.builder import ContextBuilder


class TestContextBuilder:
    """Tests for ContextBuilder class."""

    @pytest.fixture
    def mock_bus(self):
        """Create mock NexusBus."""
        bus = MagicMock()
        bus.subscribe = MagicMock()
        bus.publish = AsyncMock()
        return bus

    @pytest.fixture
    def mock_tool_registry(self):
        """Create mock ToolRegistry."""
        registry = MagicMock()
        registry.get_all_tool_definitions = MagicMock(
            return_value=[
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Search the web",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ]
        )
        return registry

    @pytest.fixture
    def mock_persistence_service(self):
        """Create mock PersistenceService."""
        service = MagicMock()
        service.get_history = AsyncMock(
            return_value=[
                {
                    "role": "human",
                    "content": "Previous message",
                    "timestamp": "2025-12-10T15:00:00Z",
                },
                {
                    "role": "ai",
                    "content": "Previous response",
                    "timestamp": "2025-12-10T15:01:00Z",
                },
            ]
        )
        return service

    @pytest.fixture
    def mock_config_service(self):
        """Create mock ConfigService."""
        service = MagicMock()
        service.get_int = MagicMock(return_value=20)
        return service

    @pytest.fixture
    def builder(
        self,
        mock_bus,
        mock_tool_registry,
        mock_persistence_service,
        mock_config_service,
    ):
        """Create ContextBuilder with mocks."""
        return ContextBuilder(
            bus=mock_bus,
            tool_registry=mock_tool_registry,
            config_service=mock_config_service,
            persistence_service=mock_persistence_service,
        )

    @pytest.mark.asyncio
    async def test_build_context_returns_correct_structure(self, builder):
        """Verify 5-message structure."""
        messages = await builder.build_context(
            owner_key="0xABC123",
            user_profile={"public_key": "0xABC123"},
            current_input="Hello!",
        )

        assert len(messages) == 5
        assert all(isinstance(m, dict) for m in messages)
        assert all("role" in m and "content" in m for m in messages)

    @pytest.mark.asyncio
    async def test_build_context_system_message_first(self, builder):
        """System message is first."""
        messages = await builder.build_context(
            owner_key="0xABC123",
            user_profile={},
            current_input="Hello!",
        )

        assert messages[0]["role"] == "system"
        assert "Nexus" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_build_context_user_messages_have_tags(self, builder):
        """Each user message has [TAG]."""
        messages = await builder.build_context(
            owner_key="0xABC123",
            user_profile={},
            current_input="Hello!",
        )

        # Messages 1-4 are user messages
        user_messages = messages[1:]
        assert all(m["role"] == "user" for m in user_messages)

        # Check tags (tags may have attributes like count=N)
        assert messages[1]["content"].startswith("[CAPABILITIES]")
        assert messages[2]["content"].startswith("[SHARED_MEMORY")
        assert messages[3]["content"].startswith("[FRIENDS_INFO]")
        assert messages[4]["content"].startswith("[THIS_MOMENT]")

    @pytest.mark.asyncio
    async def test_build_context_empty_history(self, builder, mock_persistence_service):
        """Handle no history gracefully."""
        mock_persistence_service.get_history = AsyncMock(return_value=[])

        messages = await builder.build_context(
            owner_key="0xABC123",
            user_profile={},
            current_input="Hello!",
        )

        assert len(messages) == 5
        assert "[SHARED_MEMORY count=0]" in messages[2]["content"]

    @pytest.mark.asyncio
    async def test_build_context_empty_user_profile(self, builder):
        """Handle no profile gracefully."""
        messages = await builder.build_context(
            owner_key="0xABC123",
            user_profile={},
            current_input="Hello!",
        )

        assert len(messages) == 5
        assert "[FRIENDS_INFO]" in messages[3]["content"]

    @pytest.mark.asyncio
    async def test_build_context_includes_current_input(self, builder):
        """Current input appears in THIS_MOMENT."""
        messages = await builder.build_context(
            owner_key="0xABC123",
            user_profile={},
            current_input="What is the meaning of life?",
        )

        this_moment = messages[4]["content"]
        assert "<human_input>" in this_moment
        assert "What is the meaning of life?" in this_moment

    @pytest.mark.asyncio
    async def test_build_context_includes_timestamp(self, builder):
        """Timestamp appears in THIS_MOMENT when provided."""
        messages = await builder.build_context(
            owner_key="0xABC123",
            user_profile={},
            current_input="Hello!",
            timestamp_utc="2025-12-10T08:00:00Z",
            timezone_offset=-480,
        )

        this_moment = messages[4]["content"]
        assert "<current_time>" in this_moment

    @pytest.mark.asyncio
    async def test_build_context_no_persistence_service(
        self, mock_bus, mock_tool_registry, mock_config_service
    ):
        """Handle missing persistence service."""
        builder = ContextBuilder(
            bus=mock_bus,
            tool_registry=mock_tool_registry,
            config_service=mock_config_service,
            persistence_service=None,
        )

        messages = await builder.build_context(
            owner_key="0xABC123",
            user_profile={},
            current_input="Hello!",
        )

        assert len(messages) == 5
        assert "[SHARED_MEMORY count=0]" in messages[2]["content"]

    def test_subscribe_to_bus(self, builder, mock_bus):
        """subscribe_to_bus registers handler."""
        builder.subscribe_to_bus()

        mock_bus.subscribe.assert_called_once()

    def test_extract_user_input_from_run(self, builder):
        """Extract input from run history."""
        run = Run(
            id="run-123",
            owner_key="0xABC",
            history=[
                Message(
                    run_id="run-123",
                    owner_key="0xABC",
                    role=Role.HUMAN,
                    content="Hello!",
                )
            ],
        )

        result = builder._extract_user_input_from_run(run)
        assert result == "Hello!"

    def test_extract_user_input_from_empty_run(self, builder):
        """Handle empty run history."""
        run = Run(id="run-123", owner_key="0xABC", history=[])

        result = builder._extract_user_input_from_run(run)
        assert result == ""
