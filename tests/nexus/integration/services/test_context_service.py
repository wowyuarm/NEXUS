"""
Integration tests for ContextService.

These tests verify that ContextService correctly handles event-driven interactions
via NexusBus, including proper message handling and response publishing. All external
dependencies are mocked to ensure isolation while testing the service's integration
with the event bus system.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from nexus.services.context import ContextService
from nexus.core.models import Message, Run, RunStatus, Role
from nexus.core.topics import Topics


class TestContextServiceIntegration:
    """Integration test suite for ContextService event-driven behavior."""

    @pytest.fixture
    def mock_bus(self):
        """Create a mock NexusBus for testing."""
        mock_bus = Mock()
        mock_bus.publish = AsyncMock()
        mock_bus.subscribe = Mock()
        return mock_bus

    @pytest.fixture
    def mock_tool_registry(self):
        """Create a mock ToolRegistry for testing."""
        mock_registry = Mock()
        mock_registry.get_all_tool_definitions.return_value = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
        return mock_registry

    @pytest.fixture
    def mock_persistence_service(self):
        """Create a mock PersistenceService for testing."""
        mock_service = AsyncMock()
        mock_service.get_history.return_value = [
            {"role": "human", "content": "Hello, how are you?"},
            {"role": "ai", "content": "I'm doing well, thank you!"}
        ]
        return mock_service

    @pytest.fixture
    def mock_config_service(self):
        """Create a mock ConfigService for testing."""
        mock_service = Mock()
        mock_service.get_int.return_value = 20  # Default history limit
        # Default user_defaults with prompts (new object structure)
        mock_service.get_user_defaults.return_value = {
            "config": {
                "model": "gemini-2.5-flash",
                "temperature": 0.8
            },
            "prompts": {
                "field": {
                    "content": "场域：共同成长的对话空间...",
                    "editable": False,
                    "order": 1
                },
                "presence": {
                    "content": "You are Nexus, an AI assistant.",
                    "editable": False,
                    "order": 2
                },
                "capabilities": {
                    "content": "Available tools description",
                    "editable": False,
                    "order": 3
                },
                "learning": {
                    "content": "用户档案与学习记录...",
                    "editable": True,
                    "order": 4
                }
            }
        }
        return mock_service

    @pytest.fixture
    def context_service(self, mock_bus, mock_tool_registry, mock_persistence_service, mock_config_service):
        """Create ContextService instance with mocked dependencies."""
        return ContextService(
            bus=mock_bus,
            tool_registry=mock_tool_registry,
            config_service=mock_config_service,
            persistence_service=mock_persistence_service
        )

    @pytest.mark.asyncio
    async def test_handle_build_request_success(self, context_service, mock_bus, mock_tool_registry, mock_persistence_service, mocker):
        """
        Test that ContextService correctly handles CONTEXT_BUILD_REQUEST and publishes
        properly formatted CONTEXT_BUILD_RESPONSE with messages and tools.
        """
        # Arrange: Create Run object with user input
        human_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.HUMAN,
            content="What is artificial intelligence?"
        )
        
        run = Run(
            id="test-run-123",
            owner_key="test-session-456",
            status=RunStatus.BUILDING_CONTEXT,
            history=[human_message],
            metadata={
                "user_profile": {
                    "public_key": "test-session-456",
                    "config_overrides": {},
                    "prompt_overrides": {}
                }
            }
        )
        
        # Prepare input message with Run object
        input_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.SYSTEM,
            content=run
        )

        # Configure mock persistence service to return history
        mock_persistence_service.get_history.return_value = [
            {"role": "human", "content": "Previous question"},
            {"role": "ai", "content": "Previous answer"}
        ]

        # Configure mock tool registry to return tool definitions
        expected_tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
        mock_tool_registry.get_all_tool_definitions.return_value = expected_tools

        # Act: Handle the build request
        await context_service.handle_build_request(input_message)

        # Assert: Verify that CONTEXT_BUILD_RESPONSE was published with correct format
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        
        # Verify topic
        assert call_args[0][0] == Topics.CONTEXT_BUILD_RESPONSE
        
        # Verify message structure
        published_message = call_args[0][1]
        assert published_message.run_id == "test-run-123"
        assert published_message.owner_key == "test-session-456"
        assert published_message.role == Role.SYSTEM
        
        # Verify content structure
        content = published_message.content
        assert content["status"] == "success"
        assert "messages" in content
        assert "tools" in content
        
        # Verify messages format (should include system prompt, history, and current input)
        messages = content["messages"]
        assert len(messages) >= 3  # At least system + current input + some history
        assert messages[0]["role"] == "system"
        # System prompt should be from user_defaults (since no overrides)
        # It should contain default content "Nexus"
        assert "Nexus" in messages[0]["content"]
        assert messages[-1]["role"] == "user"
        # The final message should be in XML context format
        assert "<Human_Input>" in messages[-1]["content"]
        assert "What is artificial intelligence?" in messages[-1]["content"]
        
        # Verify tools are included
        assert content["tools"] == expected_tools

        # Verify persistence service was called with correct parameters
        mock_persistence_service.get_history.assert_called_once_with("test-session-456", 20)

    @pytest.mark.asyncio
    async def test_handle_build_request_error_handling(self, context_service, mock_bus, mock_persistence_service, mock_config_service, mocker):
        """
        Test that ContextService properly handles errors and publishes error response.
        """
        # Arrange: Create Run object
        human_message = Message(
            run_id="test-run-error",
            owner_key="test-session-error",
            role=Role.HUMAN,
            content="Test input"
        )
        
        run = Run(
            id="test-run-error",
            owner_key="test-session-error",
            status=RunStatus.BUILDING_CONTEXT,
            history=[human_message],
            metadata={
                "user_profile": {
                    "public_key": "test-session-error",
                    "config_overrides": {},
                    "prompt_overrides": {}
                }
            }
        )
        
        input_message = Message(
            run_id="test-run-error",
            owner_key="test-session-error",
            role=Role.SYSTEM,
            content=run
        )

        # Mock config service to raise an exception
        mock_config_service.get_user_defaults.side_effect = Exception("Config service error")

        # Act: Handle the build request
        await context_service.handle_build_request(input_message)

        # Assert: Verify that error response was published
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        
        # Verify topic
        assert call_args[0][0] == Topics.CONTEXT_BUILD_RESPONSE
        
        # Verify error message structure
        published_message = call_args[0][1]
        assert published_message.run_id == "test-run-error"
        assert published_message.owner_key == "test-session-error"
        assert published_message.role == Role.SYSTEM
        
        # Verify error content
        content = published_message.content
        assert content["status"] == "error"
        assert content["messages"] == []
        assert content["tools"] == []

    @pytest.mark.asyncio
    async def test_handle_build_request_missing_current_input(self, context_service, mock_bus):
        """
        Test that ContextService handles missing current_input gracefully.
        """
        # Arrange: Prepare input message without current_input
        input_message = Message(
            run_id="test-run-missing",
            owner_key="test-session-missing",
            role=Role.HUMAN,
            content={
                "owner_key": "test-session-missing"
                # Missing current_input
            }
        )

        # Act: Handle the build request
        await context_service.handle_build_request(input_message)

        # Assert: Verify that no response was published (early return)
        mock_bus.publish.assert_not_called()

    def test_subscribe_to_bus(self, context_service, mock_bus):
        """
        Test that ContextService correctly subscribes to the appropriate topics.
        """
        # Act: Subscribe to bus
        context_service.subscribe_to_bus()

        # Assert: Verify subscription to correct topic
        mock_bus.subscribe.assert_called_once_with(
            Topics.CONTEXT_BUILD_REQUEST,
            context_service.handle_build_request
        )

    @pytest.mark.asyncio
    async def test_context_composition_with_overrides(self, context_service, mock_bus, mock_tool_registry, mock_persistence_service, mock_config_service):
        """
        Test that ContextService composes prompts correctly when user has prompt_overrides.
        Verifies that user's custom learning profile overrides the default.
        """
        # Arrange: Create Run object with user_profile containing prompt_overrides
        human_message = Message(
            run_id="test-run-override",
            owner_key="user-with-overrides",
            role=Role.HUMAN,
            content="Hello!"
        )
        
        run = Run(
            id="test-run-override",
            owner_key="user-with-overrides",
            status=RunStatus.BUILDING_CONTEXT,
            history=[human_message],
            metadata={
                "user_profile": {
                    "public_key": "user-with-overrides",
                    "config_overrides": {},
                    "prompt_overrides": {
                        "learning": "我是曦，你的AI灵魂伴侣。用户档案..."
                    }
                }
            }
        )
        
        # Create input message with Run object
        input_message = Message(
            run_id="test-run-override",
            owner_key="user-with-overrides",
            role=Role.SYSTEM,
            content=run  # Pass Run object as content
        )
        
        # Mock persistence to return empty history
        mock_persistence_service.get_history.return_value = []
        
        # Act: Handle the build request
        await context_service.handle_build_request(input_message)
        
        # Assert: Verify response was published
        assert mock_bus.publish.called
        call_args = mock_bus.publish.call_args
        published_message = call_args[0][1]
        
        # Verify the system prompt includes the overridden learning profile
        messages = published_message.content["messages"]
        system_message = messages[0]
        assert system_message["role"] == "system"
        # System prompt should contain the overridden learning "我是曦"
        assert "我是曦" in system_message["content"]
        assert "你的AI灵魂伴侣" in system_message["content"]
        # The learning was overridden, but field/presence/capabilities parts still use defaults
        # which is correct behavior - only specified overrides are applied

    @pytest.mark.asyncio
    async def test_context_uses_defaults_for_new_user(self, context_service, mock_bus, mock_tool_registry, mock_persistence_service, mock_config_service):
        """
        Test that ContextService uses default prompts when user has no overrides.
        Verifies that system uses the default prompts from config.
        """
        # Arrange: Create Run object with user_profile but empty overrides
        human_message = Message(
            run_id="test-run-default",
            owner_key="new-user",
            role=Role.HUMAN,
            content="What is AI?"
        )
        
        run = Run(
            id="test-run-default",
            owner_key="new-user",
            status=RunStatus.BUILDING_CONTEXT,
            history=[human_message],
            metadata={
                "user_profile": {
                    "public_key": "new-user",
                    "config_overrides": {},
                    "prompt_overrides": {}  # Empty overrides
                }
            }
        )
        
        # Create input message with Run object
        input_message = Message(
            run_id="test-run-default",
            owner_key="new-user",
            role=Role.SYSTEM,
            content=run
        )
        
        # Mock persistence to return empty history
        mock_persistence_service.get_history.return_value = []
        
        # Act: Handle the build request
        await context_service.handle_build_request(input_message)
        
        # Assert: Verify response was published
        assert mock_bus.publish.called
        call_args = mock_bus.publish.call_args
        published_message = call_args[0][1]
        
        # Verify the system prompt includes the default prompts
        messages = published_message.content["messages"]
        system_message = messages[0]
        assert system_message["role"] == "system"
        # System prompt should contain the default content "Nexus"
        assert "Nexus" in system_message["content"]
        # Should contain content from all 4 layers
        assert "Available tools description" in system_message["content"]
