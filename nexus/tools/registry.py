"""
Tool registry for NEXUS.

Manages the registration and retrieval of tools available to the system.
Provides a centralized registry for tool definitions and their corresponding
function implementations.
"""

import logging
from typing import Dict, List, Callable, Optional, Any

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for managing tool definitions and their implementations.

    This class maintains a mapping between tool names and their metadata
    (for LLM integration) as well as their actual function implementations
    (for execution).
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        # Store tool metadata (OpenAI/Google format)
        self._tools: Dict[str, Dict[str, Any]] = {}
        # Store actual function implementations
        self._functions: Dict[str, Callable] = {}
        logger.info("ToolRegistry initialized")

    def register(self, tool_definition: Dict[str, Any], tool_function: Callable) -> None:
        """
        Register a tool with its definition and implementation.

        Args:
            tool_definition: Tool metadata in OpenAI/Google format
            tool_function: The actual function implementation

        Raises:
            ValueError: If tool_definition is invalid or tool already exists
        """
        try:
            # Extract tool name from definition
            if "function" not in tool_definition or "name" not in tool_definition["function"]:
                raise ValueError("Invalid tool definition: missing function.name")

            tool_name = tool_definition["function"]["name"]

            # Check if tool already exists
            if tool_name in self._tools:
                logger.warning(f"Tool '{tool_name}' already registered, overwriting")

            # Register the tool
            self._tools[tool_name] = tool_definition
            self._functions[tool_name] = tool_function

            logger.info(f"Tool '{tool_name}' registered successfully")

        except Exception as e:
            error_msg = f"Failed to register tool: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def get_tool_definition(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get tool definition by name.

        Args:
            name: The tool name

        Returns:
            Tool definition dict or None if not found
        """
        definition = self._tools.get(name)
        if definition is None:
            logger.warning(f"Tool definition not found for: {name}")
        return definition

    def get_tool_function(self, name: str) -> Optional[Callable]:
        """
        Get tool function implementation by name.

        Args:
            name: The tool name

        Returns:
            Tool function or None if not found
        """
        function = self._functions.get(name)
        if function is None:
            logger.warning(f"Tool function not found for: {name}")
        return function

    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get all registered tool definitions.

        Returns:
            List of all tool definitions for LLM integration
        """
        definitions = list(self._tools.values())
        logger.debug(f"Returning {len(definitions)} tool definitions")
        return definitions

    def list_tool_names(self) -> List[str]:
        """
        Get names of all registered tools.

        Returns:
            List of tool names
        """
        names = list(self._tools.keys())
        logger.debug(f"Available tools: {names}")
        return names

    def is_tool_registered(self, name: str) -> bool:
        """
        Check if a tool is registered.

        Args:
            name: The tool name

        Returns:
            True if tool is registered, False otherwise
        """
        return name in self._tools

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: The tool name

        Returns:
            True if tool was unregistered, False if not found
        """
        if name not in self._tools:
            logger.warning(f"Cannot unregister tool '{name}': not found")
            return False

        del self._tools[name]
        del self._functions[name]
        logger.info(f"Tool '{name}' unregistered successfully")
        return True