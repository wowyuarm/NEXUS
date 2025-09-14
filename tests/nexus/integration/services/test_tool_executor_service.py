"""
Integration tests for ToolExecutorService.

These tests verify that ToolExecutorService correctly handles event-driven interactions
via NexusBus, including proper tool execution request handling and result publishing. All external
dependencies are mocked to ensure isolation while testing the service's integration
with the event bus system.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from nexus.services.tool_executor import ToolExecutorService
from nexus.core.models import Message, Role
from nexus.core.topics import Topics


class TestToolExecutorServiceIntegration:
    """Integration test suite for ToolExecutorService event-driven behavior."""

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
        return mock_registry

    @pytest.fixture
    def tool_executor_service(self, mock_bus, mock_tool_registry):
        """Create ToolExecutorService instance with mocked dependencies."""
        return ToolExecutorService(bus=mock_bus, tool_registry=mock_tool_registry)

    @pytest.mark.asyncio
    async def test_handle_tool_request_success(self, tool_executor_service, mock_bus, mock_tool_registry):
        """
        Test that ToolExecutorService correctly handles TOOLS_REQUESTS and publishes
        properly formatted TOOLS_RESULTS with successful execution status.
        """
        # Arrange: Prepare input message
        input_message = Message(
            run_id="test-run-123",
            session_id="test-session-456",
            role=Role.SYSTEM,
            content={
                "name": "web_search",
                "args": {"query": "artificial intelligence news"}
            }
        )

        # Configure mock tool registry to return a simple lambda function
        test_tool_function = lambda query: f"search result for {query}"
        mock_tool_registry.get_tool_function.return_value = test_tool_function

        # Act: Handle the tool request
        await tool_executor_service.handle_tool_request(input_message)

        # Assert: Verify that TOOLS_RESULTS was published with correct format
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        
        # Verify topic
        assert call_args[0][0] == Topics.TOOLS_RESULTS
        
        # Verify message structure
        published_message = call_args[0][1]
        assert published_message.run_id == "test-run-123"
        assert published_message.session_id == "test-session-456"
        assert published_message.role == Role.TOOL
        
        # Verify content structure
        content = published_message.content
        assert content["status"] == "success"
        assert content["result"] == "search result for artificial intelligence news"
        assert content["tool_name"] == "web_search"

        # Verify tool registry was called with correct parameters
        mock_tool_registry.get_tool_function.assert_called_once_with("web_search")

    @pytest.mark.asyncio
    async def test_handle_tool_request_failure(self, tool_executor_service, mock_bus, mock_tool_registry):
        """
        Test that ToolExecutorService correctly handles tool execution failures and publishes
        error response with proper status and error message.
        """
        # Arrange: Prepare input message
        input_message = Message(
            run_id="test-run-error",
            session_id="test-session-error",
            role=Role.SYSTEM,
            content={
                "name": "failing_tool",
                "args": {"param": "value"}
            }
        )

        # Configure mock tool registry to return a function that raises an exception
        def failing_tool_function(**kwargs):
            raise ValueError("Tool execution failed: invalid parameter")
        
        mock_tool_registry.get_tool_function.return_value = failing_tool_function

        # Act: Handle the tool request
        await tool_executor_service.handle_tool_request(input_message)

        # Assert: Verify that error response was published
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        
        # Verify topic
        assert call_args[0][0] == Topics.TOOLS_RESULTS
        
        # Verify error message structure
        published_message = call_args[0][1]
        assert published_message.run_id == "test-run-error"
        assert published_message.session_id == "test-session-error"
        assert published_message.role == Role.TOOL
        
        # Verify error content
        content = published_message.content
        assert content["status"] == "error"
        assert "Tool execution failed: invalid parameter" in content["result"]
        assert content["tool_name"] == "failing_tool"

    @pytest.mark.asyncio
    async def test_handle_tool_request_tool_not_found(self, tool_executor_service, mock_bus, mock_tool_registry):
        """
        Test that ToolExecutorService handles missing tools gracefully.
        """
        # Arrange: Prepare input message
        input_message = Message(
            run_id="test-run-missing",
            session_id="test-session-missing",
            role=Role.SYSTEM,
            content={
                "name": "nonexistent_tool",
                "args": {}
            }
        )

        # Configure mock tool registry to return None (tool not found)
        mock_tool_registry.get_tool_function.return_value = None

        # Act: Handle the tool request
        await tool_executor_service.handle_tool_request(input_message)

        # Assert: Verify that error response was published
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        
        # Verify topic
        assert call_args[0][0] == Topics.TOOLS_RESULTS
        
        # Verify error message structure
        published_message = call_args[0][1]
        assert published_message.run_id == "test-run-missing"
        assert published_message.session_id == "test-session-missing"
        assert published_message.role == Role.TOOL
        
        # Verify error content
        content = published_message.content
        assert content["status"] == "error"
        assert "Tool 'nonexistent_tool' not found in registry" in content["result"]
        assert content["tool_name"] == "nonexistent_tool"

    @pytest.mark.asyncio
    async def test_handle_tool_request_invalid_content(self, tool_executor_service, mock_bus):
        """
        Test that ToolExecutorService handles invalid message content gracefully.
        """
        # Arrange: Prepare input message with invalid content
        input_message = Message(
            run_id="test-run-invalid",
            session_id="test-session-invalid",
            role=Role.SYSTEM,
            content="invalid_content_not_dict"  # Should be a dict
        )

        # Act: Handle the tool request
        await tool_executor_service.handle_tool_request(input_message)

        # Assert: Verify that error response was published
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        
        # Verify topic
        assert call_args[0][0] == Topics.TOOLS_RESULTS
        
        # Verify error message structure
        published_message = call_args[0][1]
        assert published_message.run_id == "test-run-invalid"
        assert published_message.session_id == "test-session-invalid"
        assert published_message.role == Role.TOOL
        
        # Verify error content
        content = published_message.content
        assert content["status"] == "error"
        assert "Tool request content must be a dictionary" in content["result"]
        assert content["tool_name"] == "unknown"

    @pytest.mark.asyncio
    async def test_handle_tool_request_missing_tool_name(self, tool_executor_service, mock_bus):
        """
        Test that ToolExecutorService handles missing tool name gracefully.
        """
        # Arrange: Prepare input message without tool name
        input_message = Message(
            run_id="test-run-no-name",
            session_id="test-session-no-name",
            role=Role.SYSTEM,
            content={
                "args": {"param": "value"}
                # Missing "name" field
            }
        )

        # Act: Handle the tool request
        await tool_executor_service.handle_tool_request(input_message)

        # Assert: Verify that error response was published
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        
        # Verify topic
        assert call_args[0][0] == Topics.TOOLS_RESULTS
        
        # Verify error message structure
        published_message = call_args[0][1]
        assert published_message.run_id == "test-run-no-name"
        assert published_message.session_id == "test-session-no-name"
        assert published_message.role == Role.TOOL
        
        # Verify error content
        content = published_message.content
        assert content["status"] == "error"
        assert "Tool request missing 'name' field" in content["result"]
        assert content["tool_name"] == "unknown"

    @pytest.mark.asyncio
    async def test_handle_tool_request_invalid_args_type(self, tool_executor_service, mock_bus, mock_tool_registry):
        """
        Test that ToolExecutorService handles invalid args type gracefully.
        """
        # Arrange: Prepare input message with invalid args type
        input_message = Message(
            run_id="test-run-invalid-args",
            session_id="test-session-invalid-args",
            role=Role.SYSTEM,
            content={
                "name": "test_tool",
                "args": "invalid_args_should_be_dict"  # Should be a dict
            }
        )

        # Act: Handle the tool request
        await tool_executor_service.handle_tool_request(input_message)

        # Assert: Verify that error response was published
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        
        # Verify topic
        assert call_args[0][0] == Topics.TOOLS_RESULTS
        
        # Verify error message structure
        published_message = call_args[0][1]
        assert published_message.run_id == "test-run-invalid-args"
        assert published_message.session_id == "test-session-invalid-args"
        assert published_message.role == Role.TOOL
        
        # Verify error content
        content = published_message.content
        assert content["status"] == "error"
        assert "Tool args must be a dictionary" in content["result"]
        assert content["tool_name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_handle_tool_request_with_complex_result(self, tool_executor_service, mock_bus, mock_tool_registry):
        """
        Test that ToolExecutorService handles tools that return complex data structures.
        """
        # Arrange: Prepare input message
        input_message = Message(
            run_id="test-run-complex",
            session_id="test-session-complex",
            role=Role.SYSTEM,
            content={
                "name": "data_processor",
                "args": {"input_data": [1, 2, 3]}
            }
        )

        # Configure mock tool registry to return a function with complex result
        def complex_tool_function(input_data):
            return {
                "processed_data": [x * 2 for x in input_data],
                "summary": f"Processed {len(input_data)} items",
                "metadata": {"timestamp": "2023-01-01", "version": "1.0"}
            }
        
        mock_tool_registry.get_tool_function.return_value = complex_tool_function

        # Act: Handle the tool request
        await tool_executor_service.handle_tool_request(input_message)

        # Assert: Verify that success response was published with complex result
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        
        # Verify topic
        assert call_args[0][0] == Topics.TOOLS_RESULTS
        
        # Verify message structure
        published_message = call_args[0][1]
        assert published_message.run_id == "test-run-complex"
        assert published_message.session_id == "test-session-complex"
        assert published_message.role == Role.TOOL
        
        # Verify content structure
        content = published_message.content
        assert content["status"] == "success"
        assert content["tool_name"] == "data_processor"
        
        # Verify complex result is preserved
        result = content["result"]
        assert isinstance(result, dict)
        assert result["processed_data"] == [2, 4, 6]
        assert result["summary"] == "Processed 3 items"
        assert "metadata" in result

    def test_subscribe_to_bus(self, tool_executor_service, mock_bus):
        """
        Test that ToolExecutorService correctly subscribes to the appropriate topics.
        """
        # Act: Subscribe to bus
        tool_executor_service.subscribe_to_bus()

        # Assert: Verify subscription to correct topic
        mock_bus.subscribe.assert_called_once_with(
            Topics.TOOLS_REQUESTS,
            tool_executor_service.handle_tool_request
        )
