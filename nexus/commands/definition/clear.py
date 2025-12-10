"""
Clear command definition for NEXUS.

Provides a clear command that clears the chat history on the client side.
This command is executed entirely on the frontend without backend communication.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Command definition
COMMAND_DEFINITION = {
    "name": "clear",
    "description": "Clear the chat messages from view (context history preserved)",
    "usage": "/clear",
    "handler": "client",
    "examples": ["/clear"],
}


async def execute(context: dict[str, Any]) -> dict[str, Any]:
    """
    Execute the clear command.

    This command should not be executed on the server side as it's a client-side operation.
    This function exists for completeness but should not be called in practice.

    Args:
        context: Execution context (unused)

    Returns:
        Dict indicating this should be handled client-side

    Raises:
        RuntimeError: Always, as this should be handled client-side
    """
    logger.warning(
        "Clear command executed on server - this should be handled client-side"
    )

    raise RuntimeError(
        "Clear command should be executed on the client side, not on the server. "
        "This indicates a configuration or routing error."
    )
