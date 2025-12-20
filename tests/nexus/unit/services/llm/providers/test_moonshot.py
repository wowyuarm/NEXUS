"""Unit tests for Moonshot LLM provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nexus.services.llm.providers.moonshot import MoonshotLLMProvider


class TestMoonshotLLMProvider:
    """Test suite for MoonshotLLMProvider."""

    def test_moonshot_provider_initialization(self):
        """Verify provider creates client with correct parameters."""
        api_key = "test-api-key"
        base_url = "https://api.moonshot.cn/v1"
        model = "kimi-k2-0905-preview"
        timeout = 30

        with patch("nexus.services.llm.providers.moonshot.AsyncOpenAI") as mock_openai_class:
            provider = MoonshotLLMProvider(
                api_key=api_key, base_url=base_url, model=model, timeout=timeout
            )

            # Verify attributes
            assert provider.api_key == api_key
            assert provider.base_url == base_url
            assert provider.default_model == model
            assert provider.timeout == timeout

            # Verify OpenAI client initialization
            mock_openai_class.assert_called_once_with(
                api_key=api_key, base_url=base_url, timeout=timeout
            )

    def test_moonshot_provider_missing_api_key(self):
        """Missing API key raises ValueError."""
        with pytest.raises(ValueError, match="API key is required"):
            MoonshotLLMProvider(api_key="")

    def test_moonshot_provider_default_base_url(self):
        """Verify default base URL matches Moonshot documentation."""
        api_key = "test-key"

        with patch("openai.AsyncOpenAI"):
            provider = MoonshotLLMProvider(api_key=api_key)

            # Verify default base URL
            assert provider.base_url == "https://api.moonshot.cn/v1"
            assert provider.default_model == "kimi-k2-0905-preview"

    @pytest.mark.asyncio
    async def test_moonshot_provider_chat_completion_params(self):
        """Verify parameter passing to OpenAI client."""
        api_key = "test-key"
        messages = [{"role": "user", "content": "Hello"}]

        with patch("nexus.services.llm.providers.moonshot.AsyncOpenAI") as mock_openai_class:
            mock_client = AsyncMock()
            mock_openai_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = MagicMock()
            mock_response.choices[0].message.content = "Test response"
            mock_response.choices[0].message.tool_calls = None

            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            provider = MoonshotLLMProvider(api_key=api_key)

            # Call chat_completion
            result = await provider.chat_completion(
                messages=messages,
                temperature=0.8,
                max_tokens=100,
                tools=[],
                stream=False,
            )

            # Verify client called with correct params
            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args[1]

            assert call_kwargs["model"] == "kimi-k2-0905-preview"
            assert call_kwargs["messages"] == messages
            assert call_kwargs["temperature"] == 0.8
            assert call_kwargs["max_tokens"] == 100
            assert call_kwargs["stream"] is False
            # tools should not be in kwargs when empty list
            assert "tools" not in call_kwargs

            # Verify result structure
            assert "content" in result
            assert result["content"] == "Test response"
            assert result["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_moonshot_provider_chat_completion_streaming(self):
        """Verify streaming mode works."""
        api_key = "test-key"
        messages = [{"role": "user", "content": "Hello"}]

        with patch("nexus.services.llm.providers.moonshot.AsyncOpenAI") as mock_openai_class:
            mock_client = AsyncMock()
            mock_openai_class.return_value = mock_client

            # Mock streaming response
            mock_stream = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_stream)

            # Mock common utilities
            with patch(
                "nexus.services.llm.providers.moonshot.handle_streaming_response"
            ) as mock_handle:
                mock_handle.return_value = {
                    "content": "Streamed response",
                    "tool_calls": None,
                    "content_chunks": ["Streamed ", "response"],
                }

                provider = MoonshotLLMProvider(api_key=api_key)
                result = await provider.chat_completion(
                    messages=messages, stream=True
                )

                # Verify streaming called
                mock_client.chat.completions.create.assert_called_once()
                call_kwargs = mock_client.chat.completions.create.call_args[1]
                assert call_kwargs["stream"] is True

                # Verify streaming handler called
                mock_handle.assert_called_once_with(mock_stream)

                assert result["content"] == "Streamed response"