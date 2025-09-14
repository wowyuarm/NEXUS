"""
Tool Executor service for NEXUS.

Responsible for executing registered tools upon request messages received via
NexusBus. Handles tool execution asynchronously and publishes results back
to the bus.
"""

import asyncio
import logging
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Role
from nexus.core.topics import Topics
from nexus.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Constants for tool execution status
TOOL_STATUS_SUCCESS = "success"
TOOL_STATUS_ERROR = "error"
TOOL_STATUS_UNKNOWN = "unknown"


class ToolExecutorService:
    """
    Service responsible for executing tools based on requests from the NexusBus.

    This service listens for tool execution requests, dispatches them to the
    appropriate tool functions via the ToolRegistry, and publishes results
    back to the bus.
    """

    def __init__(self, bus: NexusBus, tool_registry: ToolRegistry) -> None:
        """
        Initialize the ToolExecutorService.

        Args:
            bus: The NexusBus instance for communication
            tool_registry: Registry containing available tools
        """
        self.bus = bus
        self.tool_registry = tool_registry
        logger.info("ToolExecutorService initialized")

    def subscribe_to_bus(self) -> None:
        """Subscribe to tool request topics on the NexusBus."""
        self.bus.subscribe(Topics.TOOLS_REQUESTS, self.handle_tool_request)
        logger.info("ToolExecutorService subscribed to NexusBus")

    def _create_tool_result_message(
        self,
        run_id: str,
        session_id: str,
        result: str,
        status: str,
        tool_name: str,
        call_id: str = ""
    ) -> Message:
        """
        Create a standardized tool result message.

        Args:
            run_id: The run identifier
            session_id: The session identifier
            result: The tool execution result or error message
            status: The execution status (success/error)
            tool_name: The name of the executed tool

        Returns:
            A Message object containing the tool result
        """
        return Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.TOOL,
            content={
                "result": result,
                "status": status,
                "tool_name": tool_name,
                "call_id": call_id
            }
        )

    async def handle_tool_request(self, message: Message) -> None:
        """
        Handle tool execution requests.

        Args:
            message: Message containing tool request with name and args
        """
        run_id = message.run_id
        session_id = message.session_id
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

            logger.info(f"Executing tool '{tool_name}' with args: {tool_args} for run_id={run_id}")

            # Ensure tool_args is a dictionary
            if not isinstance(tool_args, dict):
                logger.error(f"Tool args must be a dictionary, got {type(tool_args)}: {tool_args}")
                raise ValueError(f"Tool args must be a dictionary, got {type(tool_args)}")

            # Get tool function from registry
            tool_function = self.tool_registry.get_tool_function(tool_name)
            if tool_function is None:
                raise ValueError(f"Tool '{tool_name}' not found in registry")

            # Execute tool function asynchronously using asyncio.to_thread
            # This allows synchronous tool functions to run without blocking the event loop
            result = await asyncio.to_thread(tool_function, **tool_args)

            # Create and publish success result
            result_message = self._create_tool_result_message(
                run_id=run_id,
                session_id=session_id,
                result=result,
                status=TOOL_STATUS_SUCCESS,
                tool_name=tool_name,
                call_id=call_id
            )
            await self.bus.publish(Topics.TOOLS_RESULTS, result_message)
            logger.info(f"Tool '{tool_name}' executed successfully for run_id={run_id}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Tool execution failed for run_id={run_id}, tool='{tool_name}': {error_msg}")

            # Create and publish error result
            error_message = self._create_tool_result_message(
                run_id=run_id,
                session_id=session_id,
                result=error_msg,
                status=TOOL_STATUS_ERROR,
                tool_name=tool_name or TOOL_STATUS_UNKNOWN,
                call_id=call_id
            )
            await self.bus.publish(Topics.TOOLS_RESULTS, error_message)
