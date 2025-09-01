"""Integration tests for PersistenceService."""

import pytest
from unittest.mock import AsyncMock
from nexus.core.models import Message, Role, Run
from nexus.services.persistence import PersistenceService


class TestPersistenceService:
    """Test suite for PersistenceService integration behavior."""

    @pytest.fixture
    def mock_database_service(self, mocker):
        """Fixture providing a mock DatabaseService with insert_message_async method."""
        mock_db = mocker.MagicMock()
        mock_db.insert_message_async = AsyncMock(return_value=True)
        return mock_db

    @pytest.fixture
    def persistence_service(self, mock_database_service):
        """Fixture providing a PersistenceService instance with mocked DatabaseService."""
        return PersistenceService(mock_database_service)

    @pytest.mark.asyncio
    async def test_persists_human_message_on_new_run(self, persistence_service, mock_database_service):
        """Test that PersistenceService persists human messages on RUNS_NEW events."""
        # Arrange
        run_id = "run_123"
        session_id = "session_456"
        user_input = "Hello, how are you?"
        
        # Create a Run object with history
        run = Run(
            id=run_id,
            session_id=session_id,
            history=[
                Message(
                    run_id=run_id,
                    session_id=session_id,
                    role=Role.HUMAN,
                    content=user_input
                )
            ]
        )
        
        # Create the RUNS_NEW message
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.SYSTEM,
            content=run
        )

        # Act
        await persistence_service.handle_new_run(message)

        # Assert
        mock_database_service.insert_message_async.assert_called_once()
        persisted_message = mock_database_service.insert_message_async.call_args[0][0]
        assert persisted_message.role == Role.HUMAN
        assert persisted_message.content == user_input
        assert persisted_message.run_id == run_id
        assert persisted_message.session_id == session_id

    @pytest.mark.asyncio
    async def test_persists_ai_message_on_llm_result(self, persistence_service, mock_database_service):
        """Test that PersistenceService persists AI messages on LLM_RESULTS events."""
        # Arrange
        run_id = "run_123"
        session_id = "session_456"
        ai_content = "I'm doing well, thank you for asking!"
        
        # Create the LLM_RESULTS message
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.AI,
            content={
                "content": ai_content,
                "tool_calls": None
            }
        )

        # Act
        await persistence_service.handle_llm_result(message)

        # Assert
        mock_database_service.insert_message_async.assert_called_once()
        persisted_message = mock_database_service.insert_message_async.call_args[0][0]
        assert persisted_message.role == Role.AI
        assert persisted_message.content == ai_content
        assert persisted_message.run_id == run_id
        assert persisted_message.session_id == session_id

    @pytest.mark.asyncio
    async def test_persists_tool_message_on_tool_result(self, persistence_service, mock_database_service):
        """Test that PersistenceService persists tool messages on TOOLS_RESULTS events."""
        # Arrange
        run_id = "run_123"
        session_id = "session_456"
        tool_name = "calculator"
        tool_result = "42"
        
        # Create the TOOLS_RESULTS message
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.SYSTEM,
            content={
                "tool_name": tool_name,
                "result": tool_result,
                "status": "success",
                "call_id": "call_789"
            }
        )

        # Act
        await persistence_service.handle_tool_result(message)

        # Assert
        mock_database_service.insert_message_async.assert_called_once()
        persisted_message = mock_database_service.insert_message_async.call_args[0][0]
        assert persisted_message.role == Role.TOOL
        assert persisted_message.content == tool_result
        assert persisted_message.run_id == run_id
        assert persisted_message.session_id == session_id
        assert persisted_message.metadata["tool_name"] == tool_name

    @pytest.mark.asyncio
    async def test_skips_system_role_llm_messages(self, persistence_service, mock_database_service):
        """Test that PersistenceService skips SYSTEM role LLM messages (streaming events)."""
        # Arrange
        run_id = "run_123"
        session_id = "session_456"
        
        # Create a SYSTEM role LLM_RESULTS message (streaming event)
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.SYSTEM,
            content={
                "content": "streaming chunk",
                "tool_calls": None
            }
        )

        # Act
        await persistence_service.handle_llm_result(message)

        # Assert
        mock_database_service.insert_message_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_empty_tool_results(self, persistence_service, mock_database_service):
        """Test that PersistenceService skips empty tool results."""
        # Arrange
        run_id = "run_123"
        session_id = "session_456"
        
        # Create an empty tool result message
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.SYSTEM,
            content={
                "tool_name": "calculator",
                "result": "",
                "status": "success",
                "call_id": "call_789"
            }
        )

        # Act
        await persistence_service.handle_tool_result(message)

        # Assert
        mock_database_service.insert_message_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_llm_result_with_tool_calls(self, persistence_service, mock_database_service):
        """Test that PersistenceService handles LLM results with tool calls correctly."""
        # Arrange
        run_id = "run_123"
        session_id = "session_456"
        ai_content = "I'll use the calculator tool to help you."
        tool_calls = [{"function": {"name": "calculator", "arguments": "{\"expression\": \"2+2\"}"}}]
        
        # Create the LLM_RESULTS message with tool calls
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.AI,
            content={
                "content": ai_content,
                "tool_calls": tool_calls
            }
        )

        # Act
        await persistence_service.handle_llm_result(message)

        # Assert
        mock_database_service.insert_message_async.assert_called_once()
        persisted_message = mock_database_service.insert_message_async.call_args[0][0]
        assert persisted_message.role == Role.AI
        assert persisted_message.content == ai_content
        assert persisted_message.metadata["has_tool_calls"] is True
        assert persisted_message.metadata["tool_calls"] == tool_calls