"""
LLM service for NEXUS.

This service handles LLM requests by coordinating with pluggable LLM providers.
It subscribes to LLM request topics on the NexusBus and publishes results.

Features:
- Real-time streaming responses with configurable chunk delays
- Universal LLM parameters (temperature, max_tokens, timeout) from configuration
- Consistent behavior across different LLM providers
- Automatic text chunk publishing for streaming effects via Topics.LLM_RESULTS

The service publishes text chunks and tool-call-start events to Topics.LLM_RESULTS during
streaming for the Orchestrator to forward to UI (preserving order). It then sends the final
result with any tool calls to the LLM_RESULTS topic as a consolidated message.
"""

import logging
import asyncio
import json
from typing import Dict
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Role
from nexus.core.topics import Topics
from nexus.services.config import ConfigService
from .providers.google import GoogleLLMProvider
from .providers.openrouter import OpenRouterLLMProvider

logger = logging.getLogger(__name__)

# Default LLM parameters
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 30
STREAMING_CHUNK_DELAY = 0.05  # 50ms delay between chunks for realistic streaming
TOOL_EVENT_ORDERING_DELAY = 0.1  # 100ms delay to ensure proper event ordering


class LLMService:
    def __init__(self, bus: NexusBus, config_service: ConfigService):
        self.bus = bus
        self.config_service = config_service

        # Initialize the LLM provider based on configuration
        self.provider = self._initialize_provider()
        logger.info("LLMService initialized with provider")

    def _initialize_provider(self):
        """Initialize the LLM provider based on configuration."""
        provider_name = self.config_service.get("llm.provider", "google")

        if provider_name == "google":
            api_key = self.config_service.get("llm.providers.google.api_key")
            base_url = self.config_service.get("llm.providers.google.base_url")
            model = self.config_service.get("llm.providers.google.model", "gemini-2.5-flash")
            timeout = self.config_service.get_int("llm.timeout", DEFAULT_TIMEOUT)

            if not api_key:
                raise ValueError("Google API key not found in configuration")
            if not base_url:
                raise ValueError("Google base URL not found in configuration")

            return GoogleLLMProvider(api_key=api_key, base_url=base_url, model=model, timeout=timeout)

        elif provider_name == "openrouter":
            # Get basic OpenRouter configuration
            api_key = self.config_service.get("llm.providers.openrouter.api_key")
            base_url = self.config_service.get("llm.providers.openrouter.base_url", "https://openrouter.ai/api/v1")
            model = self.config_service.get("llm.providers.openrouter.model", "moonshotai/kimi-k2:free")
            timeout = self.config_service.get_int("llm.timeout", DEFAULT_TIMEOUT)

            if not api_key:
                raise ValueError("OpenRouter API key not found in configuration")

            return OpenRouterLLMProvider(
                api_key=api_key,
                base_url=base_url,
                model=model,
                timeout=timeout
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")

    def subscribe_to_bus(self) -> None:
        """Subscribe to LLM request topics."""
        self.bus.subscribe(Topics.LLM_REQUESTS, self.handle_llm_request)
        logger.info("LLMService subscribed to NexusBus")

    async def handle_llm_request(self, message: Message) -> None:
        """
        Handle LLM completion requests.

        Extracts messages and tools from the request, applies universal LLM parameters
        (temperature, max_tokens, timeout) from configuration, and forwards the request to the
        configured LLM provider. Supports both streaming and non-streaming responses.

        Args:
            message: Message containing 'messages' list, 'tools' list and 'run_id'
        """
        try:
            logger.info(f"Handling LLM request for run_id={message.run_id}")

            # Extract messages, tools and run_id from the message content
            content = message.content
            messages = content.get("messages", [])
            tools = content.get("tools", [])
            run_id = message.run_id

            if not messages:
                logger.error(f"No messages found in LLM request for run_id={run_id}")
                return

            # Get universal LLM parameters from configuration
            temperature = self.config_service.get_float("llm.temperature", DEFAULT_TEMPERATURE)
            max_tokens = self.config_service.get_int("llm.max_tokens", DEFAULT_MAX_TOKENS)

            # Enable streaming by default for better UX
            stream = True

            # Call the LLM provider with tools and parameters
            if stream:
                # Handle streaming response in real-time
                await self._handle_real_time_streaming(message, messages, tools, temperature, max_tokens)
            else:
                # Handle non-streaming response
                result = await self.provider.chat_completion(
                    messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False
                )
                await self._handle_non_streaming_result(message, result)

        except Exception as e:
            logger.error(f"Error handling LLM request for run_id={message.run_id}: {e}")
            # Publish error result
            error_message = Message(
                run_id=message.run_id,
                session_id=message.session_id,
                role=Role.SYSTEM,
                content={
                    "content": f"Error processing LLM request: {str(e)}",
                    "tool_calls": None
                }
            )
            await self.bus.publish(Topics.LLM_RESULTS, error_message)

    async def _handle_real_time_streaming(self, original_message: Message, messages, tools, temperature, max_tokens) -> None:
        """Handle real-time streaming LLM response."""
        run_id = original_message.run_id
        session_id = original_message.session_id

        # Get streaming response from provider
        response = await self._create_streaming_response(messages, tools, temperature, max_tokens)

        # Process streaming chunks and collect results
        content_chunks, tool_calls = await self._process_streaming_chunks(response, run_id, session_id)

        # Send final result
        await self._send_final_streaming_result(run_id, session_id, content_chunks, tool_calls)

    async def _create_streaming_response(self, messages, tools, temperature, max_tokens):
        """Create streaming response from LLM provider."""
        return await self.provider.client.chat.completions.create(
            model=self.provider.default_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools if tools else None,
            stream=True
        )

    async def _process_streaming_chunks(self, response, run_id: str, session_id: str):
        """Process streaming chunks and publish them in real-time.

        Ensures proper event ordering: all text_chunk events are published first,
        then tool_call_started events are published after all content is streamed.
        """
        content_chunks = []
        tool_calls = None

        async for chunk in response:
            if chunk.choices:
                delta = chunk.choices[0].delta

                # Handle content chunks - publish immediately for real-time streaming
                if hasattr(delta, 'content') and delta.content:
                    content_chunks.append(delta.content)
                    await self._publish_text_chunk(run_id, session_id, delta.content)

                # Collect tool calls but don't publish yet - wait until all content is streamed
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    tool_calls = delta.tool_calls

        # After all content chunks are streamed, publish tool_call_started events
        if tool_calls:
            logger.info(f"All text chunks streamed for run_id={run_id}, now publishing tool_call_started events")
            await self._publish_tool_call_events(run_id, session_id, tool_calls)

        return content_chunks, tool_calls

    async def _publish_text_chunk(self, run_id: str, session_id: str, chunk: str) -> None:
        """Publish a single text chunk via LLM_RESULTS for Orchestrator forwarding."""
        chunk_event = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.SYSTEM,
            content={
                "event": "text_chunk",
                "run_id": run_id,
                "payload": {"chunk": chunk}
            }
        )
        # Publish to LLM_RESULTS so Orchestrator can forward to UI preserving order
        await self.bus.publish(Topics.LLM_RESULTS, chunk_event)
        logger.info(f"Published text chunk (LLM_RESULTS) for run_id={run_id}: '{chunk[:50]}...'")

        # Add delay for realistic streaming
        await asyncio.sleep(STREAMING_CHUNK_DELAY)

    async def _publish_tool_call_events(self, run_id: str, session_id: str, tool_calls) -> None:
        """Publish tool_call_started events via LLM_RESULTS after text chunks."""
        for tool_call in tool_calls:
            # Extract tool information from the tool call
            function_info = tool_call.function if hasattr(tool_call, 'function') else {}
            tool_name = function_info.name if hasattr(function_info, 'name') else "unknown"

            # Parse arguments - they might be a string that needs to be parsed as JSON
            tool_args = {}
            if hasattr(function_info, 'arguments'):
                try:
                    if isinstance(function_info.arguments, str):
                        tool_args = json.loads(function_info.arguments)
                    else:
                        tool_args = function_info.arguments
                except (json.JSONDecodeError, AttributeError):
                    tool_args = {"raw_arguments": str(function_info.arguments)}

            # Create and publish tool_call_started event
            tool_event = Message(
                run_id=run_id,
                session_id=session_id,
                role=Role.SYSTEM,
                content={
                    "event": "tool_call_started",
                    "run_id": run_id,
                    "payload": {
                        "tool_name": tool_name,
                        "args": tool_args
                    }
                }
            )
            # Publish to LLM_RESULTS so Orchestrator forwards after chunks
            await self.bus.publish(Topics.LLM_RESULTS, tool_event)
            logger.info(f"Published tool_call_started (LLM_RESULTS) for run_id={run_id}, tool={tool_name}")

        # Add a small delay to ensure proper event ordering
        await asyncio.sleep(TOOL_EVENT_ORDERING_DELAY)

    async def _send_final_streaming_result(self, run_id: str, session_id: str, content_chunks: list, tool_calls) -> None:
        """Send the final streaming result with tool calls."""
        full_content = ''.join(content_chunks) if content_chunks else None
        formatted_tool_calls = self._format_tool_calls(tool_calls) if tool_calls else None

        result_message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.AI,
            content={
                "content": full_content,
                "tool_calls": formatted_tool_calls
            }
        )
        await self.bus.publish(Topics.LLM_RESULTS, result_message)
        logger.info(f"Published real-time streaming LLM result for run_id={run_id}")

    def _format_tool_calls(self, tool_calls) -> list:
        """Format tool calls to expected structure."""
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
        return formatted_tool_calls

    async def _handle_non_streaming_result(self, original_message: Message, result: Dict) -> None:
        """Handle non-streaming LLM result."""
        run_id = original_message.run_id
        session_id = original_message.session_id

        # Create result message
        result_message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.AI,
            content={
                "content": result["content"],
                "tool_calls": result["tool_calls"]
            }
        )

        # Publish the result
        await self.bus.publish(Topics.LLM_RESULTS, result_message)
        logger.info(f"Published LLM result for run_id={run_id}")
