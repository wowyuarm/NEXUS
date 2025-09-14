"""
Unit tests for ContextService.

These tests verify that ContextService correctly handles system prompt loading
and LLM message formatting logic. All external dependencies (file system, database)
are mocked to ensure isolation and precise testing of internal logic.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, mock_open, patch
import os

from nexus.services.context import ContextService
from nexus.core.models import Message, Role
from nexus.core.topics import Topics


class TestLoadSystemPrompt:
    """Test suite for _load_system_prompt method."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for ContextService."""
        mock_bus = Mock()
        mock_tool_registry = Mock()
        mock_config_service = Mock()
        mock_persistence_service = Mock()
        return mock_bus, mock_tool_registry, mock_config_service, mock_persistence_service

    @pytest.fixture
    def context_service(self, mock_dependencies):
        """Create ContextService instance with mocked dependencies."""
        bus, tool_registry, config_service, persistence_service = mock_dependencies
        return ContextService(
            bus=bus,
            tool_registry=tool_registry,
            config_service=config_service,
            persistence_service=persistence_service
        )

    def test_loads_and_combines_all_prompts(self, context_service, mocker):
        """Test that _load_system_prompt loads and combines all prompt files correctly."""
        # Arrange: Mock file contents
        persona_content = "You are Xi, a helpful AI assistant."
        system_content = "Follow these system guidelines..."
        tools_content = "Available tools: search, calculate..."
        
        # Mock file operations for all three files
        mock_files = {
            'persona.md': persona_content,
            'system.md': system_content,
            'tools.md': tools_content
        }
        
        def mock_open_side_effect(file_path, *args, **kwargs):
            filename = os.path.basename(file_path)
            if filename in mock_files:
                return mock_open(read_data=mock_files[filename])()
            else:
                raise FileNotFoundError(f"No such file: {file_path}")
        
        mocker.patch('builtins.open', side_effect=mock_open_side_effect)

        # Act: Load system prompt
        result = context_service._load_system_prompt()

        # Assert: Verify content is combined correctly with separators
        expected_content = f"{persona_content}\n\n---\n\n{system_content}\n\n---\n\n{tools_content}"
        assert result == expected_content

    def test_handles_missing_prompt_files_gracefully(self, context_service, mocker):
        """Test that _load_system_prompt handles missing files gracefully."""
        # Arrange: Mock only persona.md exists, others are missing
        persona_content = "You are Xi, a helpful AI assistant."
        
        def mock_open_side_effect(file_path, *args, **kwargs):
            filename = os.path.basename(file_path)
            if filename == 'persona.md':
                return mock_open(read_data=persona_content)()
            else:
                raise FileNotFoundError(f"No such file: {file_path}")
        
        mocker.patch('builtins.open', side_effect=mock_open_side_effect)

        # Act: Load system prompt
        result = context_service._load_system_prompt()

        # Assert: Verify only persona content is returned (others default to empty)
        assert result == persona_content

    def test_handles_partial_missing_files(self, context_service, mocker):
        """Test handling when some files exist and others don't."""
        # Arrange: Mock persona.md and tools.md exist, system.md is missing
        persona_content = "You are Xi, a helpful AI assistant."
        tools_content = "Available tools: search, calculate..."
        
        def mock_open_side_effect(file_path, *args, **kwargs):
            filename = os.path.basename(file_path)
            if filename == 'persona.md':
                return mock_open(read_data=persona_content)()
            elif filename == 'tools.md':
                return mock_open(read_data=tools_content)()
            else:
                raise FileNotFoundError(f"No such file: {file_path}")
        
        mocker.patch('builtins.open', side_effect=mock_open_side_effect)

        # Act: Load system prompt
        result = context_service._load_system_prompt()

        # Assert: Verify available content is combined correctly
        expected_content = f"{persona_content}\n\n---\n\n{tools_content}"
        assert result == expected_content

    def test_returns_fallback_on_file_read_error(self, context_service, mocker):
        """Test that _load_system_prompt returns fallback prompt on file read errors."""
        # Arrange: Mock all file operations to raise IOError
        mocker.patch('builtins.open', side_effect=IOError("Permission denied"))

        # Act: Load system prompt
        result = context_service._load_system_prompt()

        # Assert: Verify fallback prompt is returned
        expected_fallback = "You are Xi, an AI assistant. Please respond helpfully and thoughtfully."
        assert result == expected_fallback

    def test_returns_fallback_on_empty_files(self, context_service, mocker):
        """Test that _load_system_prompt returns fallback when all files are empty."""
        # Arrange: Mock all files to be empty
        mocker.patch('builtins.open', mock_open(read_data=""))

        # Act: Load system prompt
        result = context_service._load_system_prompt()

        # Assert: Verify fallback prompt is returned when no content
        expected_fallback = "You are Xi, an AI assistant. Please respond helpfully and thoughtfully."
        assert result == expected_fallback

    def test_handles_whitespace_only_files(self, context_service, mocker):
        """Test handling of files that contain only whitespace."""
        # Arrange: Mock files with whitespace content
        persona_content = "   \n\t  \n   "  # Only whitespace
        system_content = "Actual system content"
        
        def mock_open_side_effect(file_path, *args, **kwargs):
            filename = os.path.basename(file_path)
            if filename == 'persona.md':
                return mock_open(read_data=persona_content)()
            elif filename == 'system.md':
                return mock_open(read_data=system_content)()
            else:
                raise FileNotFoundError(f"No such file: {file_path}")
        
        mocker.patch('builtins.open', side_effect=mock_open_side_effect)

        # Act: Load system prompt
        result = context_service._load_system_prompt()

        # Assert: Verify whitespace-only content is included but actual content dominates
        expected_content = f"{persona_content}\n\n---\n\n{system_content}"
        assert result == expected_content


class TestFormatLlmMessages:
    """Test suite for _format_llm_messages method."""

    @pytest.fixture
    def context_service(self):
        """Create ContextService instance for testing pure logic methods."""
        # For testing pure logic methods, we only need minimal setup
        mock_bus = Mock()
        mock_tool_registry = Mock()
        return ContextService(bus=mock_bus, tool_registry=mock_tool_registry)

    def test_formats_with_history(self, context_service):
        """Test that _format_llm_messages correctly formats messages with conversation history."""
        # Arrange: Prepare test data
        system_prompt = "You are Xi, an AI assistant."
        history_from_db = [
            {"role": "human", "content": "Hello, how are you?"},
            {"role": "ai", "content": "I'm doing well, thank you! How can I help you today?"},
            {"role": "human", "content": "What's the weather like?"},
            {"role": "ai", "content": "I don't have access to current weather data, but I can help you find weather information."}
        ]
        current_input = "Can you help me with Python?"

        # Act: Format messages
        result = context_service._format_llm_messages(system_prompt, history_from_db, current_input)

        # Assert: Verify message structure, role mapping, and order
        # Note: history_from_db is reversed by _format_llm_messages, so the order is reversed
        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": "I don't have access to current weather data, but I can help you find weather information."},
            {"role": "user", "content": "What's the weather like?"},
            {"role": "assistant", "content": "I'm doing well, thank you! How can I help you today?"},
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "user", "content": current_input}
        ]
        
        assert result == expected_messages
        assert len(result) == 6
        assert result[0]["role"] == "system"
        assert result[-1]["role"] == "user"
        assert result[-1]["content"] == current_input

    def test_correctly_ignores_tool_messages(self, context_service):
        """Test that _format_llm_messages correctly ignores TOOL role messages."""
        # Arrange: Prepare history with tool messages
        system_prompt = "You are Xi, an AI assistant."
        history_from_db = [
            {"role": "human", "content": "Search for Python tutorials"},
            {"role": "tool", "content": "Search results: ..."},  # Should be ignored
            {"role": "ai", "content": "Here are some great Python tutorials I found."},
            {"role": "tool", "content": "Another tool response"},  # Should be ignored
            {"role": "human", "content": "Thanks!"}
        ]
        current_input = "What about advanced topics?"

        # Act: Format messages
        result = context_service._format_llm_messages(system_prompt, history_from_db, current_input)

        # Assert: Verify tool messages are excluded
        # Note: history_from_db is reversed by _format_llm_messages
        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Thanks!"},
            {"role": "assistant", "content": "Here are some great Python tutorials I found."},
            {"role": "user", "content": "Search for Python tutorials"},
            {"role": "user", "content": current_input}
        ]
        
        assert result == expected_messages
        assert len(result) == 5
        
        # Verify no tool messages are present
        for message in result:
            assert message["role"] != "tool"

    def test_formats_with_empty_history(self, context_service):
        """Test that _format_llm_messages handles empty history correctly."""
        # Arrange: Prepare test data with empty history
        system_prompt = "You are Xi, an AI assistant."
        history_from_db = []
        current_input = "Hello, this is my first message!"

        # Act: Format messages
        result = context_service._format_llm_messages(system_prompt, history_from_db, current_input)

        # Assert: Verify only system prompt and current input are present
        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": current_input}
        ]
        
        assert result == expected_messages
        assert len(result) == 2

    def test_handles_none_content_gracefully(self, context_service):
        """Test that _format_llm_messages handles None content values gracefully."""
        # Arrange: Prepare history with None content
        system_prompt = "You are Xi, an AI assistant."
        history_from_db = [
            {"role": "human", "content": None},  # None content
            {"role": "ai", "content": "I can help you with that."},
            {"role": "human", "content": ""},  # Empty string content
            {"role": "ai", "content": "   "}  # Whitespace-only content
        ]
        current_input = "What can you do?"

        # Act: Format messages
        result = context_service._format_llm_messages(system_prompt, history_from_db, current_input)

        # Assert: Verify only non-empty messages are included
        # Note: history_from_db is reversed by _format_llm_messages
        # Empty and whitespace-only content is filtered out by content_str.strip()
        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": "I can help you with that."},
            {"role": "user", "content": current_input}
        ]
        
        assert result == expected_messages
        assert len(result) == 3

    def test_handles_unknown_roles_gracefully(self, context_service):
        """Test that _format_llm_messages ignores messages with unknown roles."""
        # Arrange: Prepare history with unknown roles
        system_prompt = "You are Xi, an AI assistant."
        history_from_db = [
            {"role": "human", "content": "Hello"},
            {"role": "unknown_role", "content": "This should be ignored"},
            {"role": "ai", "content": "Hi there!"},
            {"role": "system", "content": "This system message should be ignored"},  # Not the main system prompt
            {"role": "HUMAN", "content": "Case sensitive test"}  # Wrong case
        ]
        current_input = "How are you?"

        # Act: Format messages
        result = context_service._format_llm_messages(system_prompt, history_from_db, current_input)

        # Assert: Verify only valid roles are included
        # Note: history_from_db is reversed by _format_llm_messages
        # "HUMAN" gets converted to lowercase "human" and is processed as valid
        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Case sensitive test"},  # HUMAN -> human -> user
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "Hello"},
            {"role": "user", "content": current_input}
        ]
        
        assert result == expected_messages
        assert len(result) == 5

    def test_preserves_message_order_from_database(self, context_service):
        """Test that _format_llm_messages preserves chronological order from reversed database results."""
        # Arrange: Database returns messages in reverse chronological order (newest first)
        system_prompt = "You are Xi, an AI assistant."
        history_from_db = [
            {"role": "ai", "content": "Message 4 (newest)"},
            {"role": "human", "content": "Message 3"},
            {"role": "ai", "content": "Message 2"},
            {"role": "human", "content": "Message 1 (oldest)"}
        ]
        current_input = "Message 5 (current)"

        # Act: Format messages
        result = context_service._format_llm_messages(system_prompt, history_from_db, current_input)

        # Assert: Verify messages are in correct chronological order
        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Message 1 (oldest)"},
            {"role": "assistant", "content": "Message 2"},
            {"role": "user", "content": "Message 3"},
            {"role": "assistant", "content": "Message 4 (newest)"},
            {"role": "user", "content": current_input}
        ]
        
        assert result == expected_messages
        
        # Verify the order is correct
        content_order = [msg["content"] for msg in result[1:]]  # Skip system message
        expected_order = [
            "Message 1 (oldest)",
            "Message 2", 
            "Message 3",
            "Message 4 (newest)",
            "Message 5 (current)"
        ]
        assert content_order == expected_order

    def test_handles_mixed_content_types(self, context_service):
        """Test that _format_llm_messages handles different content types correctly."""
        # Arrange: Prepare history with various content types
        system_prompt = "You are Xi, an AI assistant."
        history_from_db = [
            {"role": "human", "content": 123},  # Number content
            {"role": "ai", "content": ["list", "content"]},  # List content (converted to string)
            {"role": "human", "content": {"dict": "content"}},  # Dict content (converted to string)
            {"role": "ai", "content": "Normal string content"}
        ]
        current_input = "What about this?"

        # Act: Format messages
        result = context_service._format_llm_messages(system_prompt, history_from_db, current_input)

        # Assert: Verify all content is converted to strings
        # Note: history_from_db is reversed by _format_llm_messages
        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": "Normal string content"},
            {"role": "user", "content": "{'dict': 'content'}"},
            {"role": "assistant", "content": "['list', 'content']"},
            {"role": "user", "content": "123"},
            {"role": "user", "content": current_input}
        ]
        
        assert result == expected_messages
        
        # Verify all content values are strings
        for message in result:
            assert isinstance(message["content"], str)
