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
    "handler": "websocket",
    "examples": [
        "/ping"
    ]
}


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the ping command.

    This command responds with a structured 'pong' message containing
    system information and latency data.

    Args:
        context: Execution context containing system services and state (unused)

    Returns:
        Dict with status, message, and system data

    Raises:
        RuntimeError: If command execution fails
    """
    try:
        import time
        logger.info("Ping command executed")

        # Record start time for latency calculation
        start_time = time.time()

        # Return the enhanced ping-pong response
        result = {
            "status": "success",
            "message": "pong",
            "data": {
                "latency_ms": 1,  # Placeholder for actual latency calculation
                "nexus_version": "0.2.0",
                "timestamp": time.time()
            }
        }

        # Calculate actual latency
        end_time = time.time()
        result["data"]["latency_ms"] = round((end_time - start_time) * 1000, 2)

        logger.info("Ping command completed successfully")
        return result

    except Exception as e:
        error_msg = f"Ping command execution failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)