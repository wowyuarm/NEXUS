"""
Tool registry for NEXUS.

Manages the registration and retrieval of tools available to the system.
Provides a centralized registry for tool definitions and their corresponding
function implementations. Features automatic tool discovery and registration
from specified module paths.
"""

import logging
import importlib
import pkgutil
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

    def discover_and_register(self, discovery_path: str) -> None:
        """
        Automatically discover and register tools from a given module path.

        Args:
            discovery_path: Module path to search for tools (e.g., 'nexus.tools.definition')
        """
        try:
            logger.info(f"Starting tool discovery in path: {discovery_path}")

            package = importlib.import_module(discovery_path)
            if not hasattr(package, '__path__'):
                logger.warning(f"Package {discovery_path} has no __path__ attribute")
                return

            # Discover and register tools from each module
            for _, modname, ispkg in pkgutil.iter_modules(package.__path__):
                if not ispkg:  # Skip sub-packages
                    full_module_name = f"{discovery_path}.{modname}"
                    self._process_module_for_tools(full_module_name)

            logger.info(f"Tool discovery completed. Total registered tools: {len(self._tools)}")

        except Exception as e:
            logger.error(f"Error during tool discovery in {discovery_path}: {e}")
            raise

    def _process_module_for_tools(self, module_name: str) -> None:
        """Process a single module to discover and register tools."""
        logger.debug(f"Examining module: {module_name}")

        try:
            module = importlib.import_module(module_name)
            tool_definitions = self._extract_tool_definitions(module)

            for tool_def_name, tool_definition in tool_definitions.items():
                self._register_tool_from_definition(module, module_name, tool_def_name, tool_definition)

        except Exception as e:
            logger.error(f"Error importing module {module_name}: {e}")

    def _extract_tool_definitions(self, module) -> Dict[str, Dict]:
        """Extract tool definitions from a module."""
        tool_definitions = {}
        for attr_name in dir(module):
            if attr_name.endswith('_TOOL') and not attr_name.startswith('_'):
                attr_value = getattr(module, attr_name)
                if isinstance(attr_value, dict):
                    tool_definitions[attr_name] = attr_value
                    logger.debug(f"Found tool definition: {attr_name}")
        return tool_definitions

    def _register_tool_from_definition(self, module, module_name: str, tool_def_name: str, tool_definition: Dict) -> None:
        """Register a tool from its definition and corresponding function."""
        try:
            # Validate tool definition structure
            if "function" not in tool_definition or "name" not in tool_definition["function"]:
                logger.warning(f"Invalid tool definition {tool_def_name}: missing function.name")
                return

            function_name = tool_definition["function"]["name"]

            # Find and validate the function
            if hasattr(module, function_name):
                tool_function = getattr(module, function_name)
                if callable(tool_function):
                    self.register(tool_definition, tool_function)
                    logger.info(f"Auto-registered tool: {function_name} from {module_name}")
                else:
                    logger.warning(f"Found {function_name} in {module_name} but it's not callable")
            else:
                logger.warning(f"Tool function {function_name} not found in {module_name}")

        except Exception as e:
            logger.error(f"Error processing tool definition {tool_def_name} in {module_name}: {e}")