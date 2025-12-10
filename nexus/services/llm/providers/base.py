"""
Base LLM provider interface for NEXUS.

This module defines the abstract base class that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    async def chat_completion(
        self, messages: list[dict[str, Any]], **kwargs
    ) -> dict[str, Any]:
        """
        Generate a chat completion response.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            **kwargs: Additional provider-specific parameters

        Returns:
            Dictionary containing 'content' (str) and 'tool_calls' (List or None)
        """
        pass
