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
from nexus.core.models import Message, Role
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
        # Arrange: Prepare input message
        input_message = Message(
            run_id="test-run-123",
            session_id="test-session-456",
            role=Role.HUMAN,
            content={
                "current_input": "What is artificial intelligence?",
                "session_id": "test-session-456"
            }
        )

        # Mock system prompt loading
        system_prompt = "You are Xi, an AI assistant."
        mocker.patch.object(context_service, '_load_system_prompt', return_value=system_prompt)

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
        assert published_message.session_id == "test-session-456"
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
        assert messages[0]["content"] == system_prompt
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "What is artificial intelligence?"
        
        # Verify tools are included
        assert content["tools"] == expected_tools

        # Verify persistence service was called with correct parameters
        mock_persistence_service.get_history.assert_called_once_with("test-session-456", 20)

    @pytest.mark.asyncio
    async def test_handle_build_request_error_handling(self, context_service, mock_bus, mock_persistence_service, mocker):
        """
        Test that ContextService properly handles errors and publishes error response.
        """
        # Arrange: Prepare input message
        input_message = Message(
            run_id="test-run-error",
            session_id="test-session-error",
            role=Role.HUMAN,
            content={
                "current_input": "Test input",
                "session_id": "test-session-error"
            }
        )

        # Mock system prompt loading to raise an exception
        mocker.patch.object(context_service, '_load_system_prompt', side_effect=Exception("File system error"))

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
        assert published_message.session_id == "test-session-error"
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
            session_id="test-session-missing",
            role=Role.HUMAN,
            content={
                "session_id": "test-session-missing"
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
