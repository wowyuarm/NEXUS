"""
Context service for NEXUS.

Responsible for building conversational context prior to LLM calls. It subscribes
for context build requests and publishes the build outputs when ready.
"""

import logging
import os
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Role
from nexus.core.topics import Topics

logger = logging.getLogger(__name__)


class ContextService:
    def __init__(self, bus: NexusBus):
        self.bus = bus
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

            # Create response message
            response_message = Message(
                run_id=run_id,
                session_id=message.session_id,
                role=Role.SYSTEM,
                content={
                    "status": "success",
                    "messages": messages
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
                    "messages": []
                }
            )
            await self.bus.publish(Topics.CONTEXT_BUILD_RESPONSE, error_message)

    def _load_system_prompt(self) -> str:
        """Load system prompt from prompts/xi/persona.md file."""
        try:
            # Get the path relative to the project root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            persona_path = os.path.join(project_root, "prompts", "xi", "persona.md")

            with open(persona_path, "r", encoding="utf-8") as f:
                content = f.read()

            logger.info(f"Loaded system prompt from {persona_path}")
            return content

        except Exception as e:
            logger.error(f"Error loading system prompt: {e}")
            # Return a fallback system prompt
            return "You are Xi, an AI assistant. Please respond helpfully and thoughtfully."
