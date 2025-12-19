"""Unit tests for context formatters."""


from nexus.services.context.formatters import (
    FriendsInfoFormatter,
    MemoryFormatter,
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
            {
                "role": "human",
                "content": "Search for X",
                "timestamp": "2025-12-10T15:30:00Z",
            },
            {
                "role": "tool",
                "content": "Tool result",
                "timestamp": "2025-12-10T15:31:00Z",
            },
            {
                "role": "ai",
                "content": "Based on search...",
                "timestamp": "2025-12-10T15:32:00Z",
            },
        ]

        result = MemoryFormatter.format_shared_memory(history)

        assert "[SHARED_MEMORY count=2]" in result
        assert "Tool result" not in result
        assert "Human: Search for X" in result
        assert "Nexus: Based on search" in result

    def test_format_shared_memory_respects_limit(self):
        """Respects message limit."""
        history = [
            {
                "role": "human",
                "content": f"Message {i}",
                "timestamp": "2025-12-10T15:30:00Z",
            }
            for i in range(30)
        ]

        result = MemoryFormatter.format_shared_memory(history, limit=5)

        assert "[SHARED_MEMORY count=5]" in result

    def test_format_shared_memory_truncates_long_content(self):
        """Long messages are truncated."""
        long_content = "A" * 600
        history = [
            {
                "role": "human",
                "content": long_content,
                "timestamp": "2025-12-10T15:30:00Z",
            },
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

    def test_merge_messages_by_run_id_simple(self):
        """Basic merging of AI messages within same run_id."""
        messages = [
            {
                "id": "msg1",
                "run_id": "run_abc",
                "role": "human",
                "content": "Hello",
                "timestamp": "2025-12-10T15:30:00Z",
            },
            {
                "id": "msg2",
                "run_id": "run_abc",
                "role": "ai",
                "content": "First AI response",
                "timestamp": "2025-12-10T15:31:00Z",
            },
            {
                "id": "msg3",
                "run_id": "run_abc",
                "role": "ai",
                "content": "Second AI response",
                "timestamp": "2025-12-10T15:32:00Z",
                "metadata": {"has_tool_calls": False},
            },
        ]

        merged = MemoryFormatter._merge_messages_by_run_id(messages)

        # Should have 2 messages: 1 human + 1 merged AI
        assert len(merged) == 2

        # AI message first (newest timestamp)
        ai_msg = merged[0]
        assert ai_msg["role"] == "ai"
        assert "First AI response" in ai_msg["content"]
        assert "Second AI response" in ai_msg["content"]
        assert ai_msg["run_id"] == "run_abc"

        # Human message second (older timestamp)
        human_msg = merged[1]
        assert human_msg["role"] == "human"
        assert human_msg["content"] == "Hello"

    def test_merge_messages_by_run_id_multiple_human(self):
        """Multiple human messages within same run_id (all kept)."""
        messages = [
            {
                "id": "msg1",
                "run_id": "run_abc",
                "role": "human",
                "content": "First question",
                "timestamp": "2025-12-10T15:30:00Z",
            },
            {
                "id": "msg2",
                "run_id": "run_abc",
                "role": "human",
                "content": "Second question",
                "timestamp": "2025-12-10T15:31:00Z",
            },
            {
                "id": "msg3",
                "run_id": "run_abc",
                "role": "ai",
                "content": "AI response",
                "timestamp": "2025-12-10T15:32:00Z",
            },
        ]

        merged = MemoryFormatter._merge_messages_by_run_id(messages)

        # Should have 3 messages: 1 ai + 2 human (newest to oldest)
        assert len(merged) == 3
        assert merged[0]["role"] == "ai"
        assert merged[0]["content"] == "AI response"
        assert merged[1]["role"] == "human"
        assert merged[1]["content"] == "Second question"
        assert merged[2]["role"] == "human"
        assert merged[2]["content"] == "First question"

    def test_merge_messages_by_run_id_no_run_id(self):
        """Messages without run_id remain unchanged."""
        messages = [
            {
                "id": "msg1",
                "role": "human",  # No run_id
                "content": "Hello",
                "timestamp": "2025-12-10T15:30:00Z",
            },
            {
                "id": "msg2",
                "role": "ai",  # No run_id
                "content": "Hi",
                "timestamp": "2025-12-10T15:31:00Z",
            },
        ]

        merged = MemoryFormatter._merge_messages_by_run_id(messages)

        # Should have 2 messages, sorted by timestamp descending
        assert len(merged) == 2
        assert merged[0]["role"] == "ai"  # Newer timestamp (15:31)
        assert merged[1]["role"] == "human"  # Older timestamp (15:30)

    def test_extract_tool_call_annotation_web_search(self):
        """Extract annotation for web_search tool."""
        tool_calls = [
            {
                "name": "web_search",
                "arguments": {"query": "人工智能发展现状"},
                "id": "call_123",
            }
        ]

        annotation = MemoryFormatter._extract_tool_call_annotation(tool_calls)
        assert annotation == "[tool_use:web_search, query:人工智能发展现状]"

    def test_extract_tool_call_annotation_empty(self):
        """Empty tool_calls returns empty string."""
        annotation = MemoryFormatter._extract_tool_call_annotation([])
        assert annotation == ""

    def test_extract_tool_call_annotation_multiple_tools(self):
        """Multiple tools separated by semicolon."""
        tool_calls = [
            {
                "name": "web_search",
                "arguments": {"query": "AI trends"},
                "id": "call_1",
            },
            {
                "name": "calculator",
                "arguments": {"expression": "2+2"},
                "id": "call_2",
            },
        ]

        annotation = MemoryFormatter._extract_tool_call_annotation(tool_calls)
        assert "[tool_use:web_search, query:AI trends" in annotation
        assert "tool_use:calculator, expression:2+2" in annotation
        assert ";" in annotation  # Semicolon separator

    def test_format_shared_memory_with_merged_messages(self):
        """format_shared_memory uses merged messages."""
        history = [
            {
                "id": "msg1",
                "run_id": "run_abc",
                "role": "human",
                "content": "Search for AI",
                "timestamp": "2025-12-10T15:30:00Z",
            },
            {
                "id": "msg2",
                "run_id": "run_abc",
                "role": "ai",
                "content": "I'll search...",
                "timestamp": "2025-12-10T15:31:00Z",
                "metadata": {
                    "has_tool_calls": True,
                    "tool_calls": [
                        {
                            "name": "web_search",
                            "arguments": {"query": "AI development 2025"},
                            "id": "call_123",
                        }
                    ],
                },
            },
            {
                "id": "msg3",
                "run_id": "run_abc",
                "role": "ai",
                "content": "Based on search results...",
                "timestamp": "2025-12-10T15:32:00Z",
            },
        ]

        result = MemoryFormatter.format_shared_memory(history)

        # Count should be 2 (human + merged ai)
        assert "[SHARED_MEMORY count=2]" in result
        # Should contain tool annotation
        assert "[tool_use:web_search, query:AI development 2025]" in result
        # Should contain both AI messages
        assert "I'll search..." in result
        assert "Based on search results..." in result

        # Verify annotation is between the two AI messages (not at the end)
        # Split result into lines and find relevant lines
        lines = result.split('\n')

        # Find the line with "Nexus: I'll search..."
        nexus_line_index = -1
        for i, line in enumerate(lines):
            if 'Nexus:' in line and "I'll search..." in line:
                nexus_line_index = i
                break

        assert nexus_line_index >= 0, "Should find Nexus line with 'I'll search...'"

        # The next line should be the annotation
        assert nexus_line_index + 1 < len(lines), "Should have annotation line after Nexus line"
        annotation_line = lines[nexus_line_index + 1]
        assert annotation_line == "[tool_use:web_search, query:AI development 2025]", \
            f"Expected annotation line, got: {annotation_line}"

        # The line after annotation should be "Based on search results..."
        assert nexus_line_index + 2 < len(lines), "Should have 'Based on search results...' line after annotation"
        based_line = lines[nexus_line_index + 2]
        assert based_line == "Based on search results...", \
            f"Expected 'Based on search results...', got: {based_line}"

    def test_format_shared_memory_count_updated(self):
        """Count reflects merged message count, not original count."""
        history = [
            {
                "id": "msg1",
                "run_id": "run_abc",
                "role": "human",
                "content": "Hello",
                "timestamp": "2025-12-10T15:30:00Z",
            },
            {
                "id": "msg2",
                "run_id": "run_abc",
                "role": "ai",
                "content": "First",
                "timestamp": "2025-12-10T15:31:00Z",
            },
            {
                "id": "msg3",
                "run_id": "run_abc",
                "role": "ai",
                "content": "Second",
                "timestamp": "2025-12-10T15:32:00Z",
            },
            # Another run_id - should be separate
            {
                "id": "msg4",
                "run_id": "run_def",
                "role": "human",
                "content": "Another",
                "timestamp": "2025-12-10T15:33:00Z",
            },
            {
                "id": "msg5",
                "run_id": "run_def",
                "role": "ai",
                "content": "Response",
                "timestamp": "2025-12-10T15:34:00Z",
            },
        ]

        result = MemoryFormatter.format_shared_memory(history)

        # Should have count=4 (run_abc: human + merged ai, run_def: human + ai)
        assert "[SHARED_MEMORY count=4]" in result

    def test_format_shared_memory_limit_applied_after_merge(self):
        """Limit is applied after merging, not before."""
        history = [
            {
                "id": f"msg{i}",
                "run_id": f"run_{i}",
                "role": "human",
                "content": f"Question {i}",
                "timestamp": f"2025-12-10T15:{30+i}:00Z",
            }
            for i in range(10)
        ]
        # Add AI responses for each
        for i in range(10):
            history.append({
                "id": f"msg_ai_{i}",
                "run_id": f"run_{i}",
                "role": "ai",
                "content": f"Answer {i}",
                "timestamp": f"2025-12-10T15:{40+i}:00Z",
            })

        # With limit=5, should get 5 merged pairs (human+ai) = 5 total messages
        result = MemoryFormatter.format_shared_memory(history, limit=5)
        assert "[SHARED_MEMORY count=5]" in result


class TestFriendsInfoFormatter:
    """Tests for FriendsInfoFormatter."""

    def test_format_friends_info_with_profile(self):
        """Format profile correctly with friends_profile content."""
        user_profile = {
            "public_key": "0xABC123",
            "prompt_overrides": {
                "friends_profile": "This friend prefers concise answers."
            },
            "created_at": "2025-01-01T00:00:00Z",
        }

        result = FriendsInfoFormatter.format_friends_info(user_profile)

        assert "[FRIENDS_INFO]" in result
        assert "This friend prefers concise answers" in result


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
            "created_at": "2025-06-15T10:00:00Z",
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
            timezone_offset=-480,  # UTC+8
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
            timezone_offset=-480,  # UTC+8 (480 minutes ahead, negative in JS)
        )

        # Should show 16:00 in +08:00 timezone
        assert "16:00:00+08:00" in result

    def test_format_this_moment_no_timestamp(self):
        """Handle missing timestamp gracefully."""
        result = MomentFormatter.format_this_moment(
            current_input="Hello", timestamp_utc="", timezone_offset=0
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
            current_input=multiline, timestamp_utc="", timezone_offset=0
        )

        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_format_this_moment_string_timezone_offset(self):
        """Handle timezone_offset as string (bug regression test)."""
        result = MomentFormatter.format_this_moment(
            current_input="Test",
            timestamp_utc="2025-12-19T02:17:24.260Z",
            timezone_offset="-480",  # String instead of int (from metadata)
        )

        assert "[THIS_MOMENT]" in result
        assert "<human_input>" in result
        assert "Test" in result
        # Should correctly format time without warning
        assert "10:17:24+08:00" in result
