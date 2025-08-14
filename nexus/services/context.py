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


class ContextService:
    def __init__(self, bus: NexusBus, tool_registry: ToolRegistry):
        self.bus = bus
        self.tool_registry = tool_registry
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

            # Create simplified messages list
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": current_input
                }
            ]

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
