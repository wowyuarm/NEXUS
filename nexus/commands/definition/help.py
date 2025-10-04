"""
Help command definition for NEXUS.

Provides a help command that lists all available commands and their usage.
This command is essential for users to discover what commands are available
in the system.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Command definition
COMMAND_DEFINITION = {
    "name": "help",
    "description": "Display information about available commands",
    "usage": "/help",
    "handler": "websocket",
    "examples": [
        "/help"
    ]
}


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the help command.

    This command formats and displays information about all available commands
    in the system. It uses the command_definitions provided in the context
    to generate a comprehensive help message.

    Args:
        context: Execution context containing command_definitions

    Returns:
        Dict with status and formatted help message

    Raises:
        RuntimeError: If command execution fails or command_definitions not available
    """
    try:
        logger.info("Help command executed")

        # Get command definitions from context
        command_definitions = context.get('command_definitions', {})

        if not command_definitions:
            logger.warning("No command definitions found in context")
            result = {
                "status": "success",
                "message": "Available commands:\n  No commands found"
            }
            return result

        # Return complete command metadata for frontend consumption
        result = {
            "status": "success",
            "message": "Available commands retrieved successfully",
            "data": {
                "commands": command_definitions
            }
        }

        logger.info("Help command completed successfully")
        return result

    except Exception as e:
        error_msg = f"Help command execution failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)