"""Unit tests for prompt management."""

import pytest

from nexus.services.context.prompts import PromptManager, CORE_IDENTITY


class TestCoreIdentity:
    """Tests for CORE_IDENTITY constant."""

    def test_core_identity_not_empty(self):
        """CORE_IDENTITY is not empty."""
        assert CORE_IDENTITY
        assert len(CORE_IDENTITY) > 100

    def test_core_identity_contains_nexus(self):
        """CORE_IDENTITY mentions Nexus."""
        assert "Nexus" in CORE_IDENTITY

    def test_core_identity_contains_key_sections(self):
        """CORE_IDENTITY contains expected sections."""
        assert "dialogue space" in CORE_IDENTITY.lower()
        assert "friend" in CORE_IDENTITY.lower()
        assert "[CAPABILITIES]" in CORE_IDENTITY
        assert "[SHARED_MEMORY]" in CORE_IDENTITY
        assert "[FRIENDS_INFO]" in CORE_IDENTITY
        assert "[THIS_MOMENT]" in CORE_IDENTITY

    def test_core_identity_language_instruction(self):
        """CORE_IDENTITY has language matching instruction."""
        assert "human_input" in CORE_IDENTITY.lower()
        assert "language" in CORE_IDENTITY.lower()


class TestPromptManager:
    """Tests for PromptManager class."""

    def test_get_core_identity_returns_content(self):
        """get_core_identity returns non-empty string."""
        manager = PromptManager()
        result = manager.get_core_identity()

        assert result
        assert isinstance(result, str)
        assert "Nexus" in result

    def test_get_core_identity_stripped(self):
        """get_core_identity returns stripped content."""
        manager = PromptManager()
        result = manager.get_core_identity()

        assert result == result.strip()

    def test_get_capabilities_prompt_format(self):
        """get_capabilities_prompt formats correctly."""
        manager = PromptManager()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

        result = manager.get_capabilities_prompt(tools)

        assert "[CAPABILITIES]" in result
        assert "web_search" in result
        assert "Search the web" in result
        assert "query" in result
        assert "(required)" in result

    def test_get_capabilities_prompt_empty_tools(self):
        """get_capabilities_prompt handles empty tools."""
        manager = PromptManager()
        result = manager.get_capabilities_prompt([])

        assert "[CAPABILITIES]" in result
        assert "No tools available" in result

    def test_get_capabilities_prompt_multiple_tools(self):
        """get_capabilities_prompt handles multiple tools."""
        manager = PromptManager()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "tool_a",
                    "description": "First tool",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "tool_b",
                    "description": "Second tool",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

        result = manager.get_capabilities_prompt(tools)

        assert "tool_a" in result
        assert "tool_b" in result
        assert "First tool" in result
        assert "Second tool" in result

    def test_get_capabilities_prompt_optional_params(self):
        """get_capabilities_prompt shows optional parameters."""
        manager = PromptManager()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "Test",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "required_param": {"type": "string", "description": "Required"},
                            "optional_param": {"type": "string", "description": "Optional"}
                        },
                        "required": ["required_param"]
                    }
                }
            }
        ]

        result = manager.get_capabilities_prompt(tools)

        assert "(required)" in result
        assert "(optional)" in result
