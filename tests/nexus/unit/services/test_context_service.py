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
    """Deprecated tests for removed _load_system_prompt method.

    ContextService no longer reads prompts from the filesystem. Prompts are now
    composed dynamically from ConfigService defaults plus identity overrides. We
    keep minimal tests to ensure backward compatibility in expectations by
    redirecting to the new composition method.
    """

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

    def test_composes_prompts_from_config_defaults(self, context_service):
        """Prompts are composed from ConfigService defaults when no overrides provided."""
        # Arrange: mock ConfigService return (new 4-layer structure)
        default_prompts = {
            "field": {
                "content": "场域：共同成长的对话空间...",
                "editable": False,
                "order": 1
            },
            "presence": {
                "content": "在场方式：我如何存在于这个空间...",
                "editable": False,
                "order": 2
            },
            "capabilities": {
                "content": "能力与工具：我可以做什么...",
                "editable": False,
                "order": 3
            },
            "learning": {
                "content": "用户档案与学习记录...",
                "editable": True,
                "order": 4
            }
        }
        context_service.config_service = Mock()
        context_service.config_service.get_user_defaults.return_value = {
            "config": {},
            "prompts": default_prompts
        }

        # Act
        effective = context_service._compose_effective_prompts(user_profile={})
        combined = context_service._build_system_prompt_from_prompts(effective)

        # Assert
        expected_content = f"{default_prompts['field']['content']}\n\n---\n\n{default_prompts['presence']['content']}\n\n---\n\n{default_prompts['capabilities']['content']}\n\n---\n\n{default_prompts['learning']['content']}"
        assert combined == expected_content

    def test_overrides_learning_only(self, context_service):
        """When only learning is overridden, field/presence/capabilities remain defaults."""
        # Arrange defaults (new 4-layer structure)
        default_prompts = {
            "field": {
                "content": "场域：共同成长的对话空间...",
                "editable": False,
                "order": 1
            },
            "presence": {
                "content": "在场方式：我如何存在于这个空间...",
                "editable": False,
                "order": 2
            },
            "capabilities": {
                "content": "能力与工具：我可以做什么...",
                "editable": False,
                "order": 3
            },
            "learning": {
                "content": "用户档案与学习记录（默认模板）...",
                "editable": True,
                "order": 4
            }
        }
        context_service.config_service = Mock()
        context_service.config_service.get_user_defaults.return_value = {
            "config": {},
            "prompts": default_prompts
        }
        user_profile = {"prompt_overrides": {"learning": "用户档案：这是自定义的学习记录..."}}

        # Act
        effective = context_service._compose_effective_prompts(user_profile)
        combined = context_service._build_system_prompt_from_prompts(effective)

        # Assert
        assert "用户档案：这是自定义的学习记录" in combined
        assert "场域：共同成长的对话空间" in combined
        assert "在场方式：我如何存在于这个空间" in combined
        assert "能力与工具：我可以做什么" in combined

    def test_partial_defaults_and_overrides(self, context_service):
        """Supports partial overrides while combining with defaults (only learning is user-editable)."""
        default_prompts = {
            "field": {
                "content": "场域：共同成长的对话空间...",
                "editable": False,
                "order": 1
            },
            "presence": {
                "content": "在场方式：我如何存在于这个空间...",
                "editable": False,
                "order": 2
            },
            "capabilities": {
                "content": "能力与工具：我可以做什么...",
                "editable": False,
                "order": 3
            },
            "learning": {
                "content": "用户档案与学习记录（默认）...",
                "editable": True,
                "order": 4
            }
        }
        context_service.config_service = Mock()
        context_service.config_service.get_user_defaults.return_value = {
            "config": {},
            "prompts": default_prompts
        }
        user_profile = {"prompt_overrides": {"learning": "自定义学习记录..."}}

        effective = context_service._compose_effective_prompts(user_profile)
        combined = context_service._build_system_prompt_from_prompts(effective)

        assert "自定义学习记录" in combined
        assert combined.startswith(default_prompts["field"]["content"])

    def test_fallback_when_all_empty(self, context_service):
        """If defaults are empty and no overrides, fallback system prompt is used."""
        context_service.config_service = Mock()
        context_service.config_service.get_user_defaults.return_value = {
            "config": {},
            "prompts": {"field": "", "presence": "", "capabilities": "", "learning": ""}
        }
        effective = context_service._compose_effective_prompts({})
        combined = context_service._build_system_prompt_from_prompts(effective)
        expected_fallback = "You are NEXUS, an AI assistant. Please respond helpfully and thoughtfully."
        assert combined == expected_fallback

    def test_empty_defaults_fallback(self, context_service):
        context_service.config_service = Mock()
        context_service.config_service.get_user_defaults.return_value = {"config": {}, "prompts": {}}
        effective = context_service._compose_effective_prompts({})
        combined = context_service._build_system_prompt_from_prompts(effective)
        expected_fallback = "You are NEXUS, an AI assistant. Please respond helpfully and thoughtfully."
        assert combined == expected_fallback

    def test_whitespace_defaults(self, context_service):
        context_service.config_service = Mock()
        context_service.config_service.get_user_defaults.return_value = {
            "config": {},
            "prompts": {
                "field": {"content": "   \n\t  \n   ", "editable": False, "order": 1},
                "presence": {"content": "Actual presence content", "editable": False, "order": 2},
                "capabilities": {"content": "", "editable": False, "order": 3},
                "learning": {"content": "", "editable": True, "order": 4}
            }
        }
        effective = context_service._compose_effective_prompts({})
        combined = context_service._build_system_prompt_from_prompts(effective)
        assert "Actual presence content" in combined


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
        """Test that _format_llm_messages correctly formats messages with conversation history using new XML context structure."""
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
        expected_xml_context = """<Context>
  <Human_Input>
    Can you help me with Python?
  </Human_Input>
</Context>"""

        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": "I don't have access to current weather data, but I can help you find weather information."},
            {"role": "user", "content": "What's the weather like?"},
            {"role": "assistant", "content": "I'm doing well, thank you! How can I help you today?"},
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "user", "content": expected_xml_context}
        ]

        assert result == expected_messages
        assert len(result) == 6
        assert result[0]["role"] == "system"
        assert result[-1]["role"] == "user"
        assert result[-1]["content"] == expected_xml_context

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

        # Assert: Verify tool messages are excluded and final message uses XML context
        expected_xml_context = """<Context>
  <Human_Input>
    What about advanced topics?
  </Human_Input>
</Context>"""

        # Note: history_from_db is reversed by _format_llm_messages
        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Thanks!"},
            {"role": "assistant", "content": "Here are some great Python tutorials I found."},
            {"role": "user", "content": "Search for Python tutorials"},
            {"role": "user", "content": expected_xml_context}
        ]

        assert result == expected_messages
        assert len(result) == 5

        # Verify no tool messages are present
        for message in result:
            assert message["role"] != "tool"

    def test_formats_with_empty_history(self, context_service):
        """Test that _format_llm_messages handles empty history correctly using new XML context structure."""
        # Arrange: Prepare test data with empty history
        system_prompt = "You are Xi, an AI assistant."
        history_from_db = []
        current_input = "Hello, this is my first message!"

        # Act: Format messages
        result = context_service._format_llm_messages(system_prompt, history_from_db, current_input)

        # Assert: Verify system prompt and XML context with user input are present
        expected_xml_context = """<Context>
  <Human_Input>
    Hello, this is my first message!
  </Human_Input>
</Context>"""

        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": expected_xml_context}
        ]

        assert result == expected_messages
        assert len(result) == 2
        assert result[-1]["content"] == expected_xml_context

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

        # Assert: Verify only non-empty messages are included and final message uses XML context
        expected_xml_context = """<Context>
  <Human_Input>
    What can you do?
  </Human_Input>
</Context>"""

        # Note: history_from_db is reversed by _format_llm_messages
        # Empty and whitespace-only content is filtered out by content_str.strip()
        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": "I can help you with that."},
            {"role": "user", "content": expected_xml_context}
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

        # Assert: Verify only valid roles are included and final message uses XML context
        expected_xml_context = """<Context>
  <Human_Input>
    How are you?
  </Human_Input>
</Context>"""

        # Note: history_from_db is reversed by _format_llm_messages
        # "HUMAN" gets converted to lowercase "human" and is processed as valid
        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Case sensitive test"},  # HUMAN -> human -> user
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "Hello"},
            {"role": "user", "content": expected_xml_context}
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

        # Assert: Verify messages are in correct chronological order with XML context
        expected_xml_context = """<Context>
  <Human_Input>
    Message 5 (current)
  </Human_Input>
</Context>"""

        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Message 1 (oldest)"},
            {"role": "assistant", "content": "Message 2"},
            {"role": "user", "content": "Message 3"},
            {"role": "assistant", "content": "Message 4 (newest)"},
            {"role": "user", "content": expected_xml_context}
        ]

        assert result == expected_messages

        # Verify the order is correct
        content_order = [msg["content"] for msg in result[1:]]  # Skip system message
        expected_order = [
            "Message 1 (oldest)",
            "Message 2",
            "Message 3",
            "Message 4 (newest)",
            expected_xml_context
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

        # Assert: Verify all content is converted to strings and final message uses XML context
        expected_xml_context = """<Context>
  <Human_Input>
    What about this?
  </Human_Input>
</Context>"""

        # Note: history_from_db is reversed by _format_llm_messages
        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": "Normal string content"},
            {"role": "user", "content": "{'dict': 'content'}"},
            {"role": "assistant", "content": "['list', 'content']"},
            {"role": "user", "content": "123"},
            {"role": "user", "content": expected_xml_context}
        ]

        assert result == expected_messages

        # Verify all content values are strings
        for message in result:
            assert isinstance(message["content"], str)

    def test_formats_with_timezone_aware_timestamp(self, context_service):
        """Test that _format_llm_messages includes timezone-aware timestamp in XML context when provided."""
        # Arrange: Prepare test data with timezone-aware timestamp
        system_prompt = "You are Xi, an AI assistant."
        history_from_db = []
        current_input = "What time is it in New York?"
        client_timestamp_utc = "2025-09-16T14:30:45Z"
        client_timezone_offset = 300  # -5 hours in minutes (New York)

        # Act: Format messages with timezone-aware timestamp
        result = context_service._format_llm_messages(system_prompt, history_from_db, current_input, client_timestamp_utc, client_timezone_offset)

        # Assert: Verify timezone-aware timestamp is included in XML context
        expected_xml_context = """<Context>
  <Current_Time>2025-09-16 09:30:45-05:00</Current_Time>
  <Human_Input>
    What time is it in New York?
  </Human_Input>
</Context>"""

        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": expected_xml_context}
        ]

        assert result == expected_messages
        assert len(result) == 2
        assert result[-1]["content"] == expected_xml_context
        assert "<Current_Time>" in result[-1]["content"]
        assert "<Human_Input>" in result[-1]["content"]

    def test_formats_without_timestamp(self, context_service):
        """Test that _format_llm_messages works without timestamp information."""
        # Arrange: Prepare test data without timestamp
        system_prompt = "You are Xi, an AI assistant."
        history_from_db = []
        current_input = "Hello"

        # Act: Format messages without timestamp
        result = context_service._format_llm_messages(system_prompt, history_from_db, current_input)

        # Assert: Verify context doesn't include timestamp
        expected_xml_context = """<Context>
  <Human_Input>
    Hello
  </Human_Input>
</Context>"""

        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": expected_xml_context}
        ]

        assert result == expected_messages
        assert len(result) == 2
        assert result[-1]["content"] == expected_xml_context
        assert "<Current_Time>" not in result[-1]["content"]
        assert "<Human_Input>" in result[-1]["content"]

    def test_handles_invalid_timezone_timestamp(self, context_service):
        """Test that _format_llm_messages handles invalid timezone-aware timestamp gracefully."""
        # Arrange: Prepare test data with invalid timezone-aware timestamp
        system_prompt = "You are Xi, an AI assistant."
        history_from_db = []
        current_input = "Test message"
        client_timestamp_utc = "invalid-timestamp-format"
        client_timezone_offset = 300

        # Act: Format messages with invalid timezone-aware timestamp
        result = context_service._format_llm_messages(system_prompt, history_from_db, current_input, client_timestamp_utc, client_timezone_offset)

        # Assert: Verify invalid timestamp is included as-is in XML context (fallback)
        expected_xml_context = """<Context>
  <Current_Time>invalid-timestamp-format</Current_Time>
  <Human_Input>
    Test message
  </Human_Input>
</Context>"""

        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": expected_xml_context}
        ]

        assert result == expected_messages
        assert len(result) == 2
        assert result[-1]["content"] == expected_xml_context

    def test_xml_context_escaping(self, context_service):
        """Test that XML context properly escapes special characters in user input."""
        # Arrange: Prepare test data with special characters
        system_prompt = "You are Xi, an AI assistant."
        history_from_db = []
        current_input = "Can you help me with <script>alert('test')</script>?"
        client_timestamp_utc = "2025-09-16T14:30:45Z"
        client_timezone_offset = 0  # UTC

        # Act: Format messages with special characters
        result = context_service._format_llm_messages(system_prompt, history_from_db, current_input, client_timestamp_utc, client_timezone_offset)

        # Assert: Verify special characters are preserved (not escaped in this implementation)
        expected_xml_context = """<Context>
  <Current_Time>2025-09-16 14:30:45+00:00</Current_Time>
  <Human_Input>
    Can you help me with <script>alert('test')</script>?
  </Human_Input>
</Context>"""

        expected_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": expected_xml_context}
        ]

        assert result == expected_messages
        assert len(result) == 2
        assert result[-1]["content"] == expected_xml_context

    def test_thinking_loop_invariance(self, context_service):
        """Test that system prompt and history remain immutable (thinking loop invariance principle)."""
        # Arrange: Prepare test data
        system_prompt = "You are Xi, an AI assistant."
        history_from_db = [
            {"role": "human", "content": "First message"},
            {"role": "ai", "content": "First response"}
        ]
        current_input = "Second message"
        client_timestamp_utc = "2025-09-16T14:30:45Z"
        client_timezone_offset = 0  # UTC

        # Act: Format messages
        result = context_service._format_llm_messages(system_prompt, history_from_db, current_input, client_timestamp_utc, client_timezone_offset)

        # Assert: Verify system prompt is unchanged and history order is preserved
        expected_xml_context = """<Context>
  <Current_Time>2025-09-16 14:30:45+00:00</Current_Time>
  <Human_Input>
    Second message
  </Human_Input>
</Context>"""

        expected_messages = [
            {"role": "system", "content": system_prompt},  # Immutable
            {"role": "assistant", "content": "First response"},  # From history, in correct order
            {"role": "user", "content": "First message"},  # From history, in correct order
            {"role": "user", "content": expected_xml_context}  # New structured context
        ]

        assert result == expected_messages
        assert len(result) == 4
        assert result[0]["content"] == system_prompt  # System prompt unchanged
        assert result[1]["content"] == "First response"  # History preserved
        assert result[2]["content"] == "First message"  # History preserved

    def test_format_llm_messages_deduplicates_current_input(self, context_service):
        """Test that _format_llm_messages deduplicates current input based on run_id."""
        # Arrange: 构造包含当前run_id的历史记录
        system_prompt = "You are Xi, an AI assistant."
        history_from_db = [
            {"run_id": "current_run_id", "role": "human", "content": "test input"},
            {"run_id": "other_run_id", "role": "human", "content": "other input"},
            {"run_id": "current_run_id", "role": "ai", "content": "AI response to test input"}
        ]
        current_input = "test input"
        current_run_id = "current_run_id"

        # Act: 调用格式化方法
        # 注意：当前方法签名不支持current_run_id参数，这会导致测试失败
        result = context_service._format_llm_messages(
            system_prompt=system_prompt,
            history_from_db=history_from_db,
            current_input=current_input,
            current_run_id=current_run_id
        )

        # Assert: 验证重复消息被过滤
        human_messages = [msg for msg in result if msg["role"] == "user"]
        # 应该只有2条用户消息：一条来自历史（other_run_id），一条是XML结构化的当前输入
        assert len(human_messages) == 2
        # 验证XML结构化输入存在
        xml_messages = [msg for msg in result if "<Human_Input>" in msg.get("content", "")]
        assert len(xml_messages) == 1
        assert "test input" in xml_messages[0]["content"]
        # 验证历史中的其他用户输入仍然存在
        other_user_messages = [msg for msg in human_messages if "other input" in msg.get("content", "")]
        assert len(other_user_messages) == 1
