"""
Integration tests for LLMService.

These tests verify that LLMService correctly handles event-driven interactions
via NexusBus, including proper LLM request handling and result publishing. All external
dependencies (LLM providers, API calls) are mocked to ensure isolation while testing
the service's integration with the event bus system.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from nexus.services.llm.service import LLMService
from nexus.core.models import Message, Role
from nexus.core.topics import Topics


class TestLLMServiceIntegration:
    """Integration test suite for LLMService event-driven behavior."""

    @pytest.fixture
    def mock_bus(self):
        """Create a mock NexusBus for testing."""
        mock_bus = Mock()
        mock_bus.publish = AsyncMock()
        mock_bus.subscribe = Mock()
        return mock_bus

    @pytest.fixture
    def mock_config_service(self):
        """Create a mock ConfigService for testing."""
        mock_service = Mock()
        mock_service.get.side_effect = lambda key, default=None: {
            "llm.provider": "google",
            "llm.providers.google.api_key": "test-api-key",
            "llm.providers.google.base_url": "https://test-api.google.com",
            "llm.providers.google.model": "gemini-2.5-flash"
        }.get(key, default)
        mock_service.get_float.return_value = 0.7  # temperature
        mock_service.get_int.side_effect = lambda key, default: {
            "llm.max_tokens": 4096,
            "llm.timeout": 30
        }.get(key, default)
        # New getters used by dynamic provider path
        mock_service.get_user_defaults.return_value = {
            "config": {
                "model": "gemini-2.5-flash",
                "temperature": 0.7,
                "max_tokens": 4096,
                "timeout": 30
            },
            "prompts": {}
        }
        mock_service.get_llm_catalog.return_value = {
            "gemini-2.5-flash": {"provider": "google"}
        }
        def _get_provider_config(name: str):
            data = {
                "google": {
                    "api_key": "test-api-key",
                    "base_url": "https://test-api.google.com",
                }
            }
            return data.get(name, {})
        mock_service.get_provider_config.side_effect = _get_provider_config
        return mock_service

    @pytest.fixture
    def mock_google_provider(self):
        """Create a mock GoogleLLMProvider for testing."""
        mock_provider = Mock()
        mock_provider.chat_completion = AsyncMock()
        # For dynamic path, provider is passed around; keep minimal API
        mock_provider.client = Mock()
        mock_provider.default_model = "gemini-2.5-flash"
        mock_provider.client.chat = Mock()
        mock_provider.client.chat.completions = Mock()
        mock_provider.client.chat.completions.create = AsyncMock()
        return mock_provider

    @pytest.fixture
    def llm_service(self, mock_bus, mock_config_service, mock_google_provider, mocker):
        """Create LLMService instance with mocked dependencies."""
        # Mock the GoogleLLMProvider class to return our mock instance
        mocker.patch('nexus.services.llm.service.GoogleLLMProvider', return_value=mock_google_provider)
        
        service = LLMService(bus=mock_bus, config_service=mock_config_service)
        return service

    @pytest.mark.asyncio
    async def test_handle_llm_request_success(self, llm_service, mock_bus, mock_google_provider):
        """
        Test that LLMService correctly handles LLM_REQUESTS and publishes
        properly formatted LLM_RESULTS with content and tool_calls.
        """
        # Arrange: Prepare input message
        input_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.SYSTEM,
            content={
                "messages": [
                    {"role": "system", "content": "You are Xi, an AI assistant."},
                    {"role": "user", "content": "What is machine learning?"}
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "description": "Search the web for information"
                        }
                    }
                ]
            }
        )

        # Configure mock streaming results
        expected_tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "web_search",
                    "arguments": '{"query": "machine learning definition"}'
                }
            }
        ]

        # Mock the streaming components since streaming is enabled by default
        with patch.object(llm_service, '_create_streaming_response_with_provider') as mock_create_stream:
            with patch.object(llm_service, '_process_streaming_chunks') as mock_process_chunks:
                with patch.object(llm_service, '_send_final_streaming_result') as mock_send_final:
                    
                    # Configure mocks for streaming
                    mock_response = Mock()
                    mock_create_stream.return_value = mock_response
                    mock_process_chunks.return_value = (["Machine learning is..."], expected_tool_calls)
                    
                    # Act: Handle the LLM request
                    await llm_service.handle_llm_request(input_message)
                    
                    # Assert: Verify streaming methods were called
                    mock_create_stream.assert_called_once()
                    mock_process_chunks.assert_called_once_with(mock_response, "test-run-123", "test-session-456")
                    mock_send_final.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_llm_request_non_streaming_success(self, llm_service, mock_bus, mock_google_provider, mocker):
        """
        Adapted for dynamic provider design: verify that the streaming executor is invoked.
        """
        # Arrange: Prepare input message
        input_message = Message(
            run_id="test-run-456",
            owner_key="test-session-789",
            role=Role.SYSTEM,
            content={
                "messages": [
                    {"role": "system", "content": "You are Xi, an AI assistant."},
                    {"role": "user", "content": "Explain quantum computing"}
                ],
                "tools": []
            }
        )

        # Patch executor and assert it is called once with expected args
        with patch.object(llm_service, '_execute_streaming_with_provider', new=AsyncMock()) as mock_exec:
            await llm_service.handle_llm_request(input_message)
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_llm_request_error_handling(self, llm_service, mock_bus, mock_google_provider):
        """
        Test that LLMService properly handles errors and publishes error response.
        """
        # Arrange: Prepare input message
        input_message = Message(
            run_id="test-run-error",
            owner_key="test-session-error",
            role=Role.SYSTEM,
            content={
                "messages": [
                    {"role": "user", "content": "Test message"}
                ],
                "tools": []
            }
        )

        # Mock _execute_streaming_with_provider to raise exception
        with patch.object(llm_service, '_execute_streaming_with_provider', side_effect=Exception("API timeout error")):
            # Act: Handle the LLM request
            await llm_service.handle_llm_request(input_message)

        # Assert: Verify that error response was published
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        
        # Verify topic
        assert call_args[0][0] == Topics.LLM_RESULTS
        
        # Verify error message structure
        published_message = call_args[0][1]
        assert published_message.run_id == "test-run-error"
        assert published_message.owner_key == "test-session-error"
        assert published_message.role == Role.SYSTEM
        
        # Verify error content
        content = published_message.content
        assert "Error processing LLM request" in content["content"]
        assert content["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_handle_llm_request_missing_messages(self, llm_service, mock_bus):
        """
        Test that LLMService handles missing messages gracefully.
        """
        # Arrange: Prepare input message without messages
        input_message = Message(
            run_id="test-run-missing",
            owner_key="test-session-missing",
            role=Role.SYSTEM,
            content={
                "tools": []
                # Missing messages
            }
        )

        # Act: Handle the LLM request
        await llm_service.handle_llm_request(input_message)

        # Assert: Verify that no response was published (early return)
        mock_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_fake_llm_flow(self, llm_service, mock_bus, mocker):
        """
        Test the fake LLM flow used for E2E testing.
        """
        # Arrange: Set E2E fake mode
        mocker.patch.dict('os.environ', {'NEXUS_E2E_FAKE_LLM': '1'})
        
        input_message = Message(
            run_id="test-run-fake",
            owner_key="test-session-fake",
            role=Role.SYSTEM,
            content={
                "messages": [
                    {"role": "user", "content": "Test message"}
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {"name": "web_search"}
                    }
                ]
            }
        )

        # Mock the fake flow method
        with patch.object(llm_service, '_handle_fake_llm_flow') as mock_fake_flow:
            # Act: Handle the LLM request
            await llm_service.handle_llm_request(input_message)
            
            # Assert: Verify fake flow was called
            mock_fake_flow.assert_called_once()

    def test_subscribe_to_bus(self, llm_service, mock_bus):
        """
        Test that LLMService correctly subscribes to the appropriate topics.
        """
        # Act: Subscribe to bus
        llm_service.subscribe_to_bus()

        # Assert: Verify subscription to correct topic
        mock_bus.subscribe.assert_called_once_with(
            Topics.LLM_REQUESTS,
            llm_service.handle_llm_request
        )

    @pytest.mark.asyncio
    async def test_send_final_streaming_result(self, llm_service, mock_bus):
        """
        Test the _send_final_streaming_result method directly.
        """
        # Arrange
        run_id = "test-run-final"
        owner_key = "test-session-final"
        content_chunks = ["Hello", " world", "!"]
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "test_tool", "arguments": "{}"}
            }
        ]

        # Act: Send final result
        await llm_service._send_final_streaming_result(run_id, owner_key, content_chunks, tool_calls)

        # Assert: Verify final result was published
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        
        # Verify topic
        assert call_args[0][0] == Topics.LLM_RESULTS
        
        # Verify message structure
        published_message = call_args[0][1]
        assert published_message.run_id == run_id
        assert published_message.owner_key == owner_key
        assert published_message.role == Role.AI
        
        # Verify content
        content = published_message.content
        assert content["content"] == "Hello world!"
        assert content["tool_calls"] is not None
