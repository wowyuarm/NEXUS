"""Unit tests for GoogleLLMProvider class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from openai import APIError, APIConnectionError, RateLimitError
from requests.exceptions import ConnectionError

from nexus.services.llm.providers.google import GoogleLLMProvider


class TestGoogleLLMProvider:
    """Test suite for GoogleLLMProvider functionality."""

    @pytest.fixture
    def google_provider(self):
        """Fixture providing a GoogleLLMProvider instance for testing."""
        return GoogleLLMProvider(
            api_key="test_api_key_123",
            base_url="https://generativelanguage.googleapis.com",
            model="gemini-2.5-flash",
            timeout=30
        )

    @pytest.fixture
    def sample_messages(self):
        """Fixture providing sample messages for testing."""
        return [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"},
            {"role": "user", "content": "What's the weather like today?"}
        ]

    @pytest.fixture
    def sample_tools(self):
        """Fixture providing sample tools for testing."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the current weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. San Francisco, CA"
                            }
                        },
                        "required": ["location"]
                    }
                }
            }
        ]

    def test_initialization_with_no_api_key(self):
        """Test that initializing GoogleLLMProvider with an empty api_key raises ValueError."""
        with pytest.raises(ValueError, match="API key is required for GoogleLLMProvider"):
            GoogleLLMProvider(api_key="", base_url="https://generativelanguage.googleapis.com")

    def test_initialization_with_valid_api_key(self):
        """Test successful initialization with valid API key."""
        provider = GoogleLLMProvider(
            api_key="valid_api_key_123",
            base_url="https://generativelanguage.googleapis.com"
        )
        
        assert provider.api_key == "valid_api_key_123"
        assert provider.base_url == "https://generativelanguage.googleapis.com"
        assert provider.default_model == "gemini-2.5-flash"
        assert provider.timeout == 30

    @pytest.mark.asyncio
    async def test_chat_completion_success(self, google_provider, sample_messages, mocker):
        """Test successful chat completion with content and tool calls."""
        # Mock the AsyncOpenAI client and its chat.completions.create method
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "The weather is sunny today!"
        # Create a proper tool call object
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "get_weather"
        mock_tool_call.function.arguments = '{"location": "San Francisco, CA"}'
        
        mock_response.choices[0].message.tool_calls = [mock_tool_call]

        mock_client = mocker.patch.object(google_provider, 'client')
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Mock logger to capture info logs
        mock_logger = mocker.patch('nexus.services.llm.providers.google.logger')

        # Call the method
        result = await google_provider.chat_completion(sample_messages)

        # Verify the result
        assert result["content"] == "The weather is sunny today!"
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["id"] == "call_123"
        assert result["tool_calls"][0]["type"] == "function"
        assert result["tool_calls"][0]["function"]["name"] == "get_weather"
        assert result["tool_calls"][0]["function"]["arguments"] == '{"location": "San Francisco, CA"}'

        # Verify the API call was made with correct parameters
        mock_client.chat.completions.create.assert_called_once_with(
            model="gemini-2.5-flash",
            messages=sample_messages,
            temperature=0.7,
            max_tokens=4096,
            stream=False
        )

        # Verify logging
        mock_logger.info.assert_called()
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Requesting chat completion" in call for call in info_calls)
        assert any("Chat completion successful" in call for call in info_calls)

    @pytest.mark.asyncio
    async def test_chat_completion_with_tools(self, google_provider, sample_messages, sample_tools, mocker):
        """Test successful chat completion with tools parameter."""
        # Mock the AsyncOpenAI client and its chat.completions.create method
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = None
        # Create a proper tool call object
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_456"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "get_weather"
        mock_tool_call.function.arguments = '{"location": "New York, NY"}'
        
        mock_response.choices[0].message.tool_calls = [mock_tool_call]

        mock_client = mocker.patch.object(google_provider, 'client')
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Call the method with tools
        result = await google_provider.chat_completion(sample_messages, tools=sample_tools)

        # Verify the result
        assert result["content"] is None
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["id"] == "call_456"
        assert result["tool_calls"][0]["function"]["name"] == "get_weather"

        # Verify the API call was made with tools parameter
        mock_client.chat.completions.create.assert_called_once_with(
            model="gemini-2.5-flash",
            messages=sample_messages,
            temperature=0.7,
            max_tokens=4096,
            stream=False,
            tools=sample_tools
        )

    @pytest.mark.asyncio
    async def test_chat_completion_api_error(self, google_provider, sample_messages, mocker):
        """Test that API errors are properly propagated."""
        # Mock the AsyncOpenAI client to raise an Exception
        mock_client = mocker.patch.object(google_provider, 'client')
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error occurred"))

        # Mock logger to capture error logs
        mock_logger = mocker.patch('nexus.services.llm.providers.google.logger')

        # Call the method and expect Exception to be raised
        with pytest.raises(Exception, match="API error occurred"):
            await google_provider.chat_completion(sample_messages)

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Error in chat completion" in error_call
        assert "API error occurred" in error_call

    @pytest.mark.asyncio
    async def test_chat_completion_connection_error(self, google_provider, sample_messages, mocker):
        """Test that connection errors are properly propagated."""
        # Mock the AsyncOpenAI client to raise a ConnectionError
        mock_client = mocker.patch.object(google_provider, 'client')
        mock_client.chat.completions.create = AsyncMock(
            side_effect=ConnectionError("Connection failed")
        )

        # Mock logger to capture error logs
        mock_logger = mocker.patch('nexus.services.llm.providers.google.logger')

        # Call the method and expect ConnectionError to be raised
        with pytest.raises(ConnectionError, match="Connection failed"):
            await google_provider.chat_completion(sample_messages)

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Error in chat completion" in error_call
        assert "Connection failed" in error_call

    @pytest.mark.asyncio
    async def test_chat_completion_rate_limit_error(self, google_provider, sample_messages, mocker):
        """Test that rate limit errors are properly propagated."""
        # Mock the AsyncOpenAI client to raise a generic Exception for rate limiting
        mock_client = mocker.patch.object(google_provider, 'client')
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Rate limit exceeded")
        )

        # Mock logger to capture error logs
        mock_logger = mocker.patch('nexus.services.llm.providers.google.logger')

        # Call the method and expect Exception to be raised
        with pytest.raises(Exception, match="Rate limit exceeded"):
            await google_provider.chat_completion(sample_messages)

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Error in chat completion" in error_call
        assert "Rate limit exceeded" in error_call

    @pytest.mark.asyncio
    async def test_chat_completion_empty_response(self, google_provider, sample_messages, mocker):
        """Test handling of empty response from API."""
        # Mock the AsyncOpenAI client to return empty response
        mock_response = MagicMock()
        mock_response.choices = []  # Empty choices list

        mock_client = mocker.patch.object(google_provider, 'client')
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Call the method
        result = await google_provider.chat_completion(sample_messages)

        # Verify the result has None content and no tool calls
        assert result["content"] is None
        assert result["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_chat_completion_custom_parameters(self, google_provider, sample_messages, mocker):
        """Test chat completion with custom parameters."""
        # Mock the AsyncOpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Custom response"
        mock_response.choices[0].message.tool_calls = None

        mock_client = mocker.patch.object(google_provider, 'client')
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Call the method with custom parameters (without streaming for simplicity)
        result = await google_provider.chat_completion(
            sample_messages,
            model="gemini-pro",
            temperature=0.2,
            max_tokens=1024,
            stream=False
        )

        # Verify the result
        assert result["content"] == "Custom response"
        assert result["tool_calls"] is None

        # Verify the API call was made with custom parameters
        mock_client.chat.completions.create.assert_called_once_with(
            model="gemini-pro",
            messages=sample_messages,
            temperature=0.2,
            max_tokens=1024,
            stream=False
        )

    @pytest.mark.asyncio
    async def test_chat_completion_streaming_response(self, google_provider, sample_messages, mocker):
        """Test handling of streaming response from API."""
        # Mock the streaming response
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta = MagicMock()
        mock_chunk1.choices[0].delta.content = "Hello"
        mock_chunk1.choices[0].delta.tool_calls = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta = MagicMock()
        mock_chunk2.choices[0].delta.content = " world!"
        mock_chunk2.choices[0].delta.tool_calls = None

        # Create an async generator for the streaming response
        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        mock_response = mock_stream()

        mock_client = mocker.patch.object(google_provider, 'client')
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Call the method with streaming enabled
        result = await google_provider.chat_completion(sample_messages, stream=True)

        # Verify the result contains combined content and chunks
        assert result["content"] == "Hello world!"
        assert result["tool_calls"] is None
        assert "content_chunks" in result
        assert result["content_chunks"] == ["Hello", " world!"]

    @pytest.mark.asyncio
    async def test_chat_completion_streaming_with_tool_calls(self, google_provider, sample_messages, mocker):
        """Test handling of streaming response with tool calls."""
        # Mock the streaming response with tool calls in final chunk
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta = MagicMock()
        mock_chunk1.choices[0].delta.content = "Thinking"
        mock_chunk1.choices[0].delta.tool_calls = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta = MagicMock()
        mock_chunk2.choices[0].delta.content = " about it..."
        # Create a proper tool call object for streaming
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_stream_123"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "get_weather"
        mock_tool_call.function.arguments = '{"location": "London, UK"}'
        
        mock_chunk2.choices[0].delta.tool_calls = [mock_tool_call]

        # Create an async generator for the streaming response
        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        mock_response = mock_stream()

        mock_client = mocker.patch.object(google_provider, 'client')
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Call the method with streaming enabled
        result = await google_provider.chat_completion(sample_messages, stream=True)

        # Verify the result contains combined content and tool calls
        assert result["content"] == "Thinking about it..."
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["id"] == "call_stream_123"
        assert result["tool_calls"][0]["function"]["name"] == "get_weather"
        assert "content_chunks" in result
        assert result["content_chunks"] == ["Thinking", " about it..."]