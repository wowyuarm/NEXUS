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
from typing import Dict, List, Optional
from openai import AsyncOpenAI
from .base import LLMProvider

logger = logging.getLogger(__name__)


class DeepSeekLLMProvider(LLMProvider):
    """DeepSeek LLM provider using OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        timeout: int = 30
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
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )

        logger.info(
            f"DeepSeekLLMProvider initialized with model={self.default_model}, "
            f"base_url={self.base_url}"
        )

    async def chat_completion(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        tools: Optional[List[Dict]] = None
    ) -> Dict:
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

            # Prepare request parameters
            request_params = {
                "model": selected_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream
            }

            # Only include tools if provided and non-empty
            if tools:
                request_params["tools"] = tools

            # Make the API call
            response = await self.client.chat.completions.create(**request_params)

            # Handle response based on streaming mode
            if stream:
                return await self._handle_streaming_response(response)
            else:
                return await self._handle_non_streaming_response(response)

        except Exception as e:
            logger.error(f"Error in DeepSeek chat completion: {e}")
            raise

    async def _handle_non_streaming_response(self, response) -> Dict:
        """Handle non-streaming response from the DeepSeek API."""
        if not response.choices:
            logger.warning("DeepSeek API returned no choices")
            return {
                "content": None,
                "tool_calls": None
            }

        message = response.choices[0].message
        content = getattr(message, 'content', None)
        tool_calls = getattr(message, 'tool_calls', None)

        # Format tool calls if present
        formatted_tool_calls = None
        if tool_calls:
            formatted_tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in tool_calls
            ]

        logger.info(
            f"DeepSeek chat completion successful, "
            f"content_length={len(content) if content else 0}, "
            f"tool_calls={len(formatted_tool_calls) if formatted_tool_calls else 0}"
        )

        return {
            "content": content,
            "tool_calls": formatted_tool_calls
        }

    async def _handle_streaming_response(self, response) -> Dict:
        """Handle streaming response from the DeepSeek API."""
        content_chunks = []
        tool_calls = None

        async for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Collect content chunks
            if hasattr(delta, 'content') and delta.content:
                content_chunks.append(delta.content)

            # Collect tool calls (usually comes in last chunk)
            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                tool_calls = delta.tool_calls

        # Combine content chunks
        full_content = ''.join(content_chunks) if content_chunks else None

        # Format tool calls if present
        formatted_tool_calls = None
        if tool_calls:
            formatted_tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in tool_calls
            ]

        logger.info(
            f"DeepSeek streaming completion successful, "
            f"content_length={len(full_content) if full_content else 0}, "
            f"chunks={len(content_chunks)}, "
            f"tool_calls={len(formatted_tool_calls) if formatted_tool_calls else 0}"
        )

        return {
            "content": full_content,
            "tool_calls": formatted_tool_calls,
            "content_chunks": content_chunks
        }

