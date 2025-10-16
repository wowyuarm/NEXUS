"""
Identity command definition for NEXUS.

Provides identity management operations through cryptographic signature validation:
- /identity: Create or verify identity
- /identity/delete: Delete identity from database

All operations require cryptographic signature for security.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Command definition
COMMAND_DEFINITION = {
    "name": "identity",
    "description": "Manage your identity (create, verify, or delete)",
    "usage": "/identity [delete]",
    "handler": "websocket",
    "requiresSignature": True,  # This command requires cryptographic signature
    "requiresGUI": True,  # This command opens a GUI modal panel in the frontend
    "examples": [
        "/identity",
        "/identity/delete"
    ]
}


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the identity command.

    Supports two operations:
    - /identity: Create or verify identity in database
    - /identity/delete: Delete identity from database

    Args:
        context: Execution context containing:
            - command: The full command string (e.g., "/identity" or "/identity/delete")
            - public_key: The verified public key (injected by signature verification)
            - identity_service: IdentityService instance for identity operations

    Returns:
        Dict with status and message about the operation result

    Raises:
        RuntimeError: If operation fails
    """
    try:
        # Extract the verified public key and command from context
        public_key = context.get('public_key')
        command = context.get('command', '/identity')
        
        if not public_key:
            error_msg = "Public key not found in context. Signature verification failed."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Get IdentityService from context
        identity_service = context.get('identity_service')
        
        if not identity_service:
            error_msg = "IdentityService not found in context."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Route to appropriate handler based on command
        if command == '/identity/delete':
            return await _handle_delete_identity(public_key, identity_service)
        else:
            return await _handle_create_or_verify_identity(public_key, identity_service)

    except Exception as e:
        error_msg = f"Identity command execution failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


async def _handle_create_or_verify_identity(public_key: str, identity_service) -> Dict[str, Any]:
    """
    Handle identity creation or verification.
    
    Args:
        public_key: The user's verified public key
        identity_service: IdentityService instance
        
    Returns:
        Dict with status and identity information
    """
    logger.info(f"Creating/verifying identity for public_key={public_key}")
    
    # Get or create identity in database
    identity = await identity_service.get_or_create_identity(public_key)
    
    if not identity:
        error_msg = f"Failed to create or retrieve identity for public_key={public_key}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    # Check if this was a new identity creation or existing retrieval
    is_new = 'created_at' in identity and identity.get('_just_created', False)
    
    if is_new:
        logger.info(f"New identity created for public_key={public_key}")
    else:
        logger.info(f"Existing identity verified for public_key={public_key}")
    
    # Create meaningful message for frontend display
    if is_new:
        message = f"新的主权身份已成功创建！存在地址：{public_key[:10]}...{public_key[-8:]}"
    else:
        message = f"身份已验证！存在地址：{public_key[:10]}...{public_key[-8:]}"
    
    # Return success with identity information
    return {
        "status": "success",
        "message": message,
        "data": {
            "public_key": public_key,
            "verified": True,
            "is_new": is_new,
            "created_at": identity.get('created_at')
        }
    }


async def _handle_delete_identity(public_key: str, identity_service) -> Dict[str, Any]:
    """
    Handle identity deletion from database.
    
    Args:
        public_key: The user's verified public key
        identity_service: IdentityService instance
        
    Returns:
        Dict with status and deletion confirmation
    """
    logger.info(f"Deleting identity for public_key={public_key}")
    
    # Delete identity from database
    success = await identity_service.delete_identity(public_key)
    
    if success:
        logger.info(f"Identity deleted successfully for public_key={public_key}")
        message = f"身份已从NEXUS系统中清除。存在地址：{public_key[:10]}...{public_key[-8:]}"
        return {
            "status": "success",
            "message": message,
            "data": {
                "public_key": public_key,
                "deleted": True
            }
        }
    else:
        # Deletion failed or identity didn't exist
        logger.warning(f"Identity deletion failed or not found for public_key={public_key}")
        message = "⚠️ 未找到身份记录或删除失败"
        return {
            "status": "warning",
            "message": message,
            "data": {
                "public_key": public_key,
                "deleted": False
            }
        }

