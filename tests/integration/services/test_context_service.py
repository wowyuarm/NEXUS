"""Integration tests for ContextService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, mock_open
from nexus.core.models import Message, Role
from nexus.core.topics import Topics
from nexus.services.context import ContextService


class TestContextService:
    """Test suite for ContextService integration behavior."""

    @pytest.fixture
    def mock_bus(self, mocker):
        """Fixture providing a mock NexusBus with publish method."""
        mock_bus = mocker.MagicMock()
        mock_bus.publish = AsyncMock()
        return mock_bus

    @pytest.fixture
    def mock_tool_registry(self, mocker):
        """Fixture providing a mock ToolRegistry with get_all_tool_definitions method."""
        mock_registry = mocker.MagicMock()
        return mock_registry

    @pytest.fixture
    def mock_persistence_service(self, mocker):
        """Fixture providing a mock PersistenceService with get_history method."""
        mock_persistence = mocker.MagicMock()
        mock_persistence.get_history = AsyncMock()
        return mock_persistence

    @pytest.fixture
    def mock_config_service(self, mocker):
        """Fixture providing a mock ConfigService with get_int method."""
        mock_config = mocker.MagicMock()
        mock_config.get_int = mocker.MagicMock(return_value=20)
        return mock_config

    @pytest.fixture
    def context_service(self, mock_bus, mock_tool_registry, mock_persistence_service, mock_config_service):
        """Fixture providing a ContextService instance with mocked dependencies."""
        service = ContextService(
            bus=mock_bus,
            tool_registry=mock_tool_registry,
            config_service=mock_config_service,
            persistence_service=mock_persistence_service
        )
        return service

    @pytest.mark.asyncio
    async def test_build_request_with_history_and_tools(
        self, context_service, mock_bus, mock_tool_registry, mock_persistence_service, mocker
    ):
        """Test that ContextService builds context with history and tools correctly."""
        # Arrange
        run_id = "run_123"
        session_id = "session_456"
        current_input = "Hello, how are you?"
        
        # Mock history messages
        history_messages = [
            {"role": "human", "content": "Previous user message"},
            {"role": "ai", "content": "Previous AI response"}
        ]
        mock_persistence_service.get_history.return_value = history_messages
        
        # Mock tool definitions
        tool_definition = {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "A test tool for debugging",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "A message"}
                    }
                }
            }
        }
        mock_tool_registry.get_all_tool_definitions.return_value = [tool_definition]
        
        # Mock prompt file loading
        fake_persona_content = "You are Xi, an AI assistant."
        fake_tools_content = "Available tools: test_tool"
        mocker.patch("builtins.open", mock_open(read_data=fake_persona_content))
        mocker.patch(
            "nexus.services.context.ContextService._load_prompt_file",
            side_effect=lambda prompts_dir, filename, fallback: 
                fake_persona_content if filename == "persona.md" else fake_tools_content
        )
        
        # Create the CONTEXT_BUILD_REQUEST message
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.SYSTEM,
            content={"current_input": current_input}
        )
        
        # Act
        await context_service.handle_build_request(message)
        
        # Assert
        # Verify persistence service was called
        mock_persistence_service.get_history.assert_called_once_with(session_id, 20)
        
        # Verify tool registry was called
        mock_tool_registry.get_all_tool_definitions.assert_called_once()
        
        # Verify bus publish was called with correct response
        mock_bus.publish.assert_called_once()
        publish_call = mock_bus.publish.call_args
        assert publish_call[0][0] == Topics.CONTEXT_BUILD_RESPONSE
        
        response_message = publish_call[0][1]
        assert response_message.run_id == run_id
        assert response_message.session_id == session_id
        assert response_message.role == Role.SYSTEM
        
        content = response_message.content
        assert content["status"] == "success"
        assert len(content["messages"]) == 4  # system prompt + 2 history + current input
        assert content["messages"][0]["role"] == "system"
        assert content["messages"][1]["role"] == "assistant"  # Second history message (ai) - processed in reverse
        assert content["messages"][2]["role"] == "user"  # First history message (human) - processed in reverse
        assert content["messages"][3]["role"] == "user"  # Current input
        assert content["messages"][3]["content"] == current_input
        
        assert len(content["tools"]) == 1
        assert content["tools"][0] == tool_definition

    @pytest.mark.asyncio
    async def test_build_request_without_persistence_service(
        self, context_service, mock_bus, mock_tool_registry, mocker
    ):
        """Test that ContextService works without persistence service."""
        # Arrange - create service without persistence service
        service = ContextService(
            bus=mock_bus,
            tool_registry=mock_tool_registry,
            config_service=None,
            persistence_service=None
        )
        
        run_id = "run_123"
        session_id = "session_456"
        current_input = "Hello, how are you?"
        
        # Mock tool definitions
        tool_definition = {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "A test tool for debugging"
            }
        }
        mock_tool_registry.get_all_tool_definitions.return_value = [tool_definition]
        
        # Mock prompt file loading
        fake_persona_content = "You are Xi, an AI assistant."
        mocker.patch("builtins.open", mock_open(read_data=fake_persona_content))
        mocker.patch(
            "nexus.services.context.ContextService._load_prompt_file",
            return_value=fake_persona_content
        )
        
        # Create the CONTEXT_BUILD_REQUEST message
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.SYSTEM,
            content={"current_input": current_input}
        )
        
        # Act
        await service.handle_build_request(message)
        
        # Assert
        # Verify tool registry was called
        mock_tool_registry.get_all_tool_definitions.assert_called_once()
        
        # Verify bus publish was called with correct response
        mock_bus.publish.assert_called_once()
        publish_call = mock_bus.publish.call_args
        response_message = publish_call[0][1]
        
        content = response_message.content
        assert content["status"] == "success"
        assert len(content["messages"]) == 2  # system prompt + current input (no history)
        assert content["messages"][0]["role"] == "system"
        assert content["messages"][1]["role"] == "user"
        assert content["messages"][1]["content"] == current_input

    @pytest.mark.asyncio
    async def test_build_request_persistence_service_failure(
        self, context_service, mock_bus, mock_tool_registry, mock_persistence_service, mocker
    ):
        """Test that ContextService handles persistence service failures gracefully."""
        # Arrange
        run_id = "run_123"
        session_id = "session_456"
        current_input = "Hello, how are you?"
        
        # Mock persistence service to raise an exception
        mock_persistence_service.get_history.side_effect = Exception("Database connection failed")
        
        # Mock tool definitions
        tool_definition = {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "A test tool for debugging"
            }
        }
        mock_tool_registry.get_all_tool_definitions.return_value = [tool_definition]
        
        # Mock prompt file loading
        fake_persona_content = "You are Xi, an AI assistant."
        mocker.patch("builtins.open", mock_open(read_data=fake_persona_content))
        mocker.patch(
            "nexus.services.context.ContextService._load_prompt_file",
            return_value=fake_persona_content
        )
        
        # Create the CONTEXT_BUILD_REQUEST message
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.SYSTEM,
            content={"current_input": current_input}
        )
        
        # Act
        await context_service.handle_build_request(message)
        
        # Assert
        # Verify persistence service was called and failed
        mock_persistence_service.get_history.assert_called_once_with(session_id, 20)
        
        # Verify tool registry was called
        mock_tool_registry.get_all_tool_definitions.assert_called_once()
        
        # Verify bus publish was called with success response (should continue without history)
        mock_bus.publish.assert_called_once()
        publish_call = mock_bus.publish.call_args
        response_message = publish_call[0][1]
        
        content = response_message.content
        assert content["status"] == "success"
        assert len(content["messages"]) == 2  # system prompt + current input (history loading failed)

    @pytest.mark.asyncio
    async def test_build_request_prompt_file_load_failure(
        self, context_service, mock_bus, mock_tool_registry, mock_persistence_service, mocker
    ):
        """Test that ContextService handles prompt file loading failures gracefully."""
        # Arrange
        run_id = "run_123"
        session_id = "session_456"
        current_input = "Hello, how are you?"
        
        # Mock history messages
        history_messages = [
            {"role": "human", "content": "Previous user message"}
        ]
        mock_persistence_service.get_history.return_value = history_messages
        
        # Mock tool definitions
        tool_definition = {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "A test tool for debugging"
            }
        }
        mock_tool_registry.get_all_tool_definitions.return_value = [tool_definition]
        
        # Mock prompt file loading to fail
        mocker.patch(
            "nexus.services.context.ContextService._load_system_prompt",
            side_effect=Exception("File not found")
        )
        
        # Create the CONTEXT_BUILD_REQUEST message
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.SYSTEM,
            content={"current_input": current_input}
        )
        
        # Act
        await context_service.handle_build_request(message)
        
        # Assert
        # Verify persistence service was NOT called (early return due to prompt loading failure)
        mock_persistence_service.get_history.assert_not_called()
        
        # Verify tool registry was NOT called (early return due to prompt loading failure)
        mock_tool_registry.get_all_tool_definitions.assert_not_called()
        
        # Verify bus publish was called with error response
        mock_bus.publish.assert_called_once()
        publish_call = mock_bus.publish.call_args
        response_message = publish_call[0][1]
        
        content = response_message.content
        assert content["status"] == "error"
        assert content["messages"] == []
        assert content["tools"] == []

    @pytest.mark.asyncio
    async def test_build_request_empty_current_input(
        self, context_service, mock_bus, mock_persistence_service
    ):
        """Test that ContextService handles empty current input gracefully."""
        # Arrange
        run_id = "run_123"
        session_id = "session_456"
        
        # Create the CONTEXT_BUILD_REQUEST message with empty input
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.SYSTEM,
            content={"current_input": ""}
        )
        
        # Act
        await context_service.handle_build_request(message)
        
        # Assert
        # Verify persistence service was not called (early return)
        mock_persistence_service.get_history.assert_not_called()
        
        # Verify bus publish was not called (early return)
        mock_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_build_request_missing_current_input(
        self, context_service, mock_bus, mock_persistence_service
    ):
        """Test that ContextService handles missing current input gracefully."""
        # Arrange
        run_id = "run_123"
        session_id = "session_456"
        
        # Create the CONTEXT_BUILD_REQUEST message without current_input
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.SYSTEM,
            content={}  # Missing current_input
        )
        
        # Act
        await context_service.handle_build_request(message)
        
        # Assert
        # Verify persistence service was not called (early return)
        mock_persistence_service.get_history.assert_not_called()
        
        # Verify bus publish was not called (early return)
        mock_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_build_request_with_tool_role_history(
        self, context_service, mock_bus, mock_tool_registry, mock_persistence_service, mocker
    ):
        """Test that ContextService correctly handles tool role messages in history."""
        # Arrange
        run_id = "run_123"
        session_id = "session_456"
        current_input = "Hello, how are you?"
        
        # Mock history messages including tool role
        history_messages = [
            {"role": "human", "content": "User question"},
            {"role": "ai", "content": "AI response with tool call"},
            {"role": "tool", "content": "Tool result", "metadata": {"tool_name": "test_tool"}}
        ]
        mock_persistence_service.get_history.return_value = history_messages
        
        # Mock tool definitions
        tool_definition = {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "A test tool for debugging"
            }
        }
        mock_tool_registry.get_all_tool_definitions.return_value = [tool_definition]
        
        # Mock prompt file loading
        fake_persona_content = "You are Xi, an AI assistant."
        mocker.patch("builtins.open", mock_open(read_data=fake_persona_content))
        mocker.patch(
            "nexus.services.context.ContextService._load_prompt_file",
            return_value=fake_persona_content
        )
        
        # Create the CONTEXT_BUILD_REQUEST message
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.SYSTEM,
            content={"current_input": current_input}
        )
        
        # Act
        await context_service.handle_build_request(message)
        
        # Assert
        # Verify bus publish was called
        mock_bus.publish.assert_called_once()
        publish_call = mock_bus.publish.call_args
        response_message = publish_call[0][1]
        
        content = response_message.content
        assert content["status"] == "success"
        # Should include all 3 history messages + system prompt + current input = 5 total
        assert len(content["messages"]) == 5
        # Tool role should be converted to proper LLM tool role format (processed in reverse)
        assert content["messages"][1]["role"] == "tool"  # Tool message from history
