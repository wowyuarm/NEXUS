"""
Google Gemini LLM provider implementation for NEXUS.

This module implements the GoogleLLMProvider class that uses the OpenAI library
to communicate with Google's Gemini API.
"""

import logging
from typing import Any

from openai import AsyncOpenAI

from .base import LLMProvider
from .common import (
    build_chat_api_params,
    handle_non_streaming_response,
    handle_streaming_response,
)

logger = logging.getLogger(__name__)


class GoogleLLMProvider(LLMProvider):
    """Google Gemini LLM provider using OpenAI library."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "gemini-2.5-flash",
        timeout: int = 30,
    ):
        """
        Initialize the Google LLM provider.

        Args:
            api_key: Google API key
            base_url: Base URL for the API
            model: Default model to use
            timeout: Request timeout in seconds
        """
        if not api_key:
            raise ValueError("API key is required for GoogleLLMProvider")

        self.api_key = api_key
        self.base_url = base_url
        self.default_model = model
        self.timeout = timeout

        # Initialize OpenAI client for Google Gemini
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=f"{self.base_url}/openai/",
            timeout=self.timeout,
        )
        logger.info(
            f"GoogleLLMProvider initialized with model={self.default_model}, timeout={self.timeout}s"
        )

    async def chat_completion(
        self, messages: list[dict[str, Any]], **kwargs
    ) -> dict[str, Any]:
        """
        Generate a chat completion using Google Gemini.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            **kwargs: Additional parameters (model, temperature, tools, stream, etc.)

        Returns:
            Dictionary containing 'content' (str) and 'tool_calls' (List or None)
        """
        try:
            # Default model and parameters
            model = kwargs.get("model", self.default_model)
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 4096)
            tools = kwargs.get("tools", [])
            stream = kwargs.get("stream", False)

            logger.info(
                f"Requesting chat completion with model={model}, messages_count={len(messages)}, "
                f"tools_count={len(tools)}, stream={stream}"
            )

            # Prepare API call parameters via common util
            api_params = build_chat_api_params(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                tools=tools,
            )

            # Make the API call
            response = await self.client.chat.completions.create(**api_params)

            # Delegate response parsing to common utils
            if stream:
                return await handle_streaming_response(response)
            return await handle_non_streaming_response(response)

        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise

    # Provider-specific handlers are deduplicated via common utilities
