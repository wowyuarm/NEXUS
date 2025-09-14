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
import os
import asyncio
import json
from typing import Dict
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Role
from nexus.core.topics import Topics
from nexus.services.config import ConfigService
from .providers.google import GoogleLLMProvider
from .providers.openrouter import OpenRouterLLMProvider
from .providers.deepseek import DeepSeekLLMProvider

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

        elif provider_name == "deepseek":
            # Get basic DeepSeek configuration
            api_key = self.config_service.get("llm.providers.deepseek.api_key")
            base_url = self.config_service.get("llm.providers.deepseek.base_url", "https://api.deepseek.com/v1")
            model = self.config_service.get("llm.providers.deepseek.model", "deepseek-chat")
            timeout = self.config_service.get_int("llm.timeout", DEFAULT_TIMEOUT)

            if not api_key:
                raise ValueError("DeepSeek API key not found in configuration")

            return DeepSeekLLMProvider(
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

            # If running in E2E fake mode, simulate streaming, tool call, and final result to avoid external dependencies
            if os.getenv("NEXUS_E2E_FAKE_LLM", "0") == "1":
                await self._handle_fake_llm_flow(message, messages, tools)
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
        # Normalize messages to satisfy provider requirements (e.g., Google needs tool 'name')
        normalized_messages = self._normalize_messages_for_provider(messages)

        return await self.provider.client.chat.completions.create(
            model=self.provider.default_model,
            messages=normalized_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools if tools else None,
            stream=True
        )

    def _normalize_messages_for_provider(self, messages: list[dict]) -> list[dict]:
        """Normalize messages to be compatible across providers.

        - Ensures tool-role messages include a non-empty 'name'. If missing, we
          backfill using the preceding assistant tool_calls matched by tool_call_id.
        - Ensures tool message content is a string (JSON-serialized if needed).
        - Leaves other roles untouched.
        """
        try:
            # Map tool_call_id -> function.name from the most recent assistant message
            call_id_to_name: dict[str, str] = {}

            for msg in messages:
                role = msg.get("role")
                if role == "assistant" and isinstance(msg.get("tool_calls"), list):
                    for tc in msg["tool_calls"]:
                        try:
                            call_id = (tc or {}).get("id") or ""
                            fn = (tc or {}).get("function", {})
                            fn_name = (fn or {}).get("name") or ""
                            if call_id and fn_name:
                                call_id_to_name[call_id] = fn_name
                        except Exception:
                            # Be resilient to unexpected structures
                            continue

            normalized: list[dict] = []
            for msg in messages:
                if msg.get("role") == "tool":
                    # Copy to avoid mutating the caller's list
                    tool_msg = dict(msg)
                    name = tool_msg.get("name") or tool_msg.get("tool_name") or ""
                    tool_call_id = tool_msg.get("tool_call_id") or ""

                    if not name:
                        # Backfill using linked assistant tool call
                        if tool_call_id and tool_call_id in call_id_to_name:
                            name = call_id_to_name[tool_call_id]
                        else:
                            name = "unknown"
                        tool_msg["name"] = name

                    # Ensure content is a string
                    content_val = tool_msg.get("content")
                    if not isinstance(content_val, str):
                        try:
                            import json as _json
                            tool_msg["content"] = _json.dumps(content_val, ensure_ascii=False)
                        except Exception:
                            tool_msg["content"] = str(content_val)

                    normalized.append(tool_msg)
                else:
                    normalized.append(msg)

            return normalized
        except Exception:
            # On any failure, return original messages for safety
            return messages

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
        """Publish tool_call_started events via LLM_RESULTS after text chunks.

        Supports both provider objects (with attributes) and dict structures.
        """
        for tool_call in tool_calls:
            tool_name = "unknown"
            tool_args = {}

            # Handle object-like tool call (provider SDK)
            if hasattr(tool_call, 'function'):
                function_info = tool_call.function
                if hasattr(function_info, 'name'):
                    tool_name = function_info.name
                if hasattr(function_info, 'arguments'):
                    try:
                        if isinstance(function_info.arguments, str):
                            tool_args = json.loads(function_info.arguments)
                        else:
                            tool_args = function_info.arguments
                    except (json.JSONDecodeError, AttributeError):
                        tool_args = {"raw_arguments": str(getattr(function_info, 'arguments', ''))}
            # Handle dict-based tool call (our fake path)
            elif isinstance(tool_call, dict):
                function_info = tool_call.get("function", {})
                tool_name = function_info.get("name", "unknown")
                raw_args = function_info.get("arguments")
                try:
                    if isinstance(raw_args, str):
                        tool_args = json.loads(raw_args)
                    elif isinstance(raw_args, dict):
                        tool_args = raw_args
                    else:
                        tool_args = {"raw_arguments": str(raw_args)}
                except json.JSONDecodeError:
                    tool_args = {"raw_arguments": str(raw_args)}

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

    async def _handle_fake_llm_flow(self, original_message: Message, messages, tools) -> None:
        """Simulate streaming, optional tool call, and final result for E2E tests.

        This avoids reliance on external LLM providers and ensures deterministic UI events
        so E2E tests can pass in isolated environments.
        """
        run_id = original_message.run_id
        session_id = original_message.session_id

        # 1) Stream a few text chunks
        for chunk in ["Thinking...", " Analyzing context...", " Preparing response."]:
            await self._publish_text_chunk(run_id, session_id, chunk)

        # 2) Optionally emit a single web_search tool call if tools include it
        has_web_search = any(
            (t.get("function", {}).get("name") == "web_search") if isinstance(t, dict) else False
            for t in (tools or [])
        )
        tool_calls = None
        if has_web_search:
            # Emit tool_call_started via LLM_RESULTS to be forwarded by Orchestrator
            await self._publish_tool_call_events(
                run_id,
                session_id,
                [{
                    "id": "call_fake_1",
                    "type": "function",
                    "function": {"name": "web_search", "arguments": json.dumps({"query": "artificial intelligence news"})}
                }]
            )
            tool_calls = [{
                "id": "call_fake_1",
                "type": "function",
                "function": {"name": "web_search", "arguments": json.dumps({"query": "artificial intelligence news"})}
            }]

        # 3) Send final result (no actual provider call)
        await self._send_final_streaming_result(run_id, session_id, [" Here is a concise summary."], tool_calls)

    def _format_tool_calls(self, tool_calls) -> list:
        """Format tool calls to expected structure; supports object or dict."""
        formatted_tool_calls = []
        for tool_call in tool_calls:
            if hasattr(tool_call, 'id') and hasattr(tool_call, 'type') and hasattr(tool_call, 'function'):
                formatted_tool_calls.append({
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": getattr(tool_call.function, 'name', 'unknown'),
                        "arguments": getattr(tool_call.function, 'arguments', {})
                    }
                })
            elif isinstance(tool_call, dict):
                formatted_tool_calls.append({
                    "id": tool_call.get("id", ""),
                    "type": tool_call.get("type", "function"),
                    "function": {
                        "name": tool_call.get("function", {}).get("name", "unknown"),
                        "arguments": tool_call.get("function", {}).get("arguments", {})
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
