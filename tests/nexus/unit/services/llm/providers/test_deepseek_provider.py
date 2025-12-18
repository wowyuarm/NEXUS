"""
Unit tests for DeepSeekLLMProvider.

These tests verify that DeepSeekLLMProvider correctly handles LLM API interactions
including chat completion requests, response processing, and error handling.
All external dependencies are mocked to ensure isolation.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from nexus.services.llm.providers.common import (
    handle_non_streaming_response,
    handle_streaming_response,
)
from nexus.services.llm.providers.deepseek import DeepSeekLLMProvider


class TestDeepSeekLLMProvider:
    """Test suite for DeepSeekLLMProvider class."""

    def test_initialization_with_api_key(self, mocker):
        """Test successful initialization with API key."""
        # Mock AsyncOpenAI
        mock_async_openai = mocker.patch(
            "nexus.services.llm.providers.deepseek.AsyncOpenAI"
        )
        mock_client = Mock()
        mock_async_openai.return_value = mock_client

        provider = DeepSeekLLMProvider(
            api_key="test_api_key",
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
            timeout=30,
        )

        assert provider.api_key == "test_api_key"
        assert provider.base_url == "https://api.deepseek.com"
        assert provider.default_model == "deepseek-chat"
        assert provider.timeout == 30
        assert provider.client == mock_client

        # Verify AsyncOpenAI was initialized with correct parameters
        mock_async_openai.assert_called_once_with(
            api_key="test_api_key", base_url="https://api.deepseek.com", timeout=30
        )

    def test_initialization_with_no_api_key(self):
        """Test initialization fails when no API key is provided."""
        with pytest.raises(
            ValueError, match="API key is required for DeepSeekLLMProvider"
        ):
            DeepSeekLLMProvider(api_key="", base_url="https://api.deepseek.com")

    @pytest.mark.asyncio
    async def test_chat_completion_success_no_tools(self, mocker):
        """Test successful chat completion without tools."""
        # Mock the OpenAI client and response
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()

        # Setup mock response structure
        mock_response.choices = [mock_choice]
        mock_choice.message = mock_message
        mock_message.content = "This is a test response"
        mock_message.tool_calls = None

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = DeepSeekLLMProvider(
            api_key="test_api_key", base_url="https://api.deepseek.com"
        )
        provider.client = mock_client

        messages = [{"role": "user", "content": "Hello, how are you?"}]

        result = await provider.chat_completion(messages)

        assert result["content"] == "This is a test response"
        assert result["tool_calls"] is None

        # Verify API was called with correct parameters
        mock_client.chat.completions.create.assert_called_once_with(
            model="deepseek-chat",
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
            stream=False,
        )

    @pytest.mark.asyncio
    async def test_chat_completion_success_with_tools(self, mocker):
        """Test successful chat completion with tools."""
        # Mock the OpenAI client and response
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_tool_call = Mock()

        # Setup mock response structure
        mock_response.choices = [mock_choice]
        mock_choice.message = mock_message
        mock_message.content = "I'll help you search for that information."

        # Setup mock tool call
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "web_search"
        mock_tool_call.function.arguments = '{"query": "weather forecast"}'

        mock_message.tool_calls = [mock_tool_call]

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = DeepSeekLLMProvider(
            api_key="test_api_key", base_url="https://api.deepseek.com"
        )
        provider.client = mock_client

        messages = [{"role": "user", "content": "What's the weather like today?"}]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"],
                    },
                },
            }
        ]

        result = await provider.chat_completion(messages, tools=tools)

        assert result["content"] == "I'll help you search for that information."
        assert result["tool_calls"] is not None
        assert len(result["tool_calls"]) == 1

        tool_call = result["tool_calls"][0]
        assert tool_call["id"] == "call_123"
        assert tool_call["type"] == "function"
        assert tool_call["function"]["name"] == "web_search"
        assert tool_call["function"]["arguments"] == '{"query": "weather forecast"}'

        # Verify API was called with tools
        mock_client.chat.completions.create.assert_called_once_with(
            model="deepseek-chat",
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
            stream=False,
            tools=tools,
        )

    @pytest.mark.asyncio
    async def test_chat_completion_with_custom_parameters(self, mocker):
        """Test chat completion with custom parameters."""
        # Mock the OpenAI client and streaming response
        mock_client = Mock()

        # Build streaming chunks that compose the final content
        def make_chunk(text: str):
            chunk = Mock()
            chunk.choices = [Mock()]
            chunk.choices[0].delta = Mock()
            chunk.choices[0].delta.content = text
            # Explicitly set tool_calls to None to avoid Mock truthiness
            chunk.choices[0].delta.tool_calls = None
            return chunk

        chunk1 = make_chunk("Custom ")
        chunk2 = make_chunk("response")

        async def mock_async_iter():
            for c in [chunk1, chunk2]:
                yield c

        mock_streaming_response = AsyncMock()
        mock_streaming_response.__aiter__ = Mock(return_value=mock_async_iter())

        mock_client.chat.completions.create = AsyncMock(
            return_value=mock_streaming_response
        )

        provider = DeepSeekLLMProvider(
            api_key="test_api_key", base_url="https://api.deepseek.com"
        )
        provider.client = mock_client

        messages = [{"role": "user", "content": "Test message"}]

        result = await provider.chat_completion(
            messages,
            model="deepseek-chat",
            temperature=0.5,
            max_tokens=1024,
            stream=True,
        )

        assert result["content"] == "Custom response"

        # Verify custom parameters were used
        mock_client.chat.completions.create.assert_called_once_with(
            model="deepseek-chat",
            messages=messages,
            temperature=0.5,
            max_tokens=1024,
            stream=True,
        )

    @pytest.mark.asyncio
    async def test_chat_completion_api_error(self, mocker):
        """Test chat completion when API call fails."""
        # Mock the OpenAI client to raise an exception
        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        provider = DeepSeekLLMProvider(
            api_key="test_api_key", base_url="https://api.deepseek.com"
        )
        provider.client = mock_client

        messages = [{"role": "user", "content": "Test message"}]

        with pytest.raises(Exception, match="API Error"):
            await provider.chat_completion(messages)

    @pytest.mark.asyncio
    async def test_chat_completion_no_choices(self, mocker):
        """Test chat completion when response has no choices."""
        # Mock the OpenAI client and response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = []

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = DeepSeekLLMProvider(
            api_key="test_api_key", base_url="https://api.deepseek.com"
        )
        provider.client = mock_client

        messages = [{"role": "user", "content": "Test message"}]

        result = await provider.chat_completion(messages)

        assert result["content"] is None
        assert result["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_handle_streaming_response(self, mocker):
        """Test handling of streaming response."""
        provider = DeepSeekLLMProvider(
            api_key="test_api_key", base_url="https://api.deepseek.com"
        )

        # Mock streaming chunks
        mock_chunk1 = Mock()
        mock_chunk1.choices = [Mock()]
        mock_chunk1.choices[0].delta = Mock()
        mock_chunk1.choices[0].delta.content = "Hello"
        mock_chunk1.choices[0].delta.tool_calls = None

        mock_chunk2 = Mock()
        mock_chunk2.choices = [Mock()]
        mock_chunk2.choices[0].delta = Mock()
        mock_chunk2.choices[0].delta.content = " world"
        mock_chunk2.choices[0].delta.tool_calls = None

        mock_chunk3 = Mock()
        mock_chunk3.choices = [Mock()]
        mock_chunk3.choices[0].delta = Mock()
        mock_chunk3.choices[0].delta.content = "!"
        mock_chunk3.choices[0].delta.tool_calls = None

        # Create an async iterator
        async def mock_async_iter():
            for chunk in [mock_chunk1, mock_chunk2, mock_chunk3]:
                yield chunk

        mock_response = AsyncMock()
        mock_response.__aiter__ = Mock(return_value=mock_async_iter())

        result = await handle_streaming_response(mock_response)

        assert result["content"] == "Hello world!"
        assert result["tool_calls"] is None
        assert "content_chunks" in result
        assert result["content_chunks"] == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    async def test_handle_streaming_response_with_tool_calls(self, mocker):
        """Test handling of streaming response with tool calls."""
        provider = DeepSeekLLMProvider(
            api_key="test_api_key", base_url="https://api.deepseek.com"
        )

        # Mock streaming chunks with tool calls
        mock_chunk = Mock()
        mock_chunk.choices = [Mock()]
        mock_chunk.choices[0].delta = Mock()
        mock_chunk.choices[0].delta.content = None

        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "web_search"
        mock_tool_call.function.arguments = '{"query": "test"}'

        mock_chunk.choices[0].delta.tool_calls = [mock_tool_call]

        # Create an async iterator
        async def mock_async_iter():
            yield mock_chunk

        mock_response = AsyncMock()
        mock_response.__aiter__ = Mock(return_value=mock_async_iter())

        result = await handle_streaming_response(mock_response)

        assert result["content"] is None
        assert result["tool_calls"] is not None
        assert len(result["tool_calls"]) == 1

        tool_call = result["tool_calls"][0]
        assert tool_call["id"] == "call_123"
        assert tool_call["function"]["name"] == "web_search"

    @pytest.mark.asyncio
    async def test_handle_non_streaming_response_no_tool_calls(self, mocker):
        """Test handling of non-streaming response without tool calls."""
        provider = DeepSeekLLMProvider(
            api_key="test_api_key", base_url="https://api.deepseek.com"
        )

        # Mock response
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()

        mock_response.choices = [mock_choice]
        mock_choice.message = mock_message
        mock_message.content = "Test response"
        # No tool_calls attribute
        del mock_message.tool_calls

        result = await handle_non_streaming_response(mock_response)

        assert result["content"] == "Test response"
        assert result["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_handle_non_streaming_response_empty_choices(self, mocker):
        """Test handling of non-streaming response with empty choices."""
        provider = DeepSeekLLMProvider(
            api_key="test_api_key", base_url="https://api.deepseek.com"
        )

        # Mock response with no choices
        mock_response = Mock()
        mock_response.choices = []

        result = await handle_non_streaming_response(mock_response)

        assert result["content"] is None
        assert result["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_chat_completion_with_empty_tools_list(self, mocker):
        """Test chat completion with empty tools list."""
        # Mock the OpenAI client and response
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()

        mock_response.choices = [mock_choice]
        mock_choice.message = mock_message
        mock_message.content = "Response without tools"
        mock_message.tool_calls = None

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = DeepSeekLLMProvider(
            api_key="test_api_key", base_url="https://api.deepseek.com"
        )
        provider.client = mock_client

        messages = [{"role": "user", "content": "Test message"}]

        # Pass empty tools list
        result = await provider.chat_completion(messages, tools=[])

        assert result["content"] == "Response without tools"
        assert result["tool_calls"] is None

        # Verify API was called without tools parameter
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "tools" not in call_kwargs
