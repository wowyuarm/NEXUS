"""
Unit tests for ToolRegistry.

These tests verify that ToolRegistry correctly handles tool registration,
discovery, and management functionality. All external dependencies are mocked
to ensure isolation.
"""

from unittest.mock import Mock, patch

import pytest

from nexus.tools.registry import ToolRegistry


class TestToolRegistry:
    """Test suite for ToolRegistry class."""

    def test_initialization(self):
        """Test that ToolRegistry initializes with empty containers."""
        registry = ToolRegistry()

        assert registry._tools == {}
        assert registry._functions == {}

    def test_register_success(self):
        """Test successful tool registration."""
        registry = ToolRegistry()

        # Mock tool definition and function
        tool_definition = {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "A test tool",
                "parameters": {
                    "type": "object",
                    "properties": {"param1": {"type": "string"}},
                    "required": ["param1"],
                },
            },
        }

        def test_function(param1: str) -> str:
            return f"Processed: {param1}"

        registry.register(tool_definition, test_function)

        # Verify tool was registered
        assert "test_tool" in registry._tools
        assert "test_tool" in registry._functions
        assert registry._tools["test_tool"] == tool_definition
        assert registry._functions["test_tool"] == test_function

    def test_register_overwrites_existing_tool(self):
        """Test that registering an existing tool overwrites it."""
        registry = ToolRegistry()

        # First tool definition
        tool_definition1 = {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "First version",
                "parameters": {"type": "object", "properties": {}},
            },
        }

        def test_function1():
            return "First version"

        # Second tool definition
        tool_definition2 = {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "Second version",
                "parameters": {"type": "object", "properties": {}},
            },
        }

        def test_function2():
            return "Second version"

        registry.register(tool_definition1, test_function1)
        registry.register(tool_definition2, test_function2)

        # Verify tool was overwritten
        assert registry._tools["test_tool"] == tool_definition2
        assert registry._functions["test_tool"] == test_function2

    def test_register_invalid_tool_definition(self):
        """Test that registering invalid tool definition raises ValueError."""
        registry = ToolRegistry()

        # Invalid tool definition (missing function.name)
        invalid_definition = {
            "type": "function",
            "function": {
                "description": "Invalid tool"
                # Missing "name" field
            },
        }

        def test_function():
            return "test"

        with pytest.raises(
            ValueError, match="Invalid tool definition: missing function.name"
        ):
            registry.register(invalid_definition, test_function)

    def test_get_tool_definition_found(self):
        """Test getting an existing tool definition."""
        registry = ToolRegistry()

        tool_definition = {
            "type": "function",
            "function": {"name": "test_tool", "description": "Test tool"},
        }

        def test_function():
            return "test"

        registry.register(tool_definition, test_function)

        result = registry.get_tool_definition("test_tool")
        assert result == tool_definition

    def test_get_tool_definition_not_found(self):
        """Test getting a non-existent tool definition."""
        registry = ToolRegistry()

        result = registry.get_tool_definition("nonexistent_tool")
        assert result is None

    def test_get_tool_function_found(self):
        """Test getting an existing tool function."""
        registry = ToolRegistry()

        tool_definition = {
            "type": "function",
            "function": {"name": "test_tool", "description": "Test tool"},
        }

        def test_function():
            return "test"

        registry.register(tool_definition, test_function)

        result = registry.get_tool_function("test_tool")
        assert result == test_function

    def test_get_tool_function_not_found(self):
        """Test getting a non-existent tool function."""
        registry = ToolRegistry()

        result = registry.get_tool_function("nonexistent_tool")
        assert result is None

    def test_get_all_tool_definitions(self):
        """Test getting all registered tool definitions."""
        registry = ToolRegistry()

        tool_definition1 = {
            "type": "function",
            "function": {"name": "tool1", "description": "Tool 1"},
        }

        tool_definition2 = {
            "type": "function",
            "function": {"name": "tool2", "description": "Tool 2"},
        }

        def function1():
            return "function1"

        def function2():
            return "function2"

        registry.register(tool_definition1, function1)
        registry.register(tool_definition2, function2)

        result = registry.get_all_tool_definitions()

        assert len(result) == 2
        assert tool_definition1 in result
        assert tool_definition2 in result

    def test_list_tool_names(self):
        """Test listing all registered tool names."""
        registry = ToolRegistry()

        tool_definition1 = {
            "type": "function",
            "function": {"name": "tool1", "description": "Tool 1"},
        }

        tool_definition2 = {
            "type": "function",
            "function": {"name": "tool2", "description": "Tool 2"},
        }

        def function1():
            return "function1"

        def function2():
            return "function2"

        registry.register(tool_definition1, function1)
        registry.register(tool_definition2, function2)

        result = registry.list_tool_names()

        assert len(result) == 2
        assert "tool1" in result
        assert "tool2" in result

    def test_is_tool_registered(self):
        """Test checking if a tool is registered."""
        registry = ToolRegistry()

        tool_definition = {
            "type": "function",
            "function": {"name": "test_tool", "description": "Test tool"},
        }

        def test_function():
            return "test"

        # Before registration
        assert not registry.is_tool_registered("test_tool")

        # After registration
        registry.register(tool_definition, test_function)
        assert registry.is_tool_registered("test_tool")

    def test_unregister_success(self):
        """Test successful tool unregistration."""
        registry = ToolRegistry()

        tool_definition = {
            "type": "function",
            "function": {"name": "test_tool", "description": "Test tool"},
        }

        def test_function():
            return "test"

        registry.register(tool_definition, test_function)

        # Verify tool is registered
        assert registry.is_tool_registered("test_tool")

        # Unregister the tool
        result = registry.unregister("test_tool")

        assert result is True
        assert not registry.is_tool_registered("test_tool")
        assert "test_tool" not in registry._tools
        assert "test_tool" not in registry._functions

    def test_unregister_nonexistent_tool(self):
        """Test unregistering a non-existent tool."""
        registry = ToolRegistry()

        result = registry.unregister("nonexistent_tool")
        assert result is False

    def test_discover_and_register_success(self, mocker):
        """Test successful tool discovery and registration."""
        # Mock package and module discovery
        mock_package = Mock()
        mock_package.__path__ = ["/test/path"]

        # Create a simple object to act as a module
        class MockModule:
            def __init__(self):
                self.DISCOVERED_TOOL = {
                    "type": "function",
                    "function": {
                        "name": "discovered_tool",
                        "description": "Auto-discovered tool",
                    },
                }
                self.discovered_tool = Mock(return_value="discovered result")
                self.__dict__ = {
                    "DISCOVERED_TOOL": self.DISCOVERED_TOOL,
                    "discovered_tool": self.discovered_tool,
                }

        mock_module = MockModule()

        # Mock importlib.import_module and pkgutil.iter_modules
        mock_import_module = mocker.patch("importlib.import_module")
        mock_iter_modules = mocker.patch("pkgutil.iter_modules")

        # First call returns the package, second call returns the module
        mock_import_module.side_effect = [mock_package, mock_module]
        mock_iter_modules.return_value = [(None, "test_module", False)]  # Not a package

        registry = ToolRegistry()
        registry.discover_and_register("nexus.tools.definition")

        # Verify tool was discovered and registered
        assert registry.is_tool_registered("discovered_tool")

    def test_discover_and_register_handles_import_error(self, mocker):
        """Test that tool discovery handles import errors gracefully."""
        # Mock package discovery
        mock_package = Mock()
        mock_package.__path__ = ["/test/path"]

        # Mock importlib.import_module and pkgutil.iter_modules
        mock_import_module = mocker.patch("importlib.import_module")
        mock_iter_modules = mocker.patch("pkgutil.iter_modules")

        mock_import_module.return_value = mock_package
        mock_iter_modules.return_value = [(None, "problem_module", False)]

        # Mock module import to raise ImportError
        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("Module not found")

            registry = ToolRegistry()

            # Should not raise an exception
            registry.discover_and_register("nexus.tools.definition")

        # Registry should still be empty due to import error
        assert len(registry.get_all_tool_definitions()) == 0

    def test_discover_and_register_ignores_module_without_tool(self, mocker):
        """Test that tool discovery ignores modules without tool definitions."""
        # Mock package discovery
        mock_package = Mock()
        mock_package.__path__ = ["/test/path"]

        # Mock module without tool definitions
        mock_module = Mock()
        # No _TOOL attributes

        # Mock importlib.import_module and pkgutil.iter_modules
        mock_import_module = mocker.patch("importlib.import_module")
        mock_iter_modules = mocker.patch("pkgutil.iter_modules")

        mock_import_module.return_value = mock_package
        mock_iter_modules.return_value = [(None, "empty_module", False)]

        with patch("importlib.import_module") as mock_import:
            mock_import.return_value = mock_module

            registry = ToolRegistry()
            registry.discover_and_register("nexus.tools.definition")

        # Registry should be empty (no tools discovered)
        assert len(registry.get_all_tool_definitions()) == 0

    def test_manual_register_and_get_workflow(self):
        """Test complete manual registration and retrieval workflow."""
        registry = ToolRegistry()

        # Define multiple tools
        tools_data = [
            {
                "definition": {
                    "type": "function",
                    "function": {
                        "name": "calculator",
                        "description": "Perform calculations",
                    },
                },
                "function": lambda x, y: x + y,
            },
            {
                "definition": {
                    "type": "function",
                    "function": {
                        "name": "text_processor",
                        "description": "Process text",
                    },
                },
                "function": lambda text: text.upper(),
            },
        ]

        # Register all tools
        for tool_data in tools_data:
            registry.register(tool_data["definition"], tool_data["function"])

        # Verify all tools are registered
        assert len(registry.get_all_tool_definitions()) == 2
        assert "calculator" in registry.list_tool_names()
        assert "text_processor" in registry.list_tool_names()

        # Test individual retrieval
        calc_def = registry.get_tool_definition("calculator")
        calc_func = registry.get_tool_function("calculator")

        assert calc_def is not None
        assert calc_def["function"]["name"] == "calculator"
        assert calc_func is not None
        assert calc_func(2, 3) == 5

        # Test tool function execution
        text_def = registry.get_tool_definition("text_processor")
        text_func = registry.get_tool_function("text_processor")

        assert text_def is not None
        assert text_def["function"]["name"] == "text_processor"
        assert text_func is not None
        assert text_func("hello") == "HELLO"

    def test_register_tool_from_definition_missing_function(self, mocker):
        """Test registration when function is missing from module."""
        registry = ToolRegistry()

        # Mock module without the corresponding function
        mock_module = Mock()

        tool_definition = {
            "type": "function",
            "function": {
                "name": "missing_function",
                "description": "Tool with missing function",
            },
        }

        # Mock hasattr to return False for the function
        mocker.patch.object(registry, "register")
        mocker.patch("builtins.hasattr", return_value=False)

        # Should not raise an exception, but should log a warning
        registry._register_tool_from_definition(
            mock_module, "test_module", "TEST_TOOL", tool_definition
        )

        # Verify register was not called
        registry.register.assert_not_called()

    def test_register_tool_from_definition_non_callable_function(self, mocker):
        """Test registration when function exists but is not callable."""
        registry = ToolRegistry()

        # Mock module with non-callable function
        mock_module = Mock()
        mock_module.missing_function = "not a function"  # String instead of function

        tool_definition = {
            "type": "function",
            "function": {
                "name": "missing_function",
                "description": "Tool with non-callable function",
            },
        }

        # Mock hasattr to return True, but the attribute is not callable
        mocker.patch.object(registry, "register")

        with patch("builtins.hasattr", return_value=True):
            registry._register_tool_from_definition(
                mock_module, "test_module", "TEST_TOOL", tool_definition
            )

        # Verify register was not called
        registry.register.assert_not_called()
