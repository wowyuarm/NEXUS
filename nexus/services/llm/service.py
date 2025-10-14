"""
LLM service for NEXUS.

This service handles LLM requests by coordinating with pluggable LLM providers.
It subscribes to LLM request topics on the NexusBus and publishes results.

Key features:
- Dynamic provider selection: Instantiates appropriate LLM provider (Google, DeepSeek,
  OpenRouter) based on requested model from LLM catalog
- User personalization: Composes effective configuration from user profile overrides
  and system defaults (model, temperature, max_tokens)
- Model alias resolution: Supports friendly model names (e.g., "Kimi-K2") mapped to
  provider-specific IDs through catalog
- Real-time streaming: Publishes text chunks with configurable delays for realistic
  streaming UX
- Tool call aggregation: Accumulates streaming tool call deltas to prevent truncated JSON
- Event ordering: Ensures all text chunks are published before tool_call_started events
- Message normalization: Ensures provider compatibility by backfilling missing tool names
  and converting content to strings
- E2E test mode: Fake LLM flow (NEXUS_E2E_FAKE_LLM=1) for isolated testing

Event flow:
The service publishes text_chunk and tool_call_started events to Topics.LLM_RESULTS during
streaming for the Orchestrator to forward to UI (preserving order). It then sends the final
result with complete tool calls to LLM_RESULTS as a consolidated message.
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

        # No longer initialize a single provider - providers are created dynamically per request
        logger.info("LLMService initialized (dynamic provider mode)")


    def subscribe_to_bus(self) -> None:
        """Subscribe to LLM request topics."""
        self.bus.subscribe(Topics.LLM_REQUESTS, self.handle_llm_request)
        logger.info("LLMService subscribed to NexusBus")

    async def handle_llm_request(self, message: Message) -> None:
        """
        Handle LLM completion requests with dynamic provider selection.

        Extracts messages and tools from the request, composes effective configuration
        from user profile and defaults, dynamically selects the appropriate provider,
        and executes the LLM call. Supports both streaming and non-streaming responses.

        Args:
            message: Message containing 'messages' list, 'tools' list, and optional 'user_profile'
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

            # Extract user_profile from content (if provided by Orchestrator)
            user_profile = content.get("user_profile", {})

            # If running in E2E fake mode, simulate streaming, tool call, and final result to avoid external dependencies
            if os.getenv("NEXUS_E2E_FAKE_LLM", "0") == "1":
                await self._handle_fake_llm_flow(message, messages, tools)
                return

            # Compose effective configuration (user overrides + defaults)
            effective_config = self._compose_effective_config(user_profile)
            
            # Get final model name (friendly alias or provider id)
            requested_model = effective_config.get('model')
            model_name = self._resolve_model_name(requested_model)
            temperature = effective_config.get('temperature', DEFAULT_TEMPERATURE)
            max_tokens = effective_config.get('max_tokens', DEFAULT_MAX_TOKENS)
            
            logger.info(f"Using model '{model_name}' with temperature={temperature}, max_tokens={max_tokens} for run_id={run_id}")

            # Dynamically get provider for this specific model
            provider = self._get_provider_for_model(model_name)

            # Enable streaming by default for better UX
            stream = True

            # Call the LLM provider with tools and parameters
            if stream:
                # Handle streaming response in real-time with dynamic provider
                await self._execute_streaming_with_provider(
                    provider, messages, tools, temperature, max_tokens, run_id, message.owner_key
                )
            else:
                # Handle non-streaming response
                result = await provider.chat_completion(
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
                owner_key=message.owner_key,
                role=Role.SYSTEM,
                content={
                    "content": f"Error processing LLM request: {str(e)}",
                    "tool_calls": None
                }
            )
            await self.bus.publish(Topics.LLM_RESULTS, error_message)

    def _compose_effective_config(self, user_profile: Dict) -> Dict:
        """
        Compose effective LLM configuration by merging defaults with user overrides.
        
        Args:
            user_profile: User profile containing config_overrides
            
        Returns:
            Dictionary with effective configuration (model, temperature, max_tokens)
        """
        # Get default configuration from ConfigService
        user_defaults = self.config_service.get_user_defaults()
        default_config = user_defaults.get('config', {})
        
        # Get user overrides
        config_overrides = user_profile.get('config_overrides', {})
        
        # Merge (overrides take precedence)
        effective_config = {
            'model': config_overrides.get('model', default_config.get('model', 'gemini-2.5-flash')),
            'temperature': config_overrides.get('temperature', default_config.get('temperature', DEFAULT_TEMPERATURE)),
            'max_tokens': config_overrides.get('max_tokens', default_config.get('max_tokens', DEFAULT_MAX_TOKENS))
        }
        
        logger.info(f"Composed effective config with overrides: {list(config_overrides.keys())}")
        return effective_config

    def _get_provider_for_model(self, model_name: str):
        """
        Dynamically instantiate the appropriate provider for a given model name.
        
        Args:
            model_name: Name of the model to use
            
        Returns:
            Instance of the appropriate LLM provider
            
        Raises:
            ValueError: If provider is not supported
        """
        # Get model catalog from ConfigService
        catalog = self.config_service.get_llm_catalog()
        
        # Check if model exists in catalog
        if model_name not in catalog:
            logger.warning(f"Model '{model_name}' not in catalog, falling back to default")
            # Fallback to default model
            user_defaults = self.config_service.get_user_defaults()
            model_name = user_defaults.get('config', {}).get('model', 'gemini-2.5-flash')
        
        # Get provider name for this model
        provider_name = catalog.get(model_name, {}).get('provider', 'google')
        logger.info(f"Using provider: {provider_name} for model: {model_name}")
        
        # Get provider configuration
        provider_config = self.config_service.get_provider_config(provider_name)
        
        if not provider_config:
            raise ValueError(f"No configuration found for provider: {provider_name}")
        
        # Get timeout from user_defaults config
        user_defaults = self.config_service.get_user_defaults()
        default_config = user_defaults.get('config', {})
        timeout = default_config.get('timeout', DEFAULT_TIMEOUT)
        
        # Instantiate the appropriate provider
        if provider_name == "google":
            return GoogleLLMProvider(
                api_key=provider_config['api_key'],
                base_url=provider_config['base_url'],
                model=catalog.get(model_name, {}).get('id', model_name),
                timeout=timeout
            )
        elif provider_name == "deepseek":
            return DeepSeekLLMProvider(
                api_key=provider_config['api_key'],
                base_url=provider_config['base_url'],
                model=catalog.get(model_name, {}).get('id', model_name),
                timeout=timeout
            )
        elif provider_name == "openrouter":
            return OpenRouterLLMProvider(
                api_key=provider_config['api_key'],
                base_url=provider_config['base_url'],
                model=catalog.get(model_name, {}).get('id', model_name),
                timeout=timeout
            )
        else:
            raise ValueError(f"Unsupported provider: {provider_name}")

    def _resolve_model_name(self, requested: str) -> str:
        """Resolve a friendly model alias to catalog key/provider id.

        Resolution order:
        1) Exact catalog key match -> use as is
        2) Alias match in any catalog entry's 'aliases' list -> use that key
        3) If matches any entry's 'id' (provider id), normalize to that entry's key
        4) Otherwise return as is
        """
        try:
            catalog = self.config_service.get_llm_catalog() or {}
            if requested in catalog:
                return requested

            for key, meta in catalog.items():
                aliases = (meta or {}).get('aliases') or []
                if isinstance(aliases, list) and requested in aliases:
                    return key

            for key, meta in catalog.items():
                provider_id = (meta or {}).get('id') or key
                if requested == provider_id:
                    return key
        except Exception:
            pass
        return requested

    async def _execute_streaming_with_provider(
        self, provider, messages, tools, temperature, max_tokens, run_id, owner_key
    ):
        """
        Execute streaming LLM call with a specific provider instance.
        
        Args:
            provider: LLM provider instance to use
            messages: List of messages for the conversation
            tools: List of available tools
            temperature: Temperature parameter for generation
            max_tokens: Maximum tokens to generate
            run_id: Run identifier
            owner_key: Owner's public key
        """
        # Get streaming response from the provided provider
        response = await self._create_streaming_response_with_provider(
            provider, messages, tools, temperature, max_tokens
        )

        # Process streaming chunks and collect results
        content_chunks, tool_calls = await self._process_streaming_chunks(response, run_id, owner_key)

        # Send final result
        await self._send_final_streaming_result(run_id, owner_key, content_chunks, tool_calls)

    async def _create_streaming_response_with_provider(self, provider, messages, tools, temperature, max_tokens):
        """Create streaming response from a specific LLM provider."""
        # Normalize messages to satisfy provider requirements
        normalized_messages = self._normalize_messages_for_provider(messages)

        return await provider.client.chat.completions.create(
            model=provider.default_model,
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
        - Ensures all non-tool messages have string 'content' (convert None to empty string).
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
                role = msg.get("role")
                if role == "tool":
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
                    # Ensure non-tool message content is a string (providers expect strings)
                    non_tool_msg = dict(msg)
                    content_val = non_tool_msg.get("content")
                    if not isinstance(content_val, str):
                        non_tool_msg["content"] = "" if content_val is None else str(content_val)
                    normalized.append(non_tool_msg)

            return normalized
        except Exception:
            # On any failure, return original messages for safety
            return messages

    async def _process_streaming_chunks(self, response, run_id: str, owner_key: str):
        """Process streaming chunks and publish them in real-time.

        Ensures proper event ordering: all text_chunk events are published first,
        then tool_call_started events are published after all content is streamed.
        """
        content_chunks = []
        # Accumulate tool_calls across streaming deltas by index to avoid truncated JSON
        # Structure: {index: {id, type, function: {name, arguments(str)}}}
        aggregated_tool_calls: dict[int, dict] = {}

        async for chunk in response:
            if not getattr(chunk, "choices", None):
                continue
            delta = chunk.choices[0].delta

            # Handle content chunks - publish immediately for real-time streaming
            if hasattr(delta, 'content') and delta.content:
                content_chunks.append(delta.content)
                await self._publish_text_chunk(run_id, owner_key, delta.content)

            # Collect and accumulate tool call deltas
            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                for tc in delta.tool_calls:
                    # Determine index (primary) for accumulation
                    try:
                        idx = getattr(tc, 'index', None)
                    except Exception:
                        idx = None
                    if idx is None and isinstance(tc, dict):
                        idx = tc.get('index')
                    if idx is None:
                        # Fallback to single-call index 0
                        idx = 0

                    entry = aggregated_tool_calls.get(idx)
                    if entry is None:
                        # Initialize entry
                        tc_id = getattr(tc, 'id', '') if not isinstance(tc, dict) else tc.get('id', '')
                        tc_type = getattr(tc, 'type', 'function') if not isinstance(tc, dict) else tc.get('type', 'function')
                        entry = {
                            "id": tc_id,
                            "type": tc_type or "function",
                            "function": {"name": "", "arguments": ""}
                        }
                        aggregated_tool_calls[idx] = entry

                    # Update id/type if provided later
                    try:
                        if not entry.get("id"):
                            entry["id"] = getattr(tc, 'id', '') if not isinstance(tc, dict) else tc.get('id', '')
                        if not entry.get("type"):
                            entry["type"] = getattr(tc, 'type', 'function') if not isinstance(tc, dict) else tc.get('type', 'function')
                    except Exception:
                        pass

                    # Merge function name and arguments (arguments arrive in parts)
                    fn = getattr(tc, 'function', None) if not isinstance(tc, dict) else tc.get('function', {})
                    if fn is not None:
                        try:
                            name_piece = getattr(fn, 'name', None) if not isinstance(tc, dict) else fn.get('name')
                        except Exception:
                            name_piece = None
                        if name_piece:
                            entry["function"]["name"] = name_piece

                        try:
                            args_piece = getattr(fn, 'arguments', None) if not isinstance(tc, dict) else fn.get('arguments')
                        except Exception:
                            args_piece = None
                        if args_piece is not None:
                            if isinstance(args_piece, str):
                                entry["function"]["arguments"] += args_piece
                            else:
                                try:
                                    import json as _json
                                    entry["function"]["arguments"] += _json.dumps(args_piece, ensure_ascii=False)
                                except Exception:
                                    entry["function"]["arguments"] += str(args_piece)

        # Convert aggregated tool calls to ordered list by index
        aggregated_list = [aggregated_tool_calls[i] for i in sorted(aggregated_tool_calls.keys())] if aggregated_tool_calls else None

        # After all content chunks are streamed, publish tool_call_started events with aggregated calls
        if aggregated_list:
            logger.info(f"All text chunks streamed for run_id={run_id}, now publishing tool_call_started events")
            await self._publish_tool_call_events(run_id, owner_key, aggregated_list)

        return content_chunks, aggregated_list

    async def _publish_text_chunk(self, run_id: str, owner_key: str, chunk: str) -> None:
        """Publish a single text chunk via LLM_RESULTS for Orchestrator forwarding."""
        chunk_event = Message(
            run_id=run_id,
            owner_key=owner_key,
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

    async def _publish_tool_call_events(self, run_id: str, owner_key: str, tool_calls) -> None:
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
                owner_key=owner_key,
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

    async def _send_final_streaming_result(self, run_id: str, owner_key: str, content_chunks: list, tool_calls) -> None:
        """Send the final streaming result with tool calls."""
        full_content = ''.join(content_chunks) if content_chunks else None
        formatted_tool_calls = self._format_tool_calls(tool_calls) if tool_calls else None

        result_message = Message(
            run_id=run_id,
            owner_key=owner_key,
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
        owner_key = original_message.owner_key

        # 1) Stream a few text chunks
        for chunk in ["Thinking...", " Analyzing context...", " Preparing response."]:
            await self._publish_text_chunk(run_id, owner_key, chunk)

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
                owner_key,
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
        await self._send_final_streaming_result(run_id, owner_key, [" Here is a concise summary."], tool_calls)

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
        owner_key = original_message.owner_key

        # Create result message
        result_message = Message(
            run_id=run_id,
            owner_key=owner_key,
            role=Role.AI,
            content={
                "content": result["content"],
                "tool_calls": result["tool_calls"]
            }
        )

        # Publish the result
        await self.bus.publish(Topics.LLM_RESULTS, result_message)
        logger.info(f"Published LLM result for run_id={run_id}")
