"""
Test tool definition for NEXUS.

Provides a debugging test tool that randomly succeeds or fails with 50% probability.
This tool is designed for testing the tool execution system and debugging purposes.
"""

import logging
import random
import time
from typing import Any

logger = logging.getLogger(__name__)

# Constants
SUCCESS_PROBABILITY = 0.5
MIN_EXECUTION_TIME = 0.5  # Minimum execution time in seconds
MAX_EXECUTION_TIME = 2.0  # Maximum execution time in seconds


def test_tool(message: str = "Hello from test tool!") -> str:
    """
    A test tool that randomly succeeds or fails with 50% probability.

    This tool is designed for debugging and testing the tool execution system.
    It simulates realistic execution time and provides detailed feedback about
    its execution status.

    Args:
        message: A custom message to include in the response (default: "Hello from test tool!")

    Returns:
        str: A formatted response indicating success or failure

    Raises:
        RuntimeError: When the tool randomly fails (50% probability)
    """
    try:
        logger.info(f"Test tool started with message: '{message}'")

        # Simulate realistic execution time
        execution_time = random.uniform(MIN_EXECUTION_TIME, MAX_EXECUTION_TIME)
        time.sleep(execution_time)

        # Generate random success/failure with 50% probability
        success = random.random() < SUCCESS_PROBABILITY

        if success:
            result = (
                f"✅ Test tool executed successfully!\n"
                f"Message: {message}\n"
                f"Execution time: {execution_time:.2f}s\n"
                f"Status: SUCCESS\n"
                f"Random value: {random.random():.4f}"
            )

            logger.info(f"Test tool completed successfully in {execution_time:.2f}s")
            return result
        else:
            error_msg = (
                f"Test tool failed randomly (50% probability)\n"
                f"Message: {message}\n"
                f"Execution time: {execution_time:.2f}s\n"
                f"Status: FAILED"
            )

            logger.warning(f"Test tool failed randomly after {execution_time:.2f}s")
            raise RuntimeError(error_msg)

    except Exception as e:
        logger.error(f"Test tool execution error: {str(e)}")
        raise


# Tool definition in OpenAI/Google format for LLM integration
TEST_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "test_tool",
        "description": "A debugging test tool that randomly succeeds or fails with 50% probability. Useful for testing the tool execution system and debugging tool-related issues. Simulates realistic execution time and provides detailed feedback.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "A custom message to include in the test response",
                    "default": "Hello from test tool!",
                }
            },
            "required": [],
        },
    },
}
