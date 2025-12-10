"""
Context building package for NEXUS.

This package provides the context construction system for LLM calls,
implementing a multi-message structure with [TAG] delimiters.

Message structure:
1. system: CORE_IDENTITY - NEXUS's essence as a friend in dialogue space
2. user: [CAPABILITIES] - Available tools and usage
3. user: [SHARED_MEMORY] - Recent conversation history
4. user: [FRIENDS_INFO] - User profile from identities
5. user: [THIS_MOMENT] - Current input with timestamp
"""

from nexus.services.context.builder import ContextBuilder
from nexus.services.context.prompts import PromptManager

__all__ = ["ContextBuilder", "PromptManager"]
