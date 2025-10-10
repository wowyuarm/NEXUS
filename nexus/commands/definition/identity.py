"""
Identity command definition for NEXUS.

Provides identity verification through cryptographic signature validation.
Returns the verified public key of the user after successful signature verification,
establishing cryptographic proof of identity ownership.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Command definition
COMMAND_DEFINITION = {
    "name": "identity",
    "description": "Verify your identity and display your public key through cryptographic signature",
    "usage": "/identity",
    "handler": "websocket",
    "requiresSignature": True,  # This command requires cryptographic signature
    "examples": [
        "/identity"
    ]
}


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the identity command.

    Creates or retrieves user identity in the database, establishing the user
    as a registered member with data persistence capabilities.

    Args:
        context: Execution context containing:
            - public_key: The verified public key (injected by signature verification)
            - identity_service: IdentityService instance for identity operations
            - Other service dependencies

    Returns:
        Dict with status, message about identity creation/verification

    Raises:
        RuntimeError: If public_key is not found or identity creation fails
    """
    try:
        # Extract the verified public key from context
        public_key = context.get('public_key')
        
        if not public_key:
            error_msg = "Public key not found in context. This should not happen if signature verification passed."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Get IdentityService from context
        identity_service = context.get('identity_service')
        
        if not identity_service:
            error_msg = "IdentityService not found in context. Identity management unavailable."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.info(f"Identity command executed for public key: {public_key}")
        
        # Get or create identity in database
        identity = await identity_service.get_or_create_identity(public_key)
        
        if not identity:
            error_msg = f"Failed to create or retrieve identity for public_key={public_key}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Check if this was a new identity creation or existing retrieval
        is_new = 'created_at' in identity and identity.get('_just_created', False)
        
        if is_new:
            message = f"✨ 身份已创建！您的主权身份已锚定到 NEXUS 公钥：{public_key[:10]}...{public_key[-8:]}"
            logger.info(f"New identity created for public_key={public_key}")
        else:
            message = f"✅ 身份已验证！欢迎回来，您的 NEXUS 公钥：{public_key[:10]}...{public_key[-8:]}"
            logger.info(f"Existing identity verified for public_key={public_key}")
        
        # Return success with identity information
        result = {
            "status": "success",
            "message": message,
            "data": {
                "public_key": public_key,
                "verified": True,
                "is_new": is_new,
                "created_at": identity.get('created_at')
            }
        }
        
        return result

    except Exception as e:
        error_msg = f"Identity command execution failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

