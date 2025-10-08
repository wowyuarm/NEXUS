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

    This command returns the verified public key of the user after successful
    signature verification. The public key is injected into the context by
    the CommandService's signature verification logic.

    Args:
        context: Execution context containing:
            - public_key: The verified public key (injected by signature verification)
            - command_name: Name of the command being executed
            - Other service dependencies

    Returns:
        Dict with status, message containing the verified public key

    Raises:
        RuntimeError: If public_key is not found in context (signature verification failed)
    """
    try:
        # Extract the verified public key from context
        public_key = context.get('public_key')
        
        if not public_key:
            error_msg = "Public key not found in context. This should not happen if signature verification passed."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.info(f"Identity command executed for public key: {public_key}")
        
        # Return success with verified public key
        result = {
            "status": "success",
            "message": f"Your verified public key is: {public_key}",
            "data": {
                "public_key": public_key,
                "verified": True
            }
        }
        
        return result

    except Exception as e:
        error_msg = f"Identity command execution failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

