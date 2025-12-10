#!/usr/bin/env python3
"""
Context Preview Script for NEXUS.

Assembles and outputs the full context that would be sent to LLM API.
Uses simulated data for history, time, current input, and friends_info.
Imports actual context building logic from nexus.services.context.

Usage:
    poetry run python scripts/context_preview.py          # formatted output
    poetry run python scripts/context_preview.py --raw    # raw API message list

Output: context_output.txt (same directory as this script)
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nexus.services.context.formatters import (
    FriendsInfoFormatter,
    MemoryFormatter,
    MomentFormatter,
)
from nexus.services.context.prompts import PromptManager
from nexus.tools.registry import ToolRegistry

# =============================================================================
# Simulated Data
# =============================================================================

def _utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


# Simulated conversation history (newest first, as returned from database)
MOCK_HISTORY = [
    {
        "role": "ai",
        "content": "当然可以！Python的列表推导式是一种简洁创建列表的方式。基本语法是 `[expression for item in iterable if condition]`。比如 `[x**2 for x in range(10) if x % 2 == 0]` 会返回偶数的平方。",
        "timestamp": (_utc_now() - timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "run_id": "run_002",
    },
    {
        "role": "human",
        "content": "能解释一下Python的列表推导式吗？",
        "timestamp": (_utc_now() - timedelta(minutes=6)).isoformat().replace("+00:00", "Z"),
        "run_id": "run_002",
    },
    {
        "role": "ai",
        "content": "你好！很高兴认识你。有什么我可以帮助你的吗？",
        "timestamp": (_utc_now() - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "run_id": "run_001",
    },
    {
        "role": "human",
        "content": "你好，我是新用户",
        "timestamp": (_utc_now() - timedelta(hours=1, minutes=1)).isoformat().replace("+00:00", "Z"),
        "run_id": "run_001",
    },
]

# Simulated user profile (friends_info)
MOCK_USER_PROFILE = {
    "owner_key": "mock_user_pubkey_12345",
    "created_at": "2024-06-15T10:30:00Z",
    "prompt_overrides": {
        "friends_profile": """- 偏好中文交流
- 软件开发者，主要使用Python
- 喜欢简洁直接的回答
- 对AI技术和编程有浓厚兴趣"""
    },
}

# Simulated current input
MOCK_CURRENT_INPUT = "帮我写一个简单的Python装饰器示例"

# Simulated timestamp (UTC) and timezone offset
MOCK_TIMESTAMP_UTC = _utc_now().isoformat().replace("+00:00", "Z")
MOCK_TIMEZONE_OFFSET = -480  # UTC+8 (Beijing/Shanghai), JS getTimezoneOffset returns -480

def get_actual_tool_definitions() -> list[dict]:
    """Get actual tool definitions from ToolRegistry."""
    registry = ToolRegistry()
    registry.discover_and_register("nexus.tools.definition")
    return registry.get_all_tool_definitions()


def build_context_preview() -> list[dict[str, str]]:
    """
    Build context messages using actual NEXUS logic with simulated data.

    Returns:
        List of message dicts as would be sent to LLM API.
    """
    prompt_manager = PromptManager()
    tool_definitions = get_actual_tool_definitions()

    messages = [
        # 1. System: CORE_IDENTITY
        {"role": "system", "content": prompt_manager.get_core_identity()},
        # 2. User: [CAPABILITIES]
        {
            "role": "user",
            "content": prompt_manager.get_capabilities_prompt(tool_definitions),
        },
        # 3. User: [SHARED_MEMORY]
        {"role": "user", "content": MemoryFormatter.format_shared_memory(MOCK_HISTORY)},
        # 4. User: [FRIENDS_INFO]
        {
            "role": "user",
            "content": FriendsInfoFormatter.format_friends_info(MOCK_USER_PROFILE),
        },
        # 5. User: [THIS_MOMENT]
        {
            "role": "user",
            "content": MomentFormatter.format_this_moment(
                current_input=MOCK_CURRENT_INPUT,
                timestamp_utc=MOCK_TIMESTAMP_UTC,
                timezone_offset=MOCK_TIMEZONE_OFFSET,
            ),
        },
    ]

    return messages


def format_output(messages: list[dict[str, str]]) -> str:
    """Format messages for file output."""
    output_lines = [
        "=" * 80,
        "NEXUS Context Preview",
        f"Generated at: {datetime.now().isoformat()}",
        "=" * 80,
        "",
    ]

    for i, msg in enumerate(messages, 1):
        role = msg["role"].upper()
        content = msg["content"]

        output_lines.append(f"{'─' * 80}")
        output_lines.append(f"[Message {i}] Role: {role}")
        output_lines.append(f"{'─' * 80}")
        output_lines.append(content)
        output_lines.append("")

    output_lines.append("=" * 80)
    output_lines.append(f"Total messages: {len(messages)}")
    output_lines.append("=" * 80)

    return "\n".join(output_lines)


def format_raw_output(messages: list[dict[str, str]]) -> str:
    """Format messages as raw API JSON list."""
    return json.dumps(messages, ensure_ascii=False, indent=2)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Preview NEXUS context for LLM API")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output raw API message list (JSON format)",
    )
    args = parser.parse_args()

    print("Building context preview...")

    # Build context using actual logic
    messages = build_context_preview()

    # Format output based on mode
    if args.raw:
        output_text = format_raw_output(messages)
    else:
        output_text = format_output(messages)

    # Write to file (same directory as script)
    script_dir = Path(__file__).parent
    output_path = script_dir / "context_output.txt"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"Context preview written to: {output_path}")
    print(f"Total messages: {len(messages)}")


if __name__ == "__main__":
    main()
