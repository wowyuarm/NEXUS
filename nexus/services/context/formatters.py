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

        # Filter to human and AI messages only, limit count
        filtered = []
        for msg in history:
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
        for msg in reversed(filtered):
            timestamp = msg.get("timestamp", "")
            role = msg.get("role", "").lower()
            content = msg.get("content", "")

            # Format timestamp
            time_str = MemoryFormatter._format_timestamp(timestamp)

            # Format role
            role_display = "Human" if role == NEXUS_ROLE_HUMAN else "Nexus"

            # Truncate very long messages
            if len(content) > 500:
                content = content[:497] + "..."

            lines.append(f"[{time_str}] {role_display}: {content}")

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

        # Also check for legacy 'learning' field for backward compatibility
        if not friends_profile:
            friends_profile = prompt_overrides.get("learning", "")

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

            # Apply timezone offset (negative because getTimezoneOffset returns minutes west)
            offset_td = timedelta(minutes=-timezone_offset)
            local_dt = utc_dt + offset_td

            # Calculate offset hours and minutes for display
            total_minutes = -timezone_offset
            offset_hours = abs(total_minutes) // 60
            offset_mins = abs(total_minutes) % 60
            offset_sign = "+" if total_minutes >= 0 else "-"

            return local_dt.strftime(
                f"%Y-%m-%d %H:%M:%S{offset_sign}{offset_hours:02d}:{offset_mins:02d}"
            )

        except Exception as e:
            logger.warning(f"Failed to format timestamp '{timestamp_utc}': {e}")
            return timestamp_utc or "Unknown time"
