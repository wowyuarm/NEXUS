"""
Ping command definition for NEXUS.

Provides a simple ping command that responds with 'pong' to test system connectivity.
This command is useful for debugging and testing the command execution system.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Command definition
COMMAND_DEFINITION = {
    "name": "ping",
    "description": "Test system connectivity by responding with 'pong'",
    "usage": "/ping",
    "examples": [
        "/ping"
    ]
}


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the ping command.

    This command responds with a simple 'pong' message to indicate that the
    command processing system is functioning correctly.

    Args:
        context: Execution context containing system services and state (unused)

    Returns:
        Dict with status and message indicating successful execution

    Raises:
        RuntimeError: If command execution fails
    """
    try:
        logger.info("Ping command executed")

        # Return the classic ping-pong response
        result = {
            "status": "success",
            "message": "pong"
        }

        logger.info("Ping command completed successfully")
        return result

    except Exception as e:
        error_msg = f"Ping command execution failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)