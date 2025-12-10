"""
Tool Executor service for NEXUS.

Responsible for executing registered tools upon request messages received via
NexusBus. Handles tool execution asynchronously and publishes results back
to the bus.

Key features:
- Async tool execution: Uses asyncio.to_thread to run synchronous tool functions
  without blocking the event loop
- Timeout control: Configurable execution timeout (system.tool_execution_timeout)
  to prevent hanging tools
- Error handling: Comprehensive error handling with detailed error messages
- Result standardization: Publishes standardized result messages with status
  (success/error/timeout) and result payload
- Tool registry integration: Dynamically retrieves tool functions from ToolRegistry
- Argument validation: Ensures tool arguments are properly formatted as dictionaries

Tool execution flow:
TOOLS_REQUESTS → validate request → get tool from registry → execute with timeout →
publish result to TOOLS_RESULTS → OrchestratorService handles result
"""

import asyncio
import logging

from nexus.core.bus import NexusBus
from nexus.core.models import Message, Role
from nexus.core.topics import Topics
from nexus.services.config import ConfigService
from nexus.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Constants for tool execution status
TOOL_STATUS_SUCCESS = "success"
TOOL_STATUS_ERROR = "error"
TOOL_STATUS_UNKNOWN = "unknown"
TOOL_STATUS_TIMEOUT = "timeout"

# Default timeout for tool execution (in seconds)
DEFAULT_TOOL_TIMEOUT = 20


class ToolExecutorService:
    """
    Service responsible for executing tools based on requests from the NexusBus.

    This service listens for tool execution requests, dispatches them to the
    appropriate tool functions via the ToolRegistry, and publishes results
    back to the bus.

    Features:
    - Asynchronous tool execution with timeout control
    - Comprehensive error handling and reporting
    - Configurable timeout duration
    """

    def __init__(
        self,
        bus: NexusBus,
        tool_registry: ToolRegistry,
        config_service: ConfigService | None = None,
    ) -> None:
        """
        Initialize the ToolExecutorService.

        Args:
            bus: The NexusBus instance for communication
            tool_registry: Registry containing available tools
            config_service: Optional ConfigService for reading timeout configuration
        """
        self.bus = bus
        self.tool_registry = tool_registry
        self.config_service = config_service

        # Get tool execution timeout from config, or use default
        self.tool_timeout = DEFAULT_TOOL_TIMEOUT
        if config_service:
            self.tool_timeout = config_service.get_int(
                "system.tool_execution_timeout", DEFAULT_TOOL_TIMEOUT
            )

        logger.info(
            f"ToolExecutorService initialized with timeout={self.tool_timeout}s"
        )

    def subscribe_to_bus(self) -> None:
        """Subscribe to tool request topics on the NexusBus."""
        self.bus.subscribe(Topics.TOOLS_REQUESTS, self.handle_tool_request)
        logger.info("ToolExecutorService subscribed to NexusBus")

    def _create_tool_result_message(
        self,
        run_id: str,
        owner_key: str,
        result: str,
        status: str,
        tool_name: str,
        call_id: str = "",
    ) -> Message:
        """
        Create a standardized tool result message.

        Args:
            run_id: The run identifier
            owner_key: The owner's public key (user identity)
            result: The tool execution result or error message
            status: The execution status (success/error)
            tool_name: The name of the executed tool

        Returns:
            A Message object containing the tool result
        """
        return Message(
            run_id=run_id,
            owner_key=owner_key,
            role=Role.TOOL,
            content={
                "result": result,
                "status": status,
                "tool_name": tool_name,
                "call_id": call_id,
            },
        )

    async def handle_tool_request(self, message: Message) -> None:
        """
        Handle tool execution requests.

        Args:
            message: Message containing tool request with name and args
        """
        run_id = message.run_id
        owner_key = message.owner_key
        tool_name = None
        call_id = ""

        try:
            logger.info(f"Handling tool request for run_id={run_id}")

            # Parse tool request from message content
            content = message.content
            if not isinstance(content, dict):
                raise ValueError("Tool request content must be a dictionary")

            tool_name = content.get("name")
            tool_args = content.get("args", {})
            call_id = content.get("call_id", "")

            if not tool_name:
                raise ValueError("Tool request missing 'name' field")

            logger.info(
                f"Executing tool '{tool_name}' with args: {tool_args} for run_id={run_id}"
            )

            # Ensure tool_args is a dictionary
            if not isinstance(tool_args, dict):
                logger.error(
                    f"Tool args must be a dictionary, got {type(tool_args)}: {tool_args}"
                )
                raise ValueError(
                    f"Tool args must be a dictionary, got {type(tool_args)}"
                )

            # Get tool function from registry
            tool_function = self.tool_registry.get_tool_function(tool_name)
            if tool_function is None:
                raise ValueError(f"Tool '{tool_name}' not found in registry")

            # Execute tool function with timeout
            # Handle both sync and async tool functions
            try:
                if asyncio.iscoroutinefunction(tool_function):
                    # For async functions, call directly
                    result = await asyncio.wait_for(
                        tool_function(**tool_args), timeout=self.tool_timeout
                    )
                else:
                    # For sync functions, use asyncio.to_thread to avoid blocking
                    result = await asyncio.wait_for(
                        asyncio.to_thread(tool_function, **tool_args),
                        timeout=self.tool_timeout,
                    )
            except TimeoutError:
                # Handle timeout specifically
                timeout_msg = (
                    f"Tool '{tool_name}' execution timed out after {self.tool_timeout}s"
                )
                logger.error(f"{timeout_msg} for run_id={run_id}")

                # Create and publish timeout error result
                timeout_message = self._create_tool_result_message(
                    run_id=run_id,
                    owner_key=owner_key,
                    result=timeout_msg,
                    status=TOOL_STATUS_TIMEOUT,
                    tool_name=tool_name,
                    call_id=call_id,
                )
                await self.bus.publish(Topics.TOOLS_RESULTS, timeout_message)
                return

            # Create and publish success result
            result_message = self._create_tool_result_message(
                run_id=run_id,
                owner_key=owner_key,
                result=result,
                status=TOOL_STATUS_SUCCESS,
                tool_name=tool_name,
                call_id=call_id,
            )
            await self.bus.publish(Topics.TOOLS_RESULTS, result_message)
            logger.info(f"Tool '{tool_name}' executed successfully for run_id={run_id}")

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Tool execution failed for run_id={run_id}, tool='{tool_name}': {error_msg}"
            )

            # Create and publish error result
            error_message = self._create_tool_result_message(
                run_id=run_id,
                owner_key=owner_key,
                result=error_msg,
                status=TOOL_STATUS_ERROR,
                tool_name=tool_name or TOOL_STATUS_UNKNOWN,
                call_id=call_id,
            )
            await self.bus.publish(Topics.TOOLS_RESULTS, error_message)
