"""
Common utilities for OpenAI-compatible LLM providers.

This module centralizes repetitive logic across provider implementations:
- Building chat.completions request parameters
- Parsing non-streaming responses
- Parsing streaming responses
- Normalizing tool_calls structures
"""

from typing import Any, Dict, List, Optional


def build_chat_api_params(
    *,
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: int,
    stream: bool,
    tools: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build parameters for OpenAI-compatible chat.completions.create.

    Excludes optional fields (like tools) when empty to avoid provider quirks.
    """
    params: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    if tools:
        params["tools"] = tools
    return params


def _format_single_tool_call(tool_call: Any) -> Dict[str, Any]:
    """Normalize a single tool_call to a plain dict structure."""
    # Object-like tool_call with attributes (provider SDK types)
    if hasattr(tool_call, "id") and hasattr(tool_call, "type") and hasattr(tool_call, "function"):
        function_obj = getattr(tool_call, "function")
        name = getattr(function_obj, "name", "unknown")
        arguments = getattr(function_obj, "arguments", {})
        return {
            "id": getattr(tool_call, "id", ""),
            "type": getattr(tool_call, "type", "function"),
            "function": {
                "name": name,
                "arguments": arguments,
            },
        }

    # Dict-like tool_call already in expected structure
    if isinstance(tool_call, dict):
        fn = tool_call.get("function", {})
        return {
            "id": tool_call.get("id", ""),
            "type": tool_call.get("type", "function"),
            "function": {
                "name": fn.get("name", "unknown"),
                "arguments": fn.get("arguments", {}),
            },
        }

    # Fallback best-effort normalization
    return {
        "id": "",
        "type": "function",
        "function": {"name": "unknown", "arguments": str(tool_call)},
    }


def format_tool_calls(tool_calls: Any) -> Optional[List[Dict[str, Any]]]:
    """Normalize provider-specific tool_calls to a uniform list of dicts.

    Returns None when no tool calls are present.
    """
    if not tool_calls:
        return None

    try:
        return [_format_single_tool_call(tc) for tc in tool_calls]
    except Exception:
        # Be defensive; if iteration fails, try single object formatting
        try:
            return [_format_single_tool_call(tool_calls)]
        except Exception:
            return None


async def handle_non_streaming_response(response: Any) -> Dict[str, Any]:
    """Parse a non-streaming OpenAI-compatible response into a simple dict."""
    message = response.choices[0].message if getattr(response, "choices", None) else None
    content = getattr(message, "content", None) if message is not None else None
    tool_calls = getattr(message, "tool_calls", None) if message is not None else None
    formatted_tool_calls = format_tool_calls(tool_calls)
    return {"content": content, "tool_calls": formatted_tool_calls}


async def handle_streaming_response(response: Any) -> Dict[str, Any]:
    """Parse a streaming OpenAI-compatible response into chunks and final values."""
    content_chunks: List[str] = []
    tool_calls = None

    async for chunk in response:
        choices = getattr(chunk, "choices", None)
        if not choices:
            continue
        delta = choices[0].delta

        # Collect content chunks
        if hasattr(delta, "content") and delta.content:
            content_chunks.append(delta.content)

        # Capture tool calls (typically provided in last chunk)
        if hasattr(delta, "tool_calls") and delta.tool_calls:
            tool_calls = delta.tool_calls

    full_content = "".join(content_chunks) if content_chunks else None
    formatted_tool_calls = format_tool_calls(tool_calls)
    return {"content": full_content, "tool_calls": formatted_tool_calls, "content_chunks": content_chunks}


