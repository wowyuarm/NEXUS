"""
Integration tests for CommandService.

These tests verify that CommandService correctly handles event-driven command processing
via NexusBus, including proper command discovery, execution, and result publishing. All external
dependencies are mocked to ensure isolation while testing the service's integration
with the event bus system.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from nexus.services.command import CommandService
from nexus.core.models import Message, Role
from nexus.core.topics import Topics


class TestCommandServiceIntegration:
    """Integration test suite for CommandService event-driven behavior."""

    @pytest.fixture
    def mock_bus(self):
        """Create a mock NexusBus for testing."""
        mock_bus = Mock()
        mock_bus.publish = AsyncMock()
        mock_bus.subscribe = Mock()
        return mock_bus

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock DatabaseService for testing."""
        mock_db = Mock()
        return mock_db

    @pytest.fixture
    def command_service(self, mock_bus, mock_database_service):
        """Create CommandService instance with mocked dependencies."""
        return CommandService(bus=mock_bus, database_service=mock_database_service)

    @pytest.mark.asyncio
    async def test_ping_command_e2e(self, mock_bus, mock_database_service):
        """
        Test that CommandService correctly handles ping command and publishes
        properly formatted result with success status.
        """
        # Arrange: Create input message for ping command
        input_message = Message(
            run_id="test-run-123",
            session_id="test-session-456",
            role=Role.COMMAND,
            content="/ping"
        )

        # Act: Create service and simulate command handling
        service = CommandService(bus=mock_bus, database_service=mock_database_service)
        await service.handle_command(input_message)

        # Assert: Verify result was published to command.result topic
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args

        # Check the topic
        assert call_args[0][0] == Topics.COMMAND_RESULT

        # Check the message structure
        result_message = call_args[0][1]
        assert result_message.role == Role.SYSTEM
        assert result_message.content == {
            "status": "success",
            "message": "pong"
        }
        assert result_message.run_id == "test-run-123"
        assert result_message.session_id == "test-session-456"

    @pytest.mark.asyncio
    async def test_help_command_e2e(self, mock_bus, mock_database_service):
        """
        Test that CommandService correctly handles help command and returns
        formatted list of available commands.
        """
        # Arrange: Create input message for help command
        input_message = Message(
            run_id="test-run-789",
            session_id="test-session-012",
            role=Role.COMMAND,
            content="/help"
        )

        # Act: Create service and simulate command handling
        service = CommandService(bus=mock_bus, database_service=mock_database_service)
        await service.handle_command(input_message)

        # Assert: Verify result was published with command list
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args

        # Check the topic
        assert call_args[0][0] == Topics.COMMAND_RESULT

        # Check the message structure
        result_message = call_args[0][1]
        assert result_message.role == Role.SYSTEM
        assert result_message.content["status"] == "success"
        assert "Available commands:" in result_message.content["message"]
        assert "ping" in result_message.content["message"]
        assert "help" in result_message.content["message"]
        assert result_message.run_id == "test-run-789"
        assert result_message.session_id == "test-session-012"

    @pytest.mark.asyncio
    async def test_invalid_command_handling(self, mock_bus, mock_database_service):
        """
        Test that CommandService properly handles unknown commands with appropriate error response.
        """
        # Arrange: Create input message for unknown command
        input_message = Message(
            run_id="test-run-invalid",
            session_id="test-session-invalid",
            role=Role.COMMAND,
            content="/unknown_command"
        )

        # Act: Create service and simulate command handling
        service = CommandService(bus=mock_bus, database_service=mock_database_service)
        await service.handle_command(input_message)

        # Assert: Verify error response was published
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args

        # Check the topic
        assert call_args[0][0] == Topics.COMMAND_RESULT

        # Check the error response structure
        result_message = call_args[0][1]
        assert result_message.role == Role.SYSTEM
        assert result_message.content["status"] == "error"
        assert "Unknown command" in result_message.content["message"]
        assert "unknown_command" in result_message.content["message"]

    @pytest.mark.asyncio
    async def test_command_service_initialization(self, mock_bus, mock_database_service):
        """
        Test that CommandService initializes correctly and subscribes to system.command topic.
        """
        # Act: Create service instance
        service = CommandService(bus=mock_bus, database_service=mock_database_service)

        # Assert: Verify service subscribed to system.command topic
        mock_bus.subscribe.assert_called_once_with(Topics.SYSTEM_COMMAND, service.handle_command)

        # Verify commands were discovered and registered
        assert len(service._command_registry) > 0
        assert "ping" in service._command_registry
        assert "help" in service._command_registry

    @pytest.mark.asyncio
    async def test_command_error_handling(self, mock_bus, mock_database_service):
        """
        Test that CommandService handles command execution errors gracefully.
        """
        # Arrange: Create a command that will raise an exception
        input_message = Message(
            run_id="test-run-error",
            session_id="test-session-error",
            role=Role.COMMAND,
            content="/ping"
        )

        # Mock the ping command to raise an exception
        with patch.object(CommandService, '_discover_and_register_commands') as mock_discover:
            # Create a broken command registry
            async def broken_execute(context):
                raise RuntimeError("Simulated command execution error")

            service = CommandService(bus=mock_bus, database_service=mock_database_service)
            service._command_registry["ping"] = broken_execute

            # Act: Handle the command
            await service.handle_command(input_message)

            # Assert: Verify error was handled and error response published
            mock_bus.publish.assert_called_once()
            call_args = mock_bus.publish.call_args

            result_message = call_args[0][1]
            assert result_message.content["status"] == "error"
            assert "Command execution failed" in result_message.content["message"]

    @pytest.mark.asyncio
    async def test_command_parsing_edge_cases(self, mock_bus, mock_database_service):
        """
        Test command parsing handles various edge cases correctly.
        """
        test_cases = [
            ("ping", "ping"),  # Without slash
            ("/ping", "ping"),  # With slash
            ("/ping   ", "ping"),  # Trailing spaces
            ("   /ping", "ping"),  # Leading spaces
        ]

        for command_input, expected_command in test_cases:
            # Reset mock
            mock_bus.reset_mock()

            input_message = Message(
                run_id="test-run-parse",
                session_id="test-session-parse",
                role=Role.COMMAND,
                content=command_input
            )

            service = CommandService(bus=mock_bus, database_service=mock_database_service)
            await service.handle_command(input_message)

            # Should succeed for ping command
            if expected_command == "ping":
                mock_bus.publish.assert_called_once()
                result_message = mock_bus.publish.call_args[0][1]
                assert result_message.content["status"] == "success"