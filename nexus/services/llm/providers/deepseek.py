"""
DeepSeek LLM provider implementation for NEXUS.

This module implements the DeepSeekLLMProvider class that uses the OpenAI library
to communicate with DeepSeek's OpenAI-compatible API.

Features:
- OpenAI-compatible chat completion interface
- Streaming and non-streaming responses
- Tool calling support
- Multiple DeepSeek model support
"""

import logging
from typing import List, Dict, Any
from openai import AsyncOpenAI
from .base import LLMProvider

logger = logging.getLogger(__name__)


class DeepSeekLLMProvider(LLMProvider):
    """DeepSeek LLM provider using OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
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
            f"timeout={self.timeout}s, base_url={self.base_url}"
        )

    async def chat_completion(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Generate a chat completion using DeepSeek.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            **kwargs: Additional parameters (model, temperature, tools, stream, etc.)

        Returns:
            Dictionary containing 'content' (str) and 'tool_calls' (List or None)
        """
        try:
            # Extract parameters with defaults
            model = kwargs.get("model", self.default_model)
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 4096)
            tools = kwargs.get("tools", [])
            stream = kwargs.get("stream", False)

            logger.info(
                f"Requesting chat completion with model={model}, "
                f"messages_count={len(messages)}, tools_count={len(tools)}, stream={stream}"
            )

            # Prepare API call parameters
            api_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream
            }

            # Add tools if provided
            if tools:
                api_params["tools"] = tools

            # Make the API call
            response = await self.client.chat.completions.create(**api_params)

            if stream:
                # Handle streaming response
                return await self._handle_streaming_response(response)
            else:
                # Handle non-streaming response
                return await self._handle_non_streaming_response(response)

        except Exception as e:
            logger.error(f"Error in DeepSeek chat completion: {e}")
            raise

    async def _handle_non_streaming_response(self, response) -> Dict[str, Any]:
        """Handle non-streaming response from the DeepSeek API."""
        # Extract content and tool calls from response
        message = response.choices[0].message if response.choices else None
        content = message.content if message else None

        # Extract tool calls safely
        tool_calls = None
        if message and hasattr(message, 'tool_calls'):
            tool_calls = message.tool_calls

        # Convert tool_calls to the expected format if present
        formatted_tool_calls = None
        if tool_calls:
            formatted_tool_calls = []
            for tool_call in tool_calls:
                formatted_tool_calls.append({
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                })

        logger.info(
            f"DeepSeek chat completion successful, "
            f"content_length={len(content) if content else 0}, "
            f"tool_calls_count={len(formatted_tool_calls) if formatted_tool_calls else 0}"
        )

        return {
            "content": content,
            "tool_calls": formatted_tool_calls
        }

    async def _handle_streaming_response(self, response) -> Dict[str, Any]:
        """Handle streaming response from the DeepSeek API."""
        content_chunks = []
        tool_calls = None

        async for chunk in response:
            if chunk.choices:
                delta = chunk.choices[0].delta

                # Collect content chunks
                if hasattr(delta, 'content') and delta.content:
                    content_chunks.append(delta.content)

                # Check for tool calls in the final chunk
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    tool_calls = delta.tool_calls

        # Combine all content chunks
        full_content = ''.join(content_chunks) if content_chunks else None

        # Convert tool_calls to the expected format if present
        formatted_tool_calls = None
        if tool_calls:
            formatted_tool_calls = []
            for tool_call in tool_calls:
                formatted_tool_calls.append({
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                })

        logger.info(
            f"DeepSeek streaming completion successful, "
            f"content_length={len(full_content) if full_content else 0}, "
            f"tool_calls_count={len(formatted_tool_calls) if formatted_tool_calls else 0}"
        )

        return {
            "content": full_content,
            "tool_calls": formatted_tool_calls,
            "content_chunks": content_chunks  # Include chunks for streaming
        }