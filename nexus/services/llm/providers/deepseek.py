"""
DeepSeek LLM provider implementation for NEXUS.

This module implements the DeepSeekLLMProvider class that uses the OpenAI library
to communicate with DeepSeek's OpenAI-compatible API.

Features:
- OpenAI-compatible API interface
- Streaming and non-streaming chat completions
- Tool/Function calling support
- Multiple DeepSeek model support
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


class DeepSeekLLMProvider(LLMProvider):
    """DeepSeek LLM provider using OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        timeout: int = 30,
    ):
        """
        Initialize the DeepSeek LLM provider.

        Args:
            api_key: DeepSeek API key
            base_url: Base URL for the DeepSeek API
            model: Default model to use
            timeout: Request timeout in seconds
        """
        if not api_key:
            raise ValueError("API key is required for DeepSeekLLMProvider")

        self.api_key = api_key
        self.base_url = base_url
        self.default_model = model
        self.timeout = timeout

        # Initialize OpenAI client for DeepSeek
        self.client = AsyncOpenAI(
            api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
        )

        logger.info(
            f"DeepSeekLLMProvider initialized with model={self.default_model}, "
            f"base_url={self.base_url}"
        )

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate a chat completion using DeepSeek.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to self.default_model)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            tools: Optional list of tool definitions for function calling

        Returns:
            Dictionary containing 'content' and optional 'tool_calls'
        """
        try:
            selected_model = model or self.default_model

            # Prepare request parameters via common util
            request_params = build_chat_api_params(
                model=selected_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                tools=tools,
            )

            # Make the API call
            response = await self.client.chat.completions.create(**request_params)

            # Handle response based on streaming mode using common utils
            if stream:
                return await handle_streaming_response(response)
            return await handle_non_streaming_response(response)

        except Exception as e:
            logger.error(f"Error in DeepSeek chat completion: {e}")
            raise

    # Provider-specific handlers are deduplicated via common utilities
