"""
REST interface for NEXUS.

Provides HTTP REST API endpoints for querying system information,
command definitions, and other stateless operations. Also provides
SSE (Server-Sent Events) endpoints for real-time streaming communication.

Key endpoints:
- GET /commands - List available commands
- POST /chat - Chat with SSE streaming response
- POST /commands/execute - Execute command synchronously
- GET /stream/{public_key} - Persistent SSE stream for connection state
- GET/POST /config - User configuration
- GET/POST /prompts - User prompt overrides
- GET /messages - Message history
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from nexus.core.auth import verify_signature

logger = logging.getLogger(__name__)

# Create the API router for REST endpoints
router = APIRouter()

# Dependency injection placeholders
# These will be overridden in main.py using app.dependency_overrides
_command_service_instance: Any | None = None
_identity_service_instance: Any | None = None
_persistence_service_instance: Any | None = None
_config_service_instance: Any | None = None
_sse_interface_instance: Any | None = None


def get_command_service():
    """
    Dependency injection function for CommandService.

    This function is a placeholder that will be overridden in main.py
    using FastAPI's dependency_overrides mechanism.

    Returns:
        CommandService instance

    Raises:
        HTTPException: If CommandService is not properly injected
    """
    if _command_service_instance is None:
        logger.error("CommandService not injected into REST interface")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable: CommandService not initialized",
        )
    return _command_service_instance


def get_identity_service():
    """Dependency injection for IdentityService."""
    if _identity_service_instance is None:
        logger.error("IdentityService not injected into REST interface")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable: IdentityService not initialized",
        )
    return _identity_service_instance


def get_persistence_service():
    """Dependency injection for PersistenceService."""
    if _persistence_service_instance is None:
        logger.error("PersistenceService not injected into REST interface")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable: PersistenceService not initialized",
        )
    return _persistence_service_instance


def get_config_service():
    """Dependency injection for ConfigService."""
    if _config_service_instance is None:
        logger.error("ConfigService not injected into REST interface")
        raise HTTPException(
            status_code=503, detail="Service unavailable: ConfigService not initialized"
        )
    return _config_service_instance


def get_sse_interface():
    """Dependency injection for SSEInterface."""
    if _sse_interface_instance is None:
        logger.error("SSEInterface not injected into REST interface")
        raise HTTPException(
            status_code=503, detail="Service unavailable: SSEInterface not initialized"
        )
    return _sse_interface_instance


async def verify_bearer_token(authorization: str | None = Header(None)) -> str:
    """
    Verify bearer token from Authorization header.

    Args:
        authorization: Authorization header value (e.g., 'Bearer <owner_key>')

    Returns:
        str: The owner_key extracted from the bearer token

    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
        )

    return parts[1]


async def verify_request_signature(request_body: dict[str, Any], owner_key: str) -> str:
    """
    Verify cryptographic signature for a request body.

    This function validates that the request was signed by the owner_key holder.
    It uses the shared verify_signature function from nexus.core.auth.

    Args:
        request_body: Complete request body (must include 'auth' field)
        owner_key: Owner key extracted from Bearer token

    Returns:
        verified_public_key

    Raises:
        HTTPException 401/403: Signature verification failed
    """
    auth_data = request_body.get("auth")
    if not auth_data:
        raise HTTPException(status_code=401, detail="Missing authentication signature")

    # Construct payload for signature verification
    # Sign the entire request body (excluding auth itself would be circular)
    # Instead, we sign a canonical representation
    payload_for_signing = json.dumps(
        {k: v for k, v in request_body.items() if k != "auth"},
        separators=(",", ":"),
        sort_keys=True,
    )

    # Call shared authentication module
    result = verify_signature(payload_for_signing, auth_data)

    if result["status"] == "error":
        logger.warning(f"Signature verification failed: {result['message']}")
        raise HTTPException(status_code=403, detail=result["message"])

    verified_key = result["public_key"]
    if not isinstance(verified_key, str):
        raise HTTPException(status_code=403, detail="Invalid public key format")

    # Verify that signed public key matches the bearer token
    if verified_key.lower() != owner_key.lower():
        logger.warning(f"Public key mismatch: token={owner_key}, signed={verified_key}")
        raise HTTPException(
            status_code=403,
            detail="Public key mismatch: signature does not match bearer token",
        )

    logger.info(f"Request signature verified for owner_key={owner_key}")
    return verified_key


# Pydantic models for request/response validation
class ConfigUpdateRequest(BaseModel):
    """Request model for updating user configuration."""

    overrides: dict[str, Any]
    auth: dict[str, str]


class PromptsUpdateRequest(BaseModel):
    """Request model for updating user prompts."""

    overrides: dict[str, str]
    auth: dict[str, str]


# Existing /commands endpoint
@router.get("/commands")
async def get_all_commands(
    cmd_svc=Depends(get_command_service),
) -> list[dict[str, Any]]:
    """
    Get all available commands and their metadata.

    This endpoint returns a list of all registered commands with their
    definitions, including name, description, usage, examples, etc.

    Args:
        cmd_svc: CommandService instance (injected)

    Returns:
        List of command definitions

    Example response:
        [
            {
                "name": "help",
                "description": "Show available commands",
                "usage": "/help",
                "handler": "server",
                "examples": ["/help"]
            }
        ]
    """
    try:
        # Get command definitions from CommandService
        commands = cmd_svc.get_all_command_definitions()
        result: list[dict[str, Any]] = commands if isinstance(commands, list) else []
        logger.info(f"Retrieved {len(result)} commands via REST API")
        return result

    except Exception as e:
        logger.error(f"Error retrieving commands: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving commands: {str(e)}"
        ) from e


# Config endpoints
@router.get("/config")
async def get_config(
    owner_key: str = Depends(verify_bearer_token),
    identity_svc=Depends(get_identity_service),
    config_svc=Depends(get_config_service),
) -> dict[str, Any]:
    """
    Get current user's effective configuration and UI metadata.

    Authentication:
        Requires Authorization header: Bearer <owner_key>

    Returns:
        {
            "effective_config": {...},  # Merged configuration
            "effective_prompts": {...}, # Merged prompts
            "user_overrides": {...},    # User's original overrides
            "editable_fields": [...],   # UI editable fields
            "field_options": {...}      # UI field metadata
        }
    """
    try:
        logger.info(f"Getting config for owner_key={owner_key}")
        profile = await identity_svc.get_effective_profile(owner_key, config_svc)
        result: dict[str, Any] = profile if isinstance(profile, dict) else {}
        return result
    except ValueError as e:
        logger.warning(f"Invalid owner_key {owner_key}: {e}")
        raise HTTPException(status_code=401, detail="Invalid owner_key") from e
    except Exception as e:
        logger.error(f"Error retrieving config for {owner_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/config")
async def update_config(
    request: ConfigUpdateRequest,
    owner_key: str = Depends(verify_bearer_token),
    identity_svc=Depends(get_identity_service),
) -> dict[str, Any]:
    """
    Update current user's configuration overrides.

    Authentication:
        - Header: Authorization: Bearer <owner_key>
        - Body must include cryptographic signature

    Request Body:
        {
            "overrides": {"model": "deepseek-chat", "temperature": 0.9},
            "auth": {"publicKey": "0x...", "signature": "0x..."}
        }

    Returns:
        {"status": "success", "message": "Configuration updated"}
    """
    try:
        # Verify signature
        await verify_request_signature(request.model_dump(), owner_key)

        # Update configuration
        logger.info(f"Updating config for owner_key={owner_key}")
        success = await identity_svc.update_user_config(owner_key, request.overrides)

        if success:
            return {
                "status": "success",
                "message": "Configuration updated successfully",
            }
        else:
            raise HTTPException(
                status_code=500, detail="Failed to update configuration"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config for {owner_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# Prompts endpoints
@router.get("/prompts")
async def get_prompts(
    owner_key: str = Depends(verify_bearer_token),
    identity_svc=Depends(get_identity_service),
    config_svc=Depends(get_config_service),
) -> dict[str, Any]:
    """
    Get current user's effective prompts and UI metadata.

    Authentication:
        Requires Authorization header: Bearer <owner_key>

    Returns:
        {
            "effective_prompts": {"friends_profile": "..."},
            "prompt_overrides": {...},
            "editable_fields": [...],
            "field_options": {...}
        }
    """
    try:
        logger.info(f"Getting prompts for owner_key={owner_key}")
        profile = await identity_svc.get_effective_profile(owner_key, config_svc)

        # Return prompts-related parts only
        return {
            "effective_prompts": profile["effective_prompts"],
            "prompt_overrides": profile["user_overrides"]["prompt_overrides"],
            "editable_fields": [
                f for f in profile["editable_fields"] if f.startswith("prompts.")
            ],
            "field_options": {
                k: v
                for k, v in profile["field_options"].items()
                if k.startswith("prompts.")
            },
        }
    except Exception as e:
        logger.error(f"Error retrieving prompts for {owner_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/prompts")
async def update_prompts(
    request: PromptsUpdateRequest,
    owner_key: str = Depends(verify_bearer_token),
    identity_svc=Depends(get_identity_service),
) -> dict[str, Any]:
    """
    Update current user's prompt overrides.

    Authentication:
        - Header: Authorization: Bearer <owner_key>
        - Body must include cryptographic signature

    Request Body:
        {
            "overrides": {"friends_profile": "User preferences and profile..."},
            "auth": {"publicKey": "0x...", "signature": "0x..."}
        }

    Returns:
        {"status": "success", "message": "Prompts updated"}
    """
    try:
        # Verify signature
        await verify_request_signature(request.model_dump(), owner_key)

        # Update prompts
        logger.info(f"Updating prompts for owner_key={owner_key}")
        success = await identity_svc.update_user_prompts(owner_key, request.overrides)

        if success:
            return {"status": "success", "message": "Prompts updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update prompts")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompts for {owner_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# Messages endpoint
@router.get("/messages")
async def get_messages(
    limit: int = Query(
        20, ge=1, le=100, description="Number of messages to retrieve (1-100)"
    ),
    owner_key: str = Depends(verify_bearer_token),
    persistence_svc=Depends(get_persistence_service),
) -> list[dict[str, Any]]:
    """
    Get current user's message history.

    Authentication:
        Requires Authorization header: Bearer <owner_key>

    Query Parameters:
        limit: Maximum number of messages to return (default: 20, range: 1-100)

    Returns:
        List of message dictionaries sorted by timestamp (newest first)
    """
    try:
        logger.info(f"Getting messages for owner_key={owner_key}, limit={limit}")
        messages = await persistence_svc.get_history(owner_key, limit)
        result: list[dict[str, Any]] = messages if isinstance(messages, list) else []
        return result
    except Exception as e:
        logger.error(f"Error retrieving messages for {owner_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# SSE Endpoints for Real-time Communication
# =============================================================================


class ChatRequest(BaseModel):
    """Request model for chat messages."""

    content: str
    client_timestamp_utc: str = ""
    client_timezone_offset: int = 0


class CommandExecuteRequest(BaseModel):
    """Request model for command execution."""

    command: str
    args: list[str] = []
    auth: dict[str, str] | None = None


@router.post("/chat")
async def chat(
    request: ChatRequest,
    owner_key: str = Depends(verify_bearer_token),
    sse_interface=Depends(get_sse_interface),
) -> StreamingResponse:
    """
    Send a chat message and receive streaming response via SSE.

    Authentication:
        Requires Authorization header: Bearer <owner_key>

    Request Body:
        {
            "content": "Hello, how are you?",
            "client_timestamp_utc": "2025-12-11T03:00:00Z",
            "client_timezone_offset": -480
        }

    Returns:
        StreamingResponse with content-type text/event-stream

    SSE Events:
        - run_started: {"owner_key": "...", "user_input": "..."}
        - text_chunk: {"chunk": "...", "is_final": false}
        - tool_call_started: {"tool_name": "...", "args": {...}}
        - tool_call_finished: {"tool_name": "...", "status": "...", "result": "..."}
        - run_finished: {"status": "completed|error"}
        - error: {"message": "..."}
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        run_id = None
        queue = None
        try:
            # Create run and publish to bus
            run_id = await sse_interface.create_run_and_publish(
                owner_key=owner_key,
                user_input=request.content,
                client_timestamp_utc=request.client_timestamp_utc,
                client_timezone_offset=request.client_timezone_offset,
            )

            # Register this stream to receive UI events
            queue = sse_interface.register_chat_stream(run_id)

            logger.info(f"SSE: Started chat stream for run_id={run_id}")

            # Stream events until run completes
            while True:
                try:
                    # Wait for events with timeout for keepalive
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # Event is the UI event dict from orchestrator
                    event_type = event.get("event", "message")
                    yield sse_interface.format_sse_event(event_type, event)

                    # Check if this is a terminal event
                    if event_type in ("run_finished", "error"):
                        logger.info(f"SSE: Chat stream ended for run_id={run_id}")
                        break

                except TimeoutError:
                    # Send keepalive comment
                    yield sse_interface.format_sse_keepalive()

        except Exception as e:
            logger.error(f"SSE: Error in chat stream: {e}")
            error_event = {"event": "error", "payload": {"message": str(e)}}
            yield sse_interface.format_sse_event("error", error_event)

        finally:
            # Cleanup
            if run_id:
                sse_interface.unregister_chat_stream(run_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )


@router.post("/commands/execute")
async def execute_command(
    request: CommandExecuteRequest,
    owner_key: str = Depends(verify_bearer_token),
    cmd_svc=Depends(get_command_service),
    identity_svc=Depends(get_identity_service),
) -> dict[str, Any]:
    """
    Execute a system command synchronously.

    This endpoint executes commands that don't require streaming responses.
    For commands requiring signature verification, include the auth field.

    Authentication:
        Requires Authorization header: Bearer <owner_key>

    Request Body:
        {
            "command": "/ping",
            "args": [],
            "auth": {"publicKey": "0x...", "signature": "0x..."} // optional
        }

    Returns:
        {
            "status": "success" | "error",
            "message": "...",
            "data": {...}  // optional
        }
    """
    try:
        command_str = request.command.strip()
        if not command_str.startswith("/"):
            command_str = "/" + command_str

        logger.info(
            f"Executing command '{command_str}' for owner_key={owner_key[:10]}..."
        )

        # Parse command name
        command_name = command_str.lstrip("/").split("/")[0].split()[0]

        # Get command definition to check if signature is required
        command_definitions = cmd_svc.get_all_command_definitions()
        command_def = next(
            (c for c in command_definitions if c.get("name") == command_name), None
        )

        if command_def is None:
            return {
                "status": "error",
                "message": f"Unknown command: {command_name}. Type '/help' for available commands.",
            }

        # Check if command requires signature
        requires_signature = command_def.get("requiresSignature", False)

        verified_public_key: str | None = None
        if requires_signature:
            if not request.auth:
                return {
                    "status": "error",
                    "message": f"Command '{command_name}' requires signature verification.",
                }
            # Verify signature
            result = verify_signature(command_str, request.auth)
            if result["status"] == "error":
                return result
            verified_public_key = result.get("public_key")

        # Build execution context
        context = {
            "command_name": command_name,
            "command": command_str,
            "command_definitions": {c["name"]: c for c in command_definitions},
            "database_service": cmd_svc.services.get("database_service"),
            "identity_service": identity_svc,
        }
        if verified_public_key:
            context["public_key"] = verified_public_key

        # Get executor and execute
        executor = cmd_svc._command_registry.get(command_name)
        if executor is None:
            # Check if it's a REST-only command
            if command_def.get("handler") == "rest":
                return {
                    "status": "error",
                    "message": f"Command '{command_name}' should be accessed via its dedicated REST endpoint.",
                }
            return {
                "status": "error",
                "message": f"No executor found for command: {command_name}",
            }

        result = await executor(context)
        return result if isinstance(result, dict) else {"status": "success", "data": result}

    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return {"status": "error", "message": f"Command execution failed: {str(e)}"}


@router.get("/stream/{public_key}")
async def event_stream(
    public_key: str,
    identity_svc=Depends(get_identity_service),
    sse_interface=Depends(get_sse_interface),
) -> StreamingResponse:
    """
    Persistent SSE stream for connection state and proactive events.

    This endpoint establishes a long-lived SSE connection that:
    1. Immediately sends a connection_state event with visitor status
    2. Keeps the connection alive with periodic keepalive comments
    3. Can receive proactive events (command results, etc.)

    Path Parameters:
        public_key: The user's public key (used for identity lookup)

    Returns:
        StreamingResponse with content-type text/event-stream

    SSE Events:
        - connection_state: {"visitor": true|false} (first event)
        - command_result: {"command": "...", "result": {...}}
        - keepalive: (comment, not an event)
    """

    async def stream_generator() -> AsyncGenerator[str, None]:
        queue = None
        try:
            # Check visitor status
            identity = await identity_svc.get_identity(public_key)
            is_visitor = identity is None

            # Send connection_state as first event
            connection_state = {"visitor": is_visitor}
            yield sse_interface.format_sse_event("connection_state", connection_state)

            logger.info(
                f"SSE: Persistent stream started for public_key={public_key[:10]}... (visitor={is_visitor})"
            )

            # Register persistent stream
            queue = sse_interface.register_persistent_stream(public_key)

            # Keep connection alive
            while True:
                try:
                    # Wait for events with timeout for keepalive
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)

                    event_type = event.get("event", "message")
                    yield sse_interface.format_sse_event(event_type, event)

                except TimeoutError:
                    # Send keepalive comment
                    yield sse_interface.format_sse_keepalive()

        except asyncio.CancelledError:
            logger.info(
                f"SSE: Persistent stream cancelled for public_key={public_key[:10]}..."
            )
            raise

        except Exception as e:
            logger.error(f"SSE: Error in persistent stream: {e}")
            error_event = {"event": "error", "payload": {"message": str(e)}}
            yield sse_interface.format_sse_event("error", error_event)

        finally:
            # Cleanup
            if queue:
                sse_interface.unregister_persistent_stream(public_key)

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
