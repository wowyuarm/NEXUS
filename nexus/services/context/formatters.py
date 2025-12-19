"""
Formatters for context building in NEXUS.

Provides formatting utilities for different context sections:
- MemoryFormatter: [SHARED_MEMORY] block from conversation history
- FriendsInfoFormatter: [FRIENDS_INFO] block from user profile
- MomentFormatter: [THIS_MOMENT] block with current input
"""

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_TRUNCATION_LIMIT = 1000

# Role mapping constants
NEXUS_ROLE_HUMAN = "human"
NEXUS_ROLE_AI = "ai"


class MemoryFormatter:
    """Formats conversation history into [SHARED_MEMORY] block."""

    @staticmethod
    def format_shared_memory(history: list[dict], limit: int = 20) -> str:
        """
        Format conversation history as shared memory.

        Args:
            history: List of message dicts from database (newest first)
            limit: Maximum number of messages to include
            config_service: Optional ConfigService for configuration

        Returns:
            Formatted [SHARED_MEMORY] block string

        Format:
            [SHARED_MEMORY count=N]
            Recent conversation memory:

            [2025-12-10 15:30] Human: ...
            [2025-12-10 15:31] Nexus: ...
        """
        if not history:
            return "[SHARED_MEMORY count=0]\nRecent conversation memory:\n\n(No previous conversations yet)"

        # 1. Merge messages by run_id
        merged_messages = MemoryFormatter._merge_messages_by_run_id(history)

        # 2. Apply limit after merging
        filtered = []
        for msg in merged_messages:
            role = msg.get("role", "").lower()
            if role in (NEXUS_ROLE_HUMAN, NEXUS_ROLE_AI):
                filtered.append(msg)
            if len(filtered) >= limit:
                break

        if not filtered:
            return "[SHARED_MEMORY count=0]\nRecent conversation memory:\n\n(No previous conversations yet)"

        lines = [
            f"[SHARED_MEMORY count={len(filtered)}]",
            "Recent conversation memory:",
            "",
        ]

        # Reverse to chronological order (oldest first)
        prev_role = None
        for msg in reversed(filtered):
            timestamp = msg.get("timestamp", "")
            role = msg.get("role", "").lower()
            content = msg.get("content", "")

            # Format timestamp
            time_str = MemoryFormatter._format_timestamp(timestamp)

            # Format role
            role_display = "Human" if role == NEXUS_ROLE_HUMAN else "Nexus"

            # Truncate very long messages
            if len(content) > DEFAULT_TRUNCATION_LIMIT:
                content = content[:DEFAULT_TRUNCATION_LIMIT-3] + "..."

            # Determine if we should show timestamp for this message
            # Show timestamp for human messages, and for AI messages that don't follow a human
            if role == NEXUS_ROLE_HUMAN:
                lines.append(f"[{time_str}] {role_display}: {content}")
            else:  # AI message
                if prev_role == NEXUS_ROLE_HUMAN:
                    # AI follows human - indent without timestamp
                    lines.append(f"  {role_display}: {content}")
                else:
                    # AI doesn't follow human (e.g., first message is AI) - show timestamp
                    lines.append(f"[{time_str}] {role_display}: {content}")

            prev_role = role

        return "\n".join(lines)

    @staticmethod
    def _format_timestamp(timestamp: Any) -> str:
        """Format timestamp to readable string."""
        if not timestamp:
            return "Unknown time"

        try:
            if isinstance(timestamp, datetime):
                return timestamp.strftime("%Y-%m-%d %H:%M")
            elif isinstance(timestamp, str):
                # Try parsing ISO format
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d %H:%M")
            else:
                return str(timestamp)
        except Exception:
            return "Unknown time"

    @staticmethod
    def _merge_messages_by_run_id(messages: list[dict]) -> list[dict]:
        """
        Merge AI messages by run_id and annotate tool calls.

        Input: Raw message list (newest first)
        Output: Merged message list (chronological order across run_ids)

        Processing:
        1. Filter: keep only role in ("human", "ai")
        2. Group by run_id
        3. For each run_id group:
           - Separate human and ai messages
           - Human messages: keep all (usually one)
           - AI messages: merge all ai messages in chronological order
           - Extract tool call info, generate annotation string
           - Build merged ai message (using latest timestamp)
        4. Reorder: ascending by timestamp (oldest first)
        """
        # 1. Filter human and AI messages only
        filtered = []
        for msg in messages:
            role = msg.get("role", "").lower()
            if role in (NEXUS_ROLE_HUMAN, NEXUS_ROLE_AI):
                filtered.append(msg)

        if not filtered:
            return []

        # 2. Group by run_id
        groups: dict[str | None, list[dict]] = {}
        for msg in filtered:
            run_id = msg.get("run_id")
            # If no run_id, treat as separate group (use None as key)
            groups.setdefault(run_id, []).append(msg)

        merged_messages = []

        for run_id, group_msgs in groups.items():
            # Skip if run_id is None (messages without run_id remain unchanged)
            if run_id is None:
                merged_messages.extend(group_msgs)
                continue

            # Sort group by timestamp ascending (oldest first)
            group_msgs.sort(key=lambda x: x.get("timestamp", ""))

            # Separate human and AI messages
            human_msgs = [msg for msg in group_msgs if msg.get("role", "").lower() == NEXUS_ROLE_HUMAN]
            ai_msgs = [msg for msg in group_msgs if msg.get("role", "").lower() == NEXUS_ROLE_AI]

            # Keep all human messages unchanged
            merged_messages.extend(human_msgs)

            # Merge AI messages if any
            if ai_msgs:
                # Sort AI messages by timestamp (should already be sorted)
                ai_msgs.sort(key=lambda x: x.get("timestamp", ""))

                # Collect contents and tool calls, track first message with tool calls
                contents = []
                all_tool_calls = []
                first_tool_call_index = -1  # Index of first AI message with tool calls

                for i, ai_msg in enumerate(ai_msgs):
                    content = ai_msg.get("content", "")
                    if content:
                        contents.append(content)

                    # Extract tool calls if present
                    metadata = ai_msg.get("metadata", {})
                    tool_calls = metadata.get("tool_calls", [])
                    if tool_calls:
                        all_tool_calls.extend(tool_calls)
                        if first_tool_call_index == -1:
                            first_tool_call_index = i

                # Build merged content with annotation inserted at correct position
                if all_tool_calls:
                    annotation = MemoryFormatter._extract_tool_call_annotation(all_tool_calls)
                    # Insert annotation after the message where tool call was declared
                    if contents and first_tool_call_index >= 0:
                        # Insert annotation after the message at first_tool_call_index
                        # If there are more messages after it, annotation goes before next message
                        # If it's the last message, annotation goes at the end
                        insertion_index = first_tool_call_index + 1
                        contents.insert(insertion_index, annotation)
                    else:
                        # Fallback: append at end
                        contents.append(annotation)

                merged_content = "\n".join(contents)

                # Use latest AI message as base for merged message
                latest_ai = ai_msgs[-1]
                merged_ai = {
                    "id": f"merged_ai_{run_id}",
                    "run_id": run_id,
                    "role": "ai",
                    "content": merged_content,
                    "timestamp": latest_ai.get("timestamp"),
                    "metadata": {
                        "source": "merged",
                        "original_count": len(ai_msgs),
                        "has_tool_calls": bool(all_tool_calls),
                    }
                }

                merged_messages.append(merged_ai)

        # Sort all messages by timestamp descending (newest first)
        # This ensures format_shared_memory's reversed() produces chronological order
        merged_messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return merged_messages

    @staticmethod
    def _extract_tool_call_annotation(tool_calls: list) -> str:
        """
        Generate annotation string from tool_calls.

        Format: [tool_use:web_search, query:人工智能最新发展]
        Multiple tools: [tool_use:web_search, query:...; tool_use:calculator, expression:...]

        Only extract key parameters: query for web_search, first param for others.
        """
        if not tool_calls:
            return ""

        annotations = []
        for tool_call in tool_calls:
            name = tool_call.get("name", "unknown")
            arguments = tool_call.get("arguments", {})

            # Extract key parameter based on tool name
            if name == "web_search":
                key_param = arguments.get("query", "")
                if key_param:
                    annotations.append(f"tool_use:{name}, query:{key_param}")
                else:
                    annotations.append(f"tool_use:{name}")
            else:
                # For other tools, take first parameter if available
                if arguments:
                    first_key = next(iter(arguments), None)
                    first_value = arguments.get(first_key, "")
                    if first_key and first_value:
                        annotations.append(f"tool_use:{name}, {first_key}:{first_value}")
                    else:
                        annotations.append(f"tool_use:{name}")
                else:
                    annotations.append(f"tool_use:{name}")

        # Join with semicolon and wrap in brackets
        if len(annotations) == 1:
            return f"[{annotations[0]}]"
        else:
            return f"[{'; '.join(annotations)}]"


class FriendsInfoFormatter:
    """Formats user profile into [FRIENDS_INFO] block."""

    @staticmethod
    def format_friends_info(user_profile: dict[str, Any]) -> str:
        """
        Format user profile as friends info.

        Args:
            user_profile: Dict containing user profile data from identities

        Returns:
            Formatted [FRIENDS_INFO] block string

        Format:
            [FRIENDS_INFO]
            About this friend:

            (Profile details or placeholder)
        """
        if not user_profile:
            return "[FRIENDS_INFO]\nAbout this friend:\n\n(New friend, getting to know each other)"

        lines = ["[FRIENDS_INFO]", "About this friend:", ""]

        # Extract prompt_overrides.friends_profile if available (user preferences)
        prompt_overrides = user_profile.get("prompt_overrides", {})
        friends_profile = prompt_overrides.get("friends_profile", "")

        if friends_profile and friends_profile.strip():
            lines.append(friends_profile.strip())
        else:
            # Check for any other profile info
            created_at = user_profile.get("created_at")

            if created_at:
                time_str = FriendsInfoFormatter._format_member_since(created_at)
                lines.append(f"Member since: {time_str}")

            if not friends_profile:
                lines.append("(Still learning about this friend's preferences)")

        return "\n".join(lines)

    @staticmethod
    def _format_member_since(created_at: Any) -> str:
        """Format creation timestamp."""
        try:
            if isinstance(created_at, datetime):
                return created_at.strftime("%Y-%m-%d")
            elif isinstance(created_at, str):
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d")
            else:
                return str(created_at)
        except Exception:
            return "Unknown"


class MomentFormatter:
    """Formats current moment context into [THIS_MOMENT] block."""

    @staticmethod
    def format_this_moment(
        current_input: str, timestamp_utc: str = "", timezone_offset: int = 0
    ) -> str:
        """
        Format current moment with XML structure.

        Args:
            current_input: The human's current input text
            timestamp_utc: UTC timestamp in ISO 8601 format
            timezone_offset: Client timezone offset in minutes (from JS getTimezoneOffset)

        Returns:
            Formatted [THIS_MOMENT] block with XML tags

        Format:
            [THIS_MOMENT]
            <current_time>2025-12-10 16:00:00+08:00</current_time>
            <human_input>
            User's input here
            </human_input>
        """
        lines = ["[THIS_MOMENT]"]

        # Format current time if available
        if timestamp_utc:
            formatted_time = MomentFormatter._format_local_time(
                timestamp_utc, timezone_offset
            )
            lines.append(f"<current_time>{formatted_time}</current_time>")

        # Add human input
        lines.append("<human_input>")
        lines.append(current_input)
        lines.append("</human_input>")

        return "\n".join(lines)

    @staticmethod
    def _format_local_time(timestamp_utc: str, timezone_offset: int) -> str:
        """
        Convert UTC timestamp to local time with offset.

        Args:
            timestamp_utc: ISO 8601 UTC timestamp
            timezone_offset: Minutes west of UTC (JS getTimezoneOffset convention)

        Returns:
            Formatted local time string with offset (e.g., "2025-12-10 16:00:00+08:00")
        """
        try:
            # Parse UTC timestamp
            utc_dt = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))

            # Coerce timezone_offset to int (may come as string from metadata)
            offset_minutes = int(timezone_offset)

            # Apply timezone offset (negative because getTimezoneOffset returns minutes west)
            offset_td = timedelta(minutes=-offset_minutes)
            local_dt = utc_dt + offset_td

            # Calculate offset hours and minutes for display
            total_minutes = -offset_minutes
            offset_hours = abs(total_minutes) // 60
            offset_mins = abs(total_minutes) % 60
            offset_sign = "+" if total_minutes >= 0 else "-"

            return local_dt.strftime(
                f"%Y-%m-%d %H:%M:%S{offset_sign}{offset_hours:02d}:{offset_mins:02d}"
            )

        except Exception as e:
            logger.warning(f"Failed to format timestamp '{timestamp_utc}': {e}")
            return timestamp_utc or "Unknown time"
