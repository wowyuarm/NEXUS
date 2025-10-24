"""
Command Service for NEXUS.

Provides a deterministic command processing engine with auto-discovery capabilities.
This service handles command execution, error handling, and result publishing
through the event bus system.

Key features:
- Auto-discovery: Automatically discovers and registers commands from the
  nexus.commands.definition package at initialization
- Command registry: Maintains registry of command executors and metadata
- Cryptographic verification: Supports signature verification for sensitive
  commands (requiresSignature flag) using Ethereum-style ECDSA signatures
- Execution context: Injects services and verified public key into command
  execution context for command access to system resources
- Structured payloads: Supports both legacy string commands ("/ping") and
  structured payloads with auth data ({"command": "/identity", "auth": {...}})
- Error handling: Gracefully handles unknown commands, signature failures,
  and execution errors with informative responses

Command discovery:
Commands are discovered from nexus.commands.definition modules. Each module
should export a COMMAND_DEFINITION dict and an execute() async function.
"""

import logging
import importlib
import pkgutil
from typing import Dict, Any, Callable, Awaitable, Optional

from nexus.core.auth import verify_signature
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Role
from nexus.core.topics import Topics

logger = logging.getLogger(__name__)


class CommandService:
    """
    Command processing engine with auto-discovery and deterministic execution.

    This service is responsible for:
    - Auto-discovering command definitions from the commands/definition directory
    - Registering command handlers for execution
    - Processing command requests through the event bus
    - Publishing command results back to the bus
    - Handling errors gracefully with informative responses
    """

    def __init__(self, bus: NexusBus, **services: Any) -> None:
        """
        Initialize the CommandService with required dependencies.

        Args:
            bus: The NexusBus instance for event communication
            **services: Additional services to inject into command contexts
        """
        self.bus = bus
        self.services = services

        # Registry for command execution functions
        self._command_registry: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {}

        # Registry for command metadata (definitions)
        self._command_definitions: Dict[str, Dict[str, Any]] = {}

        # Auto-discover and register commands
        self._discover_and_register_commands()

        # Subscribe to command requests
        self.bus.subscribe(Topics.SYSTEM_COMMAND, self.handle_command)

        logger.info(f"CommandService initialized with {len(self._command_registry)} commands")

    def _discover_and_register_commands(self) -> None:
        """
        Automatically discover and register commands from the commands definition directory.

        This method scans the nexus.commands.definition package for modules containing
        command definitions and registers them for execution.
        """
        try:
            logger.info("Starting command discovery in nexus.commands.definition")

            package = importlib.import_module('nexus.commands.definition')
            if not hasattr(package, '__path__'):
                logger.warning("nexus.commands.definition has no __path__ attribute")
                return

            # Discover and register commands from each module
            for _, modname, ispkg in pkgutil.iter_modules(package.__path__):
                if not ispkg:  # Skip sub-packages
                    full_module_name = f"nexus.commands.definition.{modname}"
                    self._process_module_for_commands(full_module_name)

            # Also process the root module itself
            try:
                self._process_module_for_commands('nexus.commands.definition')
            except Exception:
                # Don't fail discovery if root processing has issues
                pass

            logger.info(f"Command discovery completed. Registered {len(self._command_registry)} commands")

        except Exception as e:
            logger.error(f"Error during command discovery: {e}")
            raise

    def _process_module_for_commands(self, module_name: str) -> None:
        """
        Process a single module to discover and register commands.

        Args:
            module_name: Full module name to process
        """
        logger.debug(f"Examining command module: {module_name}")

        try:
            module = importlib.import_module(module_name)
            command_definitions = self._extract_command_definitions(module)

            for cmd_def_name, cmd_definition in command_definitions.items():
                self._register_command_from_definition(module, module_name, cmd_def_name, cmd_definition)

        except Exception as e:
            logger.error(f"Error importing command module {module_name}: {e}")

    def _extract_command_definitions(self, module) -> Dict[str, Dict]:
        """
        Extract command definitions from a module.

        Args:
            module: The module to search for command definitions

        Returns:
            Dictionary of command definition name to definition
        """
        command_definitions = {}
        for attr_name in dir(module):
            if attr_name == 'COMMAND_DEFINITION' and not attr_name.startswith('_'):
                attr_value = getattr(module, attr_name)
                if isinstance(attr_value, dict):
                    command_definitions[attr_name] = attr_value
                    logger.debug(f"Found command definition: {attr_name}")
        return command_definitions

    def _register_command_from_definition(self, module, module_name: str, cmd_def_name: str, cmd_definition: Dict) -> None:
        """
        Register a command from its definition and corresponding execute function.

        Args:
            module: The module containing the command
            module_name: Name of the module
            cmd_def_name: Name of the command definition variable
            cmd_definition: The command definition dictionary
        """
        try:
            # Validate command definition structure
            if "name" not in cmd_definition:
                logger.warning(f"Invalid command definition {cmd_def_name}: missing name")
                return

            command_name = cmd_definition["name"]
            handler_type = cmd_definition.get("handler", "server")

            # REST commands don't require execute() function - they are handled by REST API
            # All other command types (server/websocket/client) have execute() functions
            if handler_type == "rest":
                # Register definition only (no executor needed)
                self._command_definitions[command_name] = cmd_definition
                logger.info(f"Registered {handler_type} command: {command_name} from {module_name}")
                return

            # For server/websocket/client commands, execute function is required
            if hasattr(module, "execute"):
                execute_function = getattr(module, "execute")
                if callable(execute_function):
                    # Register both executor and definition
                    self._command_registry[command_name] = execute_function
                    self._command_definitions[command_name] = cmd_definition
                    logger.info(f"Registered command: {command_name} from {module_name}")
                else:
                    logger.warning(f"Found execute function in {module_name} but it's not callable")
            else:
                logger.warning(f"Execute function not found in {module_name} for {handler_type} command")

        except Exception as e:
            logger.error(f"Error processing command definition {cmd_def_name} in {module_name}: {e}")

    async def handle_command(self, message: Message) -> None:
        """
        Handle incoming command requests from the event bus.

        This method parses the command, verifies signature if required, executes it,
        and publishes the result.

        Args:
            message: The command request message
        """
        try:
            logger.info(f"Handling command request: {message.content}")

            # Parse the command (supports both string and structured payload)
            command_str, auth_data = self._parse_command_payload(message.content)
            command_name = self._parse_command_name(command_str)

            # Find the command executor
            executor = self._command_registry.get(command_name)
            if executor is None:
                # Command not found
                result = {
                    "status": "error",
                    "message": f"Unknown command: {command_name}. Type '/help' for available commands."
                }
                await self._publish_result(message, result)
                return

            # Check if command requires signature verification
            command_definition = self._command_definitions.get(command_name, {})
            requires_signature = command_definition.get('requiresSignature', False)

            # Verify signature if required
            verified_public_key: Optional[str] = None
            if requires_signature:
                verification_result = self._verify_signature(command_str, auth_data)
                if verification_result['status'] == 'error':
                    # Signature verification failed
                    await self._publish_result(message, verification_result)
                    return
                verified_public_key = verification_result.get('public_key')

            # Build execution context
            context = self._build_execution_context(command_name, command_str, verified_public_key)

            # Execute the command
            try:
                result = await executor(context)
                await self._publish_result(message, result)
                logger.info(f"Command '{command_name}' executed successfully")

            except Exception as e:
                # Command execution failed
                error_result = {
                    "status": "error",
                    "message": f"Command execution failed: {str(e)}"
                }
                await self._publish_result(message, error_result)
                logger.error(f"Command '{command_name}' execution failed: {e}")

        except Exception as e:
            # General error handling
            error_result = {
                "status": "error",
                "message": f"Command processing error: {str(e)}"
            }
            await self._publish_result(message, error_result)
            logger.error(f"Command processing error: {e}")

    def _parse_command_payload(self, content) -> tuple[str, Optional[Dict[str, Any]]]:
        """
        Parse command payload which can be either a string or a structured object.

        Args:
            content: Either a string command or a dict with command and auth fields

        Returns:
            Tuple of (command_string, auth_data or None)
        """
        # Handle structured payload with auth
        if isinstance(content, dict):
            command_str = content.get('command', '')
            auth_data = content.get('auth')
            return command_str, auth_data
        
        # Handle legacy string payload
        return str(content), None

    def _parse_command_name(self, content: str) -> str:
        """
        Parse the command name from the message content.
        
        For commands with sub-paths (e.g., "/identity/delete"), this returns
        only the base command name (e.g., "identity"). The full command string
        is passed separately in the execution context for internal routing.

        Args:
            content: The raw command string (e.g., "/ping" or "/identity/delete")

        Returns:
            The parsed base command name (e.g., "ping" or "identity")

        Raises:
            ValueError: If command name is empty or invalid
        """
        if not content or not isinstance(content, str):
            raise ValueError("Command content must be a non-empty string")

        # Remove leading slash and whitespace
        command = content.strip().lstrip('/')

        if not command:
            raise ValueError("Command name cannot be empty")

        # For commands with sub-paths (e.g., "identity/delete"), extract only the base command
        # The full command string is passed in context['command'] for internal routing
        base_command = command.split('/')[0]

        return base_command

    def _verify_signature(self, command_str: str, auth_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verify cryptographic signature for a command.

        This method delegates to the shared verify_signature function in nexus.core.auth.
        It verifies that the command was signed by the holder of the private key
        corresponding to the provided public key.

        Args:
            command_str: The command string that was signed
            auth_data: Dictionary containing 'publicKey' and 'signature'

        Returns:
            Dict with either:
                - {'status': 'success', 'public_key': verified_public_key}
                - {'status': 'error', 'message': error_description}
        """
        # Delegate to shared authentication module
        return verify_signature(command_str, auth_data)

    def _build_execution_context(self, command_name: str, command_str: str, public_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Build the execution context for a command.

        Args:
            command_name: Name of the command being executed (parsed, without leading slash)
            command_str: The full original command string (e.g., "/identity/delete")
            public_key: Verified public key (if signature verification was performed)

        Returns:
            Dictionary containing all required context for command execution
        """
        context = {
            'command_name': command_name,
            'command': command_str,  # Pass the full command string for routing within commands
            'command_definitions': self._command_definitions,
            **self.services  # Inject all available services
        }

        # Inject verified public key if available
        if public_key:
            context['public_key'] = public_key

        logger.debug(f"Built execution context for command '{command_name}' (full: '{command_str}')")
        return context

    async def _publish_result(self, original_message: Message, result: Dict[str, Any]) -> None:
        """
        Publish the result of command execution to the event bus.

        Args:
            original_message: The original command request message
            result: The command execution result
        """
        # Create result message
        result_message = Message(
            run_id=original_message.run_id,
            owner_key=original_message.owner_key,
            role=Role.SYSTEM,
            content=result,
            metadata={
                "command": original_message.content,
                "source": "CommandService"
            }
        )

        # Publish to command result topic
        await self.bus.publish(Topics.COMMAND_RESULT, result_message)

        logger.info(f"Published command result for run_id={original_message.run_id}")

    def get_all_command_definitions(self) -> list[Dict[str, Any]]:
        """
        Get all registered command definitions as a list.
        
        This method returns command definitions in list format, suitable for
        JSON serialization and REST API responses. Each definition contains
        metadata including name, handler, description, usage, and examples.

        Returns:
            List of command definition dictionaries
        """
        return list(self._command_definitions.values())

    def is_command_registered(self, command_name: str) -> bool:
        """
        Check if a command is registered.

        Args:
            command_name: Name of the command to check

        Returns:
            True if command is registered, False otherwise
        """
        return command_name in self._command_registry