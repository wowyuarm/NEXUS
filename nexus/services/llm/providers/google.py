"""
Google Gemini LLM provider implementation for NEXUS.

This module implements the GoogleLLMProvider class that uses the OpenAI library
to communicate with Google's Gemini API.
"""

import logging
from typing import List, Dict, Any
from openai import AsyncOpenAI
from .base import LLMProvider

logger = logging.getLogger(__name__)


class GoogleLLMProvider(LLMProvider):
    """Google Gemini LLM provider using OpenAI library."""

    def __init__(self, api_key: str, base_url: str, model: str = "gemini-2.5-flash"):
        """
        Initialize the Google LLM provider.

        Args:
            api_key: Google API key
            base_url: Base URL for the API
            model: Default model to use
        """
        if not api_key:
            raise ValueError("API key is required for GoogleLLMProvider")

        self.api_key = api_key
        self.base_url = base_url
        self.default_model = model

        # Initialize OpenAI client for Google Gemini
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=f"{self.base_url}/openai/"
        )
        logger.info(f"GoogleLLMProvider initialized with model={self.default_model}")

    async def chat_completion(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Generate a chat completion using Google Gemini.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            **kwargs: Additional parameters (model, temperature, etc.)

        Returns:
            Dictionary containing 'content' (str) and 'tool_calls' (None for now)
        """
        try:
            # Default model and parameters
            model = kwargs.get("model", self.default_model)
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 4096)

            logger.info(f"Requesting chat completion with model={model}, messages_count={len(messages)}")

            # Make the API call
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Extract content from response
            content = response.choices[0].message.content if response.choices else None

            logger.info(f"Chat completion successful, content_length={len(content) if content else 0}")

            return {
                "content": content,
                "tool_calls": None  # No tool calls in this simplified implementation
            }

        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise