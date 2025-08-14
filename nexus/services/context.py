"""
Context service for NEXUS.

Responsible for building conversational context prior to LLM calls. It subscribes
for context build requests and publishes the build outputs when ready.

Enhanced with tool registry integration to provide available tool definitions
to the LLM alongside the conversational context. Features intelligent system
prompt construction by combining persona and tool descriptions.
"""

import logging
import os
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Role
from nexus.core.topics import Topics
from nexus.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Constants
PROMPTS_SUBDIR = "prompts/xi"
PERSONA_FILENAME = "persona.md"
TOOLS_FILENAME = "tools.md"
CONTENT_SEPARATOR = "\n\n---\n\n"
FALLBACK_SYSTEM_PROMPT = "You are Xi, an AI assistant. Please respond helpfully and thoughtfully."

# Conversation history and role mapping constants
DEFAULT_HISTORY_LIMIT = 20  # Default number of recent messages to include in context
CONFIG_HISTORY_SIZE_KEY = "memory.history_context_size"
NEXUS_ROLE_HUMAN = "human"
NEXUS_ROLE_AI = "ai"
NEXUS_ROLE_TOOL = "tool"
LLM_ROLE_USER = "user"
LLM_ROLE_ASSISTANT = "assistant"
LLM_ROLE_SYSTEM = "system"


class ContextService:
    def __init__(self, bus: NexusBus, tool_registry: ToolRegistry, config_service=None, persistence_service=None):
        self.bus = bus
        self.tool_registry = tool_registry
        self.config_service = config_service
        self.persistence_service = persistence_service
        logger.info("ContextService initialized")

    def subscribe_to_bus(self) -> None:
        """Subscribe to context build request topics."""
        self.bus.subscribe(Topics.CONTEXT_BUILD_REQUEST, self.handle_build_request)
        logger.info("ContextService subscribed to NexusBus")

    async def handle_build_request(self, message: Message) -> None:
        """
        Handle context build requests.

        Args:
            message: Message containing 'current_input' and 'run_id'
        """
        try:
            logger.info(f"Handling context build request for run_id={message.run_id}")

            # Extract current input from message content
            content = message.content
            current_input = content.get("current_input", "")
            run_id = message.run_id

            if not current_input:
                logger.error(f"No current_input found in context request for run_id={run_id}")
                return

            # Load system prompt from persona.md
            system_prompt = self._load_system_prompt()

            # Build messages list with history
            messages = await self._build_messages_with_history(
                message.session_id,
                system_prompt,
                current_input
            )

            # Get all available tool definitions
            tools = self.tool_registry.get_all_tool_definitions()

            # Create response message
            response_message = Message(
                run_id=run_id,
                session_id=message.session_id,
                role=Role.SYSTEM,
                content={
                    "status": "success",
                    "messages": messages,
                    "tools": tools
                }
            )

            # Publish the context build response
            await self.bus.publish(Topics.CONTEXT_BUILD_RESPONSE, response_message)
            logger.info(f"Published context build response for run_id={run_id}")

        except Exception as e:
            logger.error(f"Error handling context build request for run_id={message.run_id}: {e}")
            # Publish error response
            error_message = Message(
                run_id=message.run_id,
                session_id=message.session_id,
                role=Role.SYSTEM,
                content={
                    "status": "error",
                    "messages": [],
                    "tools": []
                }
            )
            await self.bus.publish(Topics.CONTEXT_BUILD_RESPONSE, error_message)

    def _load_system_prompt(self) -> str:
        """Load system prompt from prompts/xi/persona.md and tools.md files."""
        try:
            # Get the prompts directory path
            current_dir = os.path.dirname(os.path.abspath(__file__))
            nexus_dir = os.path.dirname(current_dir)
            prompts_dir = os.path.join(nexus_dir, PROMPTS_SUBDIR)

            # Load prompt files
            persona_content = self._load_prompt_file(prompts_dir, PERSONA_FILENAME, FALLBACK_SYSTEM_PROMPT)
            tools_content = self._load_prompt_file(prompts_dir, TOOLS_FILENAME, "")

            # Combine content with separator
            if tools_content:
                combined_content = f"{persona_content}{CONTENT_SEPARATOR}{tools_content}"
            else:
                combined_content = persona_content

            logger.info("System prompt constructed successfully")
            return combined_content

        except Exception as e:
            logger.error(f"Error loading system prompt: {e}")
            return FALLBACK_SYSTEM_PROMPT

    def _load_prompt_file(self, prompts_dir: str, filename: str, fallback: str) -> str:
        """Load a single prompt file with error handling."""
        file_path = os.path.join(prompts_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info(f"Loaded {filename} content from {file_path}")
            return content
        except Exception as e:
            logger.warning(f"Error loading {filename}: {e}")
            return fallback

    async def _build_messages_with_history(self, session_id: str, system_prompt: str, current_input: str) -> list:
        """Build messages list with conversation history from database.

        Args:
            session_id: The session ID to load history for
            system_prompt: The system prompt to include
            current_input: The current user input

        Returns:
            List of message dictionaries for LLM context
        """
        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        # Load recent conversation history if persistence service is available
        # This provides short-term memory by including recent messages in the context
        if self.persistence_service:
            try:
                # Get history context size from config
                history_limit = DEFAULT_HISTORY_LIMIT
                if self.config_service:
                    history_limit = self.config_service.get_int(CONFIG_HISTORY_SIZE_KEY, DEFAULT_HISTORY_LIMIT)

                # Retrieve historical messages
                history_messages = await self.persistence_service.get_history(session_id, history_limit)

                # Convert database messages to LLM format and add to context
                for msg_data in reversed(history_messages):  # Reverse to get chronological order
                    role = msg_data.get("role", "").lower()
                    content = msg_data.get("content", "")

                    # Map NEXUS roles to LLM roles
                    if role == NEXUS_ROLE_HUMAN:
                        llm_role = LLM_ROLE_USER
                    elif role == NEXUS_ROLE_AI:
                        llm_role = LLM_ROLE_ASSISTANT
                    elif role == NEXUS_ROLE_TOOL:
                        # Tool results can be included as system messages or skipped
                        # For now, we'll include them as system messages with context
                        tool_name = msg_data.get("metadata", {}).get("tool_name", "unknown")
                        llm_role = LLM_ROLE_SYSTEM
                        content = f"Tool '{tool_name}' result: {content}"
                    else:
                        continue  # Skip unknown roles

                    # Handle None content and only add non-empty messages
                    if content and str(content).strip():
                        messages.append({
                            "role": llm_role,
                            "content": str(content)
                        })

                logger.info(f"Added {len(history_messages)} historical messages to context for session {session_id}")

            except Exception as e:
                logger.error(f"Failed to load conversation history for session {session_id}: {e}")
                # Continue without history if loading fails

        # Add the current user input
        messages.append({
            "role": "user",
            "content": current_input
        })

        return messages
