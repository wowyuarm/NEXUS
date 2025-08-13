"""
LLM service for NEXUS.

This service handles LLM requests by coordinating with pluggable LLM providers.
It subscribes to LLM request topics on the NexusBus and publishes results.
"""

import logging
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Role
from nexus.core.topics import Topics
from nexus.services.config import ConfigService
from .providers.google import GoogleLLMProvider

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, bus: NexusBus, config_service: ConfigService):
        self.bus = bus
        self.config_service = config_service

        # Initialize the LLM provider based on configuration
        self.provider = self._initialize_provider()
        logger.info("LLMService initialized with provider")

    def _initialize_provider(self):
        """Initialize the LLM provider based on configuration."""
        provider_name = self.config_service.get("llm.provider", "google")

        if provider_name == "google":
            api_key = self.config_service.get("llm.providers.google.api_key")
            base_url = self.config_service.get("llm.providers.google.base_url")
            model = self.config_service.get("llm.providers.google.model", "gemini-2.5-flash")

            if not api_key:
                raise ValueError("Google API key not found in configuration")
            if not base_url:
                raise ValueError("Google base URL not found in configuration")

            return GoogleLLMProvider(api_key=api_key, base_url=base_url, model=model)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")

    def subscribe_to_bus(self) -> None:
        """Subscribe to LLM request topics."""
        self.bus.subscribe(Topics.LLM_REQUESTS, self.handle_llm_request)
        logger.info("LLMService subscribed to NexusBus")

    async def handle_llm_request(self, message: Message) -> None:
        """
        Handle LLM completion requests.

        Args:
            message: Message containing 'messages' list, 'tools' list and 'run_id'
        """
        try:
            logger.info(f"Handling LLM request for run_id={message.run_id}")

            # Extract messages, tools and run_id from the message content
            content = message.content
            messages = content.get("messages", [])
            tools = content.get("tools", [])
            run_id = message.run_id

            if not messages:
                logger.error(f"No messages found in LLM request for run_id={run_id}")
                return

            # Call the LLM provider with tools
            result = await self.provider.chat_completion(messages, tools=tools)

            # Create result message
            result_message = Message(
                run_id=run_id,
                session_id=message.session_id,
                role=Role.AI,
                content={
                    "content": result["content"],
                    "tool_calls": result["tool_calls"]
                }
            )

            # Publish the result
            await self.bus.publish(Topics.LLM_RESULTS, result_message)
            logger.info(f"Published LLM result for run_id={run_id}")

        except Exception as e:
            logger.error(f"Error handling LLM request for run_id={message.run_id}: {e}")
            # Publish error result
            error_message = Message(
                run_id=message.run_id,
                session_id=message.session_id,
                role=Role.SYSTEM,
                content={
                    "content": f"Error processing LLM request: {str(e)}",
                    "tool_calls": None
                }
            )
            await self.bus.publish(Topics.LLM_RESULTS, error_message)
