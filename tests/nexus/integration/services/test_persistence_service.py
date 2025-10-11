"""
Integration tests for PersistenceService.

These tests verify that PersistenceService correctly handles event-driven interactions
via NexusBus, including proper message persistence to the database for different event types.
All external dependencies are mocked to ensure isolation while testing the service's
integration with the event bus system and database operations.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from nexus.services.persistence import PersistenceService
from nexus.core.models import Message, Run, RunStatus, Role
from nexus.core.topics import Topics


class TestPersistenceServiceIntegration:
    """Integration test suite for PersistenceService event-driven behavior."""

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock DatabaseService for testing."""
        mock_service = Mock()
        mock_service.insert_message_async = AsyncMock(return_value=True)
        mock_service.get_history_by_owner_key = AsyncMock(return_value=[])
        mock_service.bus = Mock()  # Mock bus for subscription
        return mock_service

    @pytest.fixture
    def persistence_service(self, mock_database_service):
        """Create PersistenceService instance with mocked dependencies."""
        return PersistenceService(database_service=mock_database_service)

    @pytest.fixture
    def sample_run(self):
        """Create a sample Run object for testing."""
        # Create initial human message
        human_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.HUMAN,
            content="What is artificial intelligence?"
        )
        
        # Create run with history
        run = Run(
            id="test-run-123",
            owner_key="test-session-456",
            status=RunStatus.PENDING,
            history=[human_message]
        )
        return run

    @pytest.mark.asyncio
    async def test_persists_human_message_on_new_run(self, persistence_service, mock_database_service, sample_run):
        """
        Test that PersistenceService correctly persists human message when handling new run events.
        Verifies that the message is created with correct role and content.
        """
        # Arrange: Create new run message
        new_run_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.SYSTEM,
            content=sample_run
        )
        
        # Act: Handle new run
        await persistence_service.handle_context_build_request(new_run_message)
        
        # Assert: Verify insert_message_async was called
        mock_database_service.insert_message_async.assert_called_once()
        
        # Verify the persisted message
        persisted_message = mock_database_service.insert_message_async.call_args[0][0]
        assert persisted_message.run_id == "test-run-123"
        assert persisted_message.owner_key == "test-session-456"
        assert persisted_message.role == Role.HUMAN
        assert persisted_message.content == "What is artificial intelligence?"
        assert persisted_message.metadata["source"] == "new_run"
        assert persisted_message.metadata["run_status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_persists_human_message_on_new_run_dict_format(self, persistence_service, mock_database_service):
        """
        Test that PersistenceService handles new run with dict format content.
        """
        # Arrange: Create new run message with dict content
        new_run_message = Message(
            run_id="test-run-dict",
            owner_key="test-session-dict",
            role=Role.SYSTEM,
            content={
                "user_input": "Hello, how are you?",
                "status": "active"
            }
        )
        
        # Act: Handle new run
        await persistence_service.handle_context_build_request(new_run_message)
        
        # Assert: Verify insert_message_async was called
        mock_database_service.insert_message_async.assert_called_once()
        
        # Verify the persisted message
        persisted_message = mock_database_service.insert_message_async.call_args[0][0]
        assert persisted_message.run_id == "test-run-dict"
        assert persisted_message.owner_key == "test-session-dict"
        assert persisted_message.role == Role.HUMAN
        assert persisted_message.content == "Hello, how are you?"
        assert persisted_message.metadata["source"] == "new_run"
        assert persisted_message.metadata["run_status"] == "active"

    @pytest.mark.asyncio
    async def test_persists_ai_message_on_llm_result(self, persistence_service, mock_database_service):
        """
        Test that PersistenceService correctly persists AI message when handling LLM results without tool calls.
        """
        # Arrange: Create LLM result message without tool calls
        llm_result_message = Message(
            run_id="test-run-ai",
            owner_key="test-session-ai",
            role=Role.AI,
            content={
                "content": "Artificial intelligence is a field of computer science that aims to create intelligent machines.",
                "tool_calls": None
            }
        )
        
        # Act: Handle LLM result
        await persistence_service.handle_llm_result(llm_result_message)
        
        # Assert: Verify insert_message_async was called
        mock_database_service.insert_message_async.assert_called_once()
        
        # Verify the persisted message
        persisted_message = mock_database_service.insert_message_async.call_args[0][0]
        assert persisted_message.run_id == "test-run-ai"
        assert persisted_message.owner_key == "test-session-ai"
        assert persisted_message.role == Role.AI
        assert persisted_message.content == "Artificial intelligence is a field of computer science that aims to create intelligent machines."
        assert persisted_message.metadata["source"] == "llm_result"
        assert persisted_message.metadata["tool_calls"] == None
        assert persisted_message.metadata["has_tool_calls"] is False

    @pytest.mark.asyncio
    async def test_persists_ai_intent_and_tool_result(self, persistence_service, mock_database_service):
        """
        Test that PersistenceService correctly persists AI intent with tool calls and subsequent tool results.
        """
        # Act 1: Handle LLM result with tool calls
        llm_result_with_tools = Message(
            run_id="test-run-tools",
            owner_key="test-session-tools",
            role=Role.AI,
            content={
                "content": "I'll search for information about AI.",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "arguments": '{"query": "artificial intelligence"}'
                        }
                    }
                ]
            }
        )
        
        await persistence_service.handle_llm_result(llm_result_with_tools)
        
        # Assert 1: Verify AI message with tool calls was persisted
        mock_database_service.insert_message_async.assert_called_once()
        
        ai_message = mock_database_service.insert_message_async.call_args[0][0]
        assert ai_message.run_id == "test-run-tools"
        assert ai_message.owner_key == "test-session-tools"
        assert ai_message.role == Role.AI
        assert ai_message.content == "I'll search for information about AI."
        assert ai_message.metadata["source"] == "llm_result"
        assert len(ai_message.metadata["tool_calls"]) == 1
        assert ai_message.metadata["tool_calls"][0]["function"]["name"] == "web_search"
        assert ai_message.metadata["has_tool_calls"] is True
        
        mock_database_service.insert_message_async.reset_mock()
        
        # Act 2: Handle tool result
        tool_result_message = Message(
            run_id="test-run-tools",
            owner_key="test-session-tools",
            role=Role.TOOL,
            content={
                "tool_name": "web_search",
                "result": "AI is the simulation of human intelligence processes by machines...",
                "status": "success",
                "call_id": "call_123"
            }
        )
        
        await persistence_service.handle_tool_result(tool_result_message)
        
        # Assert 2: Verify tool result was persisted
        mock_database_service.insert_message_async.assert_called_once()
        
        tool_message = mock_database_service.insert_message_async.call_args[0][0]
        assert tool_message.run_id == "test-run-tools"
        assert tool_message.owner_key == "test-session-tools"
        assert tool_message.role == Role.TOOL
        assert tool_message.content == "AI is the simulation of human intelligence processes by machines..."
        assert tool_message.metadata["source"] == "tool_result"
        assert tool_message.metadata["tool_name"] == "web_search"
        assert tool_message.metadata["status"] == "success"
        assert tool_message.metadata["execution_success"] is True

    @pytest.mark.asyncio
    async def test_skips_system_role_messages(self, persistence_service, mock_database_service):
        """
        Test that PersistenceService skips SYSTEM role messages (streaming events).
        """
        # Arrange: Create SYSTEM role message (streaming event)
        system_message = Message(
            run_id="test-run-system",
            owner_key="test-session-system",
            role=Role.SYSTEM,
            content={
                "event": "text_chunk",
                "payload": {"chunk": "Hello"}
            }
        )
        
        # Act: Handle LLM result
        await persistence_service.handle_llm_result(system_message)
        
        # Assert: Verify no message was persisted
        mock_database_service.insert_message_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_empty_content_messages(self, persistence_service, mock_database_service):
        """
        Test that PersistenceService skips messages with empty content and no tool calls.
        """
        # Arrange: Create message with empty content
        empty_message = Message(
            run_id="test-run-empty",
            owner_key="test-session-empty",
            role=Role.AI,
            content={
                "content": "",
                "tool_calls": None
            }
        )
        
        # Act: Handle LLM result
        await persistence_service.handle_llm_result(empty_message)
        
        # Assert: Verify no message was persisted
        mock_database_service.insert_message_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_none_content_in_llm_result(self, persistence_service, mock_database_service):
        """
        Test that PersistenceService handles None content in LLM results (tool-only responses).
        """
        # Arrange: Create LLM result with None content but tool calls
        llm_result_message = Message(
            run_id="test-run-none",
            owner_key="test-session-none",
            role=Role.AI,
            content={
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_456",
                        "type": "function",
                        "function": {"name": "calculator", "arguments": '{"operation": "add"}'}
                    }
                ]
            }
        )
        
        # Act: Handle LLM result
        await persistence_service.handle_llm_result(llm_result_message)
        
        # Assert: Verify message was persisted with empty string content
        mock_database_service.insert_message_async.assert_called_once()
        
        persisted_message = mock_database_service.insert_message_async.call_args[0][0]
        assert persisted_message.content == ""  # None converted to empty string
        assert persisted_message.metadata["has_tool_calls"] is True

    @pytest.mark.asyncio
    async def test_skips_empty_tool_results(self, persistence_service, mock_database_service):
        """
        Test that PersistenceService skips tool results with empty result content.
        """
        # Arrange: Create tool result with empty result
        empty_tool_result = Message(
            run_id="test-run-empty-tool",
            owner_key="test-session-empty-tool",
            role=Role.TOOL,
            content={
                "tool_name": "empty_tool",
                "result": "",
                "status": "success"
            }
        )
        
        # Act: Handle tool result
        await persistence_service.handle_tool_result(empty_tool_result)
        
        # Assert: Verify no message was persisted
        mock_database_service.insert_message_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_tool_execution_failure(self, persistence_service, mock_database_service):
        """
        Test that PersistenceService correctly persists failed tool execution results.
        """
        # Arrange: Create failed tool result
        failed_tool_result = Message(
            run_id="test-run-failed-tool",
            owner_key="test-session-failed-tool",
            role=Role.TOOL,
            content={
                "tool_name": "failing_tool",
                "result": "Error: Tool execution failed due to invalid parameters",
                "status": "error",
                "call_id": "call_error"
            }
        )
        
        # Act: Handle tool result
        await persistence_service.handle_tool_result(failed_tool_result)
        
        # Assert: Verify failed tool result was persisted
        mock_database_service.insert_message_async.assert_called_once()
        
        tool_message = mock_database_service.insert_message_async.call_args[0][0]
        assert tool_message.role == Role.TOOL
        assert tool_message.content == "Error: Tool execution failed due to invalid parameters"
        assert tool_message.metadata["tool_name"] == "failing_tool"
        assert tool_message.metadata["status"] == "error"
        assert tool_message.metadata["execution_success"] is False

    @pytest.mark.asyncio
    async def test_handles_invalid_run_data_format(self, persistence_service, mock_database_service):
        """
        Test that PersistenceService handles invalid run data format gracefully.
        """
        # Arrange: Create message with invalid run data
        invalid_run_message = Message(
            run_id="test-run-invalid",
            owner_key="test-session-invalid",
            role=Role.SYSTEM,
            content="invalid_run_data_not_object"  # Should be Run object or dict
        )
        
        # Act: Handle new run
        await persistence_service.handle_context_build_request(invalid_run_message)
        
        # Assert: Verify no message was persisted due to invalid format
        mock_database_service.insert_message_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_invalid_llm_result_format(self, persistence_service, mock_database_service):
        """
        Test that PersistenceService handles invalid LLM result format gracefully.
        """
        # Arrange: Create message with invalid content format
        invalid_llm_message = Message(
            run_id="test-run-invalid-llm",
            owner_key="test-session-invalid-llm",
            role=Role.AI,
            content="invalid_content_not_dict"  # Should be dict
        )
        
        # Act: Handle LLM result
        await persistence_service.handle_llm_result(invalid_llm_message)
        
        # Assert: Verify no message was persisted due to invalid format
        mock_database_service.insert_message_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_invalid_tool_result_format(self, persistence_service, mock_database_service):
        """
        Test that PersistenceService handles invalid tool result format gracefully.
        """
        # Arrange: Create message with invalid content format
        invalid_tool_message = Message(
            run_id="test-run-invalid-tool",
            owner_key="test-session-invalid-tool",
            role=Role.TOOL,
            content="invalid_content_not_dict"  # Should be dict
        )
        
        # Act: Handle tool result
        await persistence_service.handle_tool_result(invalid_tool_message)
        
        # Assert: Verify no message was persisted due to invalid format
        mock_database_service.insert_message_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_history_delegates_to_database_service(self, persistence_service, mock_database_service):
        """
        Test that get_history method correctly delegates to DatabaseService.
        """
        # Arrange: Configure mock to return sample history
        sample_history = [
            {"role": "human", "content": "Hello"},
            {"role": "ai", "content": "Hi there!"}
        ]
        mock_database_service.get_history_by_owner_key.return_value = sample_history
        
        # Act: Get history
        result = await persistence_service.get_history("test-session", 10)
        
        # Assert: Verify delegation and result
        mock_database_service.get_history_by_owner_key.assert_called_once_with("test-session", 10)
        assert result == sample_history

    @pytest.mark.asyncio
    async def test_get_history_handles_database_error(self, persistence_service, mock_database_service):
        """
        Test that get_history handles database errors gracefully.
        """
        # Arrange: Configure mock to raise exception
        mock_database_service.get_history_by_owner_key.side_effect = Exception("Database connection failed")
        
        # Act: Get history
        result = await persistence_service.get_history("test-session", 10)
        
        # Assert: Verify empty list returned on error
        assert result == []

    def test_subscribe_to_bus(self, persistence_service, mock_database_service):
        """
        Test that PersistenceService correctly subscribes to all required topics.
        """
        # Act: Subscribe to bus
        persistence_service.subscribe_to_bus()
        
        # Assert: Verify subscriptions to all required topics
        # Note: PersistenceService subscribes to CONTEXT_BUILD_REQUEST (not RUNS_NEW)
        # to ensure only validated members' messages are persisted
        expected_subscriptions = [
            (Topics.CONTEXT_BUILD_REQUEST, persistence_service.handle_context_build_request),
            (Topics.LLM_RESULTS, persistence_service.handle_llm_result),
            (Topics.TOOLS_RESULTS, persistence_service.handle_tool_result)
        ]
        
        assert mock_database_service.bus.subscribe.call_count == len(expected_subscriptions)
        
        for i, (expected_topic, expected_handler) in enumerate(expected_subscriptions):
            call_args = mock_database_service.bus.subscribe.call_args_list[i]
            assert call_args[0][0] == expected_topic
            assert call_args[0][1] == expected_handler
