"""
Unit tests for REST interface.

Tests the REST API endpoints for NEXUS, verifying proper separation
from WebSocket interface and correct handling of command queries.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock
from nexus.interfaces import rest


class TestRestInterface:
    """Test suite for REST API endpoints."""

    def test_commands_endpoint_exists(self):
        """
        Test: Verify that /commands endpoint returns all registered commands.

        This test verifies the REST interface properly exposes command metadata
        including all required fields with correct handler values.
        """
        # Create a mock CommandService with all four commands
        mock_command_service = Mock()
        mock_command_service.get_all_command_definitions.return_value = [
            {
                "name": "ping",
                "description": "Test system connectivity by responding with 'pong'",
                "usage": "/ping",
                "handler": "server",
                "examples": ["/ping"],
            },
            {
                "name": "help",
                "description": "Display information about available commands",
                "usage": "/help",
                "handler": "server",
                "examples": ["/help"],
            },
            {
                "name": "clear",
                "description": "Clear the chat messages from view (context history preserved)",
                "usage": "/clear",
                "handler": "client",
                "examples": ["/clear"],
            },
            {
                "name": "identity",
                "description": "Identity verification - returns your verified public key",
                "usage": "/identity",
                "handler": "server",
                "requires_signature": True,
                "examples": ["/identity"],
            },
        ]

        # Create a FastAPI app and include the REST router
        app = FastAPI()
        app.include_router(rest.router, prefix="/api/v1")

        # Override the dependency injection
        app.dependency_overrides[rest.get_command_service] = (
            lambda: mock_command_service
        )

        # Create test client
        client = TestClient(app)

        # Make request to commands endpoint
        response = client.get("/api/v1/commands")

        # Assert successful response
        assert response.status_code == 200
        commands = response.json()
        assert isinstance(commands, list)

        # Assert response is not empty
        assert len(commands) == 4, f"Expected 4 commands, got {len(commands)}"

        # Extract command names
        command_names = [cmd["name"] for cmd in commands]

        # Assert contains all expected commands
        assert "ping" in command_names, "Response should include ping command"
        assert "help" in command_names, "Response should include help command"
        assert "clear" in command_names, "Response should include clear command"
        assert "identity" in command_names, "Response should include identity command"

        # Assert each command has correct handler field
        commands_by_name = {cmd["name"]: cmd for cmd in commands}
        assert commands_by_name["ping"]["handler"] == "server"
        assert commands_by_name["help"]["handler"] == "server"
        assert commands_by_name["clear"]["handler"] == "client"
        assert commands_by_name["identity"]["handler"] == "server"

        # Assert each command has required fields
        for cmd in commands:
            assert "name" in cmd, f"Command missing 'name': {cmd}"
            assert (
                "description" in cmd
            ), f"Command {cmd.get('name')} missing 'description'"
            assert "usage" in cmd, f"Command {cmd.get('name')} missing 'usage'"
            assert "handler" in cmd, f"Command {cmd.get('name')} missing 'handler'"
            assert "examples" in cmd, f"Command {cmd.get('name')} missing 'examples'"

        # Verify get_all_command_definitions was called
        mock_command_service.get_all_command_definitions.assert_called_once()
