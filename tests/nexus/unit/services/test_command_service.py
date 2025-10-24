"""
Unit tests for CommandService.

These tests verify the core functionality of CommandService methods in isolation,
without requiring event bus integration or external dependencies.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from nexus.services.command import CommandService


class TestCommandServiceUnit:
    """Unit test suite for CommandService methods."""

    @pytest.fixture
    def mock_bus(self):
        """Create a mock NexusBus for testing."""
        mock_bus = Mock()
        mock_bus.publish = AsyncMock()
        mock_bus.subscribe = Mock()
        return mock_bus

    @pytest.fixture
    def command_service(self, mock_bus):
        """Create CommandService instance with mocked dependencies."""
        return CommandService(bus=mock_bus)

    def test_get_all_command_definitions_returns_list(self, command_service):
        """
        Test that get_all_command_definitions() returns a list.
        
        This ensures the method returns the correct data structure for JSON serialization.
        """
        result = command_service.get_all_command_definitions()
        
        assert isinstance(result, list), "get_all_command_definitions should return a list"

    def test_get_all_command_definitions_contains_all_commands(self, command_service):
        """
        Test that get_all_command_definitions() includes all registered commands.
        
        After auto-discovery, the service should return definitions for:
        ping, help, clear, identity, theme, config, prompt, and history commands.
        """
        result = command_service.get_all_command_definitions()
        command_names = [cmd["name"] for cmd in result]
        
        # Assert all expected commands are present
        assert "ping" in command_names, "ping command should be discovered"
        assert "help" in command_names, "help command should be discovered"
        assert "clear" in command_names, "clear command should be discovered"
        assert "identity" in command_names, "identity command should be discovered"
        assert "theme" in command_names, "theme command should be discovered"
        assert "config" in command_names, "config command should be discovered"
        assert "prompt" in command_names, "prompt command should be discovered"
        assert "history" in command_names, "history command should be discovered"
        
        # Assert we have exactly 8 commands
        assert len(result) == 8, f"Expected 8 commands, got {len(result)}"

    def test_get_all_command_definitions_with_correct_metadata(self, command_service):
        """
        Test that each command definition contains required metadata fields.
        
        Each command must have: name, handler, description, usage, and examples.
        """
        result = command_service.get_all_command_definitions()
        
        # Verify each command has required fields
        for cmd in result:
            assert "name" in cmd, f"Command missing 'name' field: {cmd}"
            assert "handler" in cmd, f"Command {cmd.get('name')} missing 'handler' field"
            assert "description" in cmd, f"Command {cmd.get('name')} missing 'description' field"
            assert "usage" in cmd, f"Command {cmd.get('name')} missing 'usage' field"
            assert "examples" in cmd, f"Command {cmd.get('name')} missing 'examples' field"
            
            # Verify handler has valid value
            assert cmd["handler"] in ["websocket", "client", "rest"], \
                f"Command {cmd['name']} has invalid handler: {cmd['handler']}"

    def test_get_all_command_definitions_handler_field_values(self, command_service):
        """
        Test that specific commands have correct handler field values.
        
        - ping, identity: handler = "websocket"
        - help, clear: handler = "client"
        """
        result = command_service.get_all_command_definitions()
        commands_by_name = {cmd["name"]: cmd for cmd in result}
        
        # WebSocket commands
        assert commands_by_name["ping"]["handler"] == "websocket", \
            "ping command should have handler='websocket'"
        assert commands_by_name["identity"]["handler"] == "websocket", \
            "identity command should have handler='websocket'"
        
        # Client-side commands
        assert commands_by_name["help"]["handler"] == "client", \
            "help command should have handler='client' (client-side rendering)"
        assert commands_by_name["clear"]["handler"] == "client", \
            "clear command should have handler='client'"
        assert commands_by_name["theme"]["handler"] == "client", \
            "theme command should have handler='client'"

    def test_command_discovery_loads_clear_command(self, command_service):
        """
        Test that the command discovery mechanism successfully loads clear.py.
        
        This verifies that clear.py is properly structured with COMMAND_DEFINITION
        and execute function, and is discovered during initialization.
        """
        # Check that clear is in the command registry
        assert "clear" in command_service._command_registry, \
            "clear command should be registered"
        
        # Check that clear is in the command definitions
        assert "clear" in command_service._command_definitions, \
            "clear command definition should be registered"
        
        # Verify clear has correct handler
        clear_def = command_service._command_definitions["clear"]
        assert clear_def["handler"] == "client", \
            "clear command should have handler='client'"

    def test_identity_command_has_requires_signature_field(self, command_service):
        """
        Test that identity command has requiresSignature field set to True.
        
        This field is critical for signature verification in authenticated commands.
        """
        result = command_service.get_all_command_definitions()
        commands_by_name = {cmd["name"]: cmd for cmd in result}
        
        identity_cmd = commands_by_name["identity"]
        assert "requiresSignature" in identity_cmd, \
            "identity command should have requiresSignature field"
        assert identity_cmd["requiresSignature"] is True, \
            "identity command should require signature"

