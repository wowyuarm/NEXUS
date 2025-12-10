"""
OpenRouter LLM provider implementation for NEXUS.

This module implements the OpenRouterLLMProvider class that provides access to
hundreds of AI models through OpenRouter's unified API using OpenAI-compatible
interface.

Features:
- Access to 200+ AI models through a single API
- OpenAI-compatible chat completion interface
- Streaming and non-streaming responses
- Tool calling support
- Model listing functionality
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


class OpenRouterLLMProvider(LLMProvider):
    """OpenRouter LLM provider using OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "moonshotai/kimi-k2:free",
        timeout: int = 30,
    ):
        """
        Initialize the OpenRouter LLM provider.

        Args:
            api_key: OpenRouter API key
            base_url: Base URL for the OpenRouter API
            model: Default model to use
            timeout: Request timeout in seconds
        """
        if not api_key:
            raise ValueError("API key is required for OpenRouterLLMProvider")

        self.api_key = api_key
        self.base_url = base_url
        self.default_model = model
        self.timeout = timeout

        # Initialize OpenAI client for OpenRouter
        self.client = AsyncOpenAI(
            api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
        )

        logger.info(
            f"OpenRouterLLMProvider initialized with model={self.default_model}, "
            f"timeout={self.timeout}s, base_url={self.base_url}"
        )

    async def chat_completion(
        self, messages: list[dict[str, Any]], **kwargs
    ) -> dict[str, Any]:
        """
        Generate a chat completion using OpenRouter.

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
            logger.error(f"Error in OpenRouter chat completion: {e}")
            raise

    # Provider-specific handlers are deduplicated via common utilities

    async def list_models(self) -> list[dict[str, Any]]:
        """
        List available models from OpenRouter.

        Returns:
            List of model dictionaries with id, name, and other metadata
        """
        try:
            import httpx

            # Use direct HTTP request for models endpoint
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()

                data = response.json()
                models = []

                # Parse OpenRouter models response
                for model in data.get("data", []):
                    models.append(
                        {
                            "id": model.get("id", ""),
                            "name": model.get("name", model.get("id", "")),
                            "description": model.get("description", ""),
                            "context_length": model.get("context_length", 0),
                            "pricing": model.get("pricing", {}),
                        }
                    )

                logger.info(f"Retrieved {len(models)} models from OpenRouter")
                return models

        except Exception as e:
            logger.error(f"Error listing OpenRouter models: {e}")
            return []
