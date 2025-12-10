"""
REST interface for NEXUS.

Provides HTTP REST API endpoints for querying system information,
command definitions, and other stateless operations. This interface
is separate from the WebSocket interface which handles real-time
communication and stateful sessions.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
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
