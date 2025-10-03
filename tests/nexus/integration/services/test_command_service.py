"""
Integration tests for CommandService.

These tests verify that CommandService correctly handles event-driven command processing
via NexusBus, including proper command discovery, execution, and result publishing. All external
dependencies are mocked to ensure isolation while testing the service's integration
with the event bus system.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from eth_keys import keys
from eth_hash.auto import keccak

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
        assert result_message.content["status"] == "success"
        assert result_message.content["message"] == "pong"
        assert "data" in result_message.content
        assert "latency_ms" in result_message.content["data"]
        assert "nexus_version" in result_message.content["data"]
        assert "timestamp" in result_message.content["data"]
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
        assert "data" in result_message.content
        assert "commands" in result_message.content["data"]
        
        # Verify command definitions include execution_target
        commands = result_message.content["data"]["commands"]
        assert "ping" in commands
        assert "help" in commands
        assert "clear" in commands
        
        # Verify execution_target field is present
        assert commands["ping"]["execution_target"] == "server"
        assert commands["help"]["execution_target"] == "server" 
        assert commands["clear"]["execution_target"] == "client"
        
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
        assert "clear" in service._command_registry

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

    @pytest.mark.asyncio
    async def test_signed_command_verification_success(self, mock_bus, mock_database_service):
        """
        Test that CommandService correctly verifies a properly signed command
        and executes the /identity whoami command successfully.
        """
        # Arrange: Generate a test key pair
        private_key_bytes = b'\x01' * 32  # Simple test private key
        private_key = keys.PrivateKey(private_key_bytes)
        public_key_hex = private_key.public_key.to_address()
        
        # Sign the command
        command_str = "/identity"
        # eth_keys expects bytes for signing, so we encode the command
        message_hash = keccak(command_str.encode('utf-8'))
        signature = private_key.sign_msg_hash(message_hash)
        signature_hex = signature.to_hex()
        
        # Create message with auth payload
        input_message = Message(
            run_id="test-run-signed",
            session_id="test-session-signed",
            role=Role.COMMAND,
            content={
                "command": command_str,
                "auth": {
                    "publicKey": public_key_hex,
                    "signature": signature_hex
                }
            }
        )
        
        # Act: Create service and handle the signed command
        service = CommandService(bus=mock_bus, database_service=mock_database_service)
        await service.handle_command(input_message)
        
        # Assert: Verify command was executed successfully
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        
        result_message = call_args[0][1]
        assert result_message.content["status"] == "success"
        assert "Your verified public key is" in result_message.content["message"]
        assert public_key_hex in result_message.content["message"]

    @pytest.mark.asyncio
    async def test_signed_command_verification_failure(self, mock_bus, mock_database_service):
        """
        Test that CommandService rejects commands with invalid signatures
        and returns an authentication failure error.
        """
        # Arrange: Create a command with wrong signature
        command_str = "/identity"
        fake_signature = "0x" + "00" * 65  # Invalid signature
        fake_public_key = "0x" + "00" * 20  # Invalid public key
        
        # Create message with invalid auth payload
        input_message = Message(
            run_id="test-run-invalid-sig",
            session_id="test-session-invalid-sig",
            role=Role.COMMAND,
            content={
                "command": command_str,
                "auth": {
                    "publicKey": fake_public_key,
                    "signature": fake_signature
                }
            }
        )
        
        # Act: Create service and handle the command with invalid signature
        service = CommandService(bus=mock_bus, database_service=mock_database_service)
        await service.handle_command(input_message)
        
        # Assert: Verify authentication failure was returned
        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args
        
        result_message = call_args[0][1]
        assert result_message.content["status"] == "error"
        assert "authentication" in result_message.content["message"].lower() or \
               "signature" in result_message.content["message"].lower() or \
               "verification" in result_message.content["message"].lower()