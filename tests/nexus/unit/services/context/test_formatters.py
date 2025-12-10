"""Unit tests for context formatters."""

import pytest
from datetime import datetime, timezone

from nexus.services.context.formatters import (
    MemoryFormatter,
    FriendsInfoFormatter,
    MomentFormatter,
)


class TestMemoryFormatter:
    """Tests for MemoryFormatter."""

    def test_format_shared_memory_with_messages(self):
        """Format history correctly with multiple messages."""
        history = [
            {"role": "human", "content": "Hello", "timestamp": "2025-12-10T15:30:00Z"},
            {"role": "ai", "content": "Hi there!", "timestamp": "2025-12-10T15:31:00Z"},
        ]

        result = MemoryFormatter.format_shared_memory(history)

        assert "[SHARED_MEMORY count=2]" in result
        assert "Human: Hello" in result
        assert "Nexus: Hi there!" in result

    def test_format_shared_memory_empty(self):
        """Empty history returns placeholder."""
        result = MemoryFormatter.format_shared_memory([])

        assert "[SHARED_MEMORY count=0]" in result
        assert "No previous conversations" in result

    def test_format_shared_memory_filters_tool_messages(self):
        """Tool messages are filtered out."""
        history = [
            {"role": "human", "content": "Search for X", "timestamp": "2025-12-10T15:30:00Z"},
            {"role": "tool", "content": "Tool result", "timestamp": "2025-12-10T15:31:00Z"},
            {"role": "ai", "content": "Based on search...", "timestamp": "2025-12-10T15:32:00Z"},
        ]

        result = MemoryFormatter.format_shared_memory(history)

        assert "[SHARED_MEMORY count=2]" in result
        assert "Tool result" not in result
        assert "Human: Search for X" in result
        assert "Nexus: Based on search" in result

    def test_format_shared_memory_respects_limit(self):
        """Respects message limit."""
        history = [
            {"role": "human", "content": f"Message {i}", "timestamp": "2025-12-10T15:30:00Z"}
            for i in range(30)
        ]

        result = MemoryFormatter.format_shared_memory(history, limit=5)

        assert "[SHARED_MEMORY count=5]" in result

    def test_format_shared_memory_truncates_long_content(self):
        """Long messages are truncated."""
        long_content = "A" * 600
        history = [
            {"role": "human", "content": long_content, "timestamp": "2025-12-10T15:30:00Z"},
        ]

        result = MemoryFormatter.format_shared_memory(history)

        assert "..." in result
        assert len(result) < len(long_content) + 200  # Header + some buffer

    def test_format_shared_memory_chronological_order(self):
        """Messages are ordered oldest to newest."""
        history = [
            {"role": "human", "content": "Second", "timestamp": "2025-12-10T15:31:00Z"},
            {"role": "human", "content": "First", "timestamp": "2025-12-10T15:30:00Z"},
        ]

        result = MemoryFormatter.format_shared_memory(history)

        # "First" should appear before "Second" in output
        first_pos = result.find("First")
        second_pos = result.find("Second")
        assert first_pos < second_pos


class TestFriendsInfoFormatter:
    """Tests for FriendsInfoFormatter."""

    def test_format_friends_info_with_profile(self):
        """Format profile correctly with friends_profile content."""
        user_profile = {
            "public_key": "0xABC123",
            "prompt_overrides": {
                "friends_profile": "This friend prefers concise answers."
            },
            "created_at": "2025-01-01T00:00:00Z"
        }

        result = FriendsInfoFormatter.format_friends_info(user_profile)

        assert "[FRIENDS_INFO]" in result
        assert "This friend prefers concise answers" in result

    def test_format_friends_info_legacy_learning_field(self):
        """Backward compatibility: legacy learning field still works."""
        user_profile = {
            "public_key": "0xABC123",
            "prompt_overrides": {
                "learning": "Legacy learning content."
            }
        }

        result = FriendsInfoFormatter.format_friends_info(user_profile)

        assert "[FRIENDS_INFO]" in result
        assert "Legacy learning content" in result

    def test_format_friends_info_empty(self):
        """Empty profile returns placeholder."""
        result = FriendsInfoFormatter.format_friends_info({})

        assert "[FRIENDS_INFO]" in result
        assert "New friend" in result or "getting to know" in result

    def test_format_friends_info_none(self):
        """None profile returns placeholder."""
        result = FriendsInfoFormatter.format_friends_info(None)

        assert "[FRIENDS_INFO]" in result
        assert "New friend" in result

    def test_format_friends_info_no_learning(self):
        """Profile without learning shows member since."""
        user_profile = {
            "public_key": "0xABC123",
            "prompt_overrides": {},
            "created_at": "2025-06-15T10:00:00Z"
        }

        result = FriendsInfoFormatter.format_friends_info(user_profile)

        assert "[FRIENDS_INFO]" in result
        assert "Member since" in result or "Still learning" in result


class TestMomentFormatter:
    """Tests for MomentFormatter."""

    def test_format_this_moment_with_input(self):
        """Format XML correctly with input."""
        result = MomentFormatter.format_this_moment(
            current_input="Hello, how are you?",
            timestamp_utc="2025-12-10T08:00:00Z",
            timezone_offset=-480  # UTC+8
        )

        assert "[THIS_MOMENT]" in result
        assert "<current_time>" in result
        assert "</current_time>" in result
        assert "<human_input>" in result
        assert "Hello, how are you?" in result
        assert "</human_input>" in result

    def test_format_this_moment_timezone_handling(self):
        """Timezone conversion works correctly."""
        result = MomentFormatter.format_this_moment(
            current_input="Test",
            timestamp_utc="2025-12-10T08:00:00Z",
            timezone_offset=-480  # UTC+8 (480 minutes ahead, negative in JS)
        )

        # Should show 16:00 in +08:00 timezone
        assert "16:00:00+08:00" in result

    def test_format_this_moment_no_timestamp(self):
        """Handle missing timestamp gracefully."""
        result = MomentFormatter.format_this_moment(
            current_input="Hello",
            timestamp_utc="",
            timezone_offset=0
        )

        assert "[THIS_MOMENT]" in result
        assert "<human_input>" in result
        assert "Hello" in result
        # Should not have current_time tag when no timestamp
        assert "<current_time>" not in result

    def test_format_this_moment_multiline_input(self):
        """Handle multiline input correctly."""
        multiline = "Line 1\nLine 2\nLine 3"
        result = MomentFormatter.format_this_moment(
            current_input=multiline,
            timestamp_utc="",
            timezone_offset=0
        )

        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
