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
from typing import List, Dict
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Role
from nexus.core.topics import Topics
from nexus.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Constants
PROMPTS_SUBDIR = "prompts/xi"
PERSONA_FILENAME = "persona.md"
TOOLS_FILENAME = "tools.md"
SYSTEM_FILENAME = "system.md"
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
LLM_ROLE_TOOL = "tool"


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
            message: Message containing 'current_input', 'client_timestamp_utc', 'client_timezone_offset', and 'run_id'
        """
        try:
            logger.info(f"Handling context build request for run_id={message.run_id}")

            # Extract current input and client timestamp from message content
            content = message.content
            current_input = content.get("current_input", "")
            client_timestamp_utc = content.get("client_timestamp_utc", "")
            client_timezone_offset = content.get("client_timezone_offset", 0)
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
                current_input,
                client_timestamp_utc,
                client_timezone_offset
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
            system_content = self._load_prompt_file(prompts_dir, SYSTEM_FILENAME, "")
            tools_content = self._load_prompt_file(prompts_dir, TOOLS_FILENAME, "")

            # Combine content with separator
            parts = []
            if persona_content:
                parts.append(persona_content)
            if system_content:
                parts.append(system_content)
            if tools_content:
                parts.append(tools_content)

            combined_content = CONTENT_SEPARATOR.join(parts) if parts else FALLBACK_SYSTEM_PROMPT

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

    def _format_llm_messages(
        self,
        system_prompt: str,
        history_from_db: List[Dict],
        current_input: str,
        client_timestamp_utc: str = "",
        client_timezone_offset: int = 0
    ) -> List[Dict]:
        """Format LLM messages using the new context revolution paradigm.

        This method implements the "thinking loop invariance" principle by keeping
        the system prompt and history messages immutable, while injecting dynamic
        context information in a structured XML format.

        Args:
            system_prompt: The system prompt to include (immutable)
            history_from_db: List of historical message dictionaries from database (immutable)
            current_input: The current user input
            client_timestamp: The client timestamp in ISO 8601 format

        Returns:
            List of message dictionaries formatted for LLM context
        """
        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        # Convert database messages to LLM format and add to context
        # This preserves the "thinking loop invariance" - history is immutable
        for msg_data in reversed(history_from_db):  # Reverse to get chronological order
            role = msg_data.get("role", "").lower()
            content = msg_data.get("content", "")

            # Map NEXUS roles to LLM roles
            if role == NEXUS_ROLE_HUMAN:
                llm_role = LLM_ROLE_USER
            elif role == NEXUS_ROLE_AI:
                llm_role = LLM_ROLE_ASSISTANT
            elif role == NEXUS_ROLE_TOOL:
                # IMPORTANT: Skip persisted tool messages in initial LLM context because
                # they often lack the required tool_call_id linkage to an assistant message
                # within the same request, which violates the OpenAI-compatible schema and
                # can cause INVALID_ARGUMENT (400). The agentic loop will add proper tool
                # messages during the same run when needed.
                continue
            else:
                continue  # Skip unknown roles

            # Handle None content and only add non-empty messages
            if content is None:
                content_str = ""
            else:
                content_str = str(content)
            if content_str.strip():
                messages.append({
                    "role": llm_role,
                    "content": content_str
                })

        # Build structured XML context for dynamic information
        # This implements the "structured contextual input" principle
        xml_context_parts = ["<Context>"]

        # Add current time if timestamp is available
        if client_timestamp_utc:
            # Use timezone-aware calculation when both UTC and offset are provided
            try:
                from datetime import datetime, timedelta

                # Parse ISO 8601 UTC timestamp
                utc_dt = datetime.fromisoformat(client_timestamp_utc.replace('Z', '+00:00'))

                # Apply timezone offset (negative because getTimezoneOffset() returns minutes west of UTC)
                offset_td = timedelta(minutes=-client_timezone_offset)
                local_dt = utc_dt + offset_td

                # Format as ISO 8601 with timezone offset
                # Calculate timezone offset hours and minutes
                total_minutes = -client_timezone_offset  # Convert back to positive for display
                offset_hours = abs(total_minutes) // 60
                offset_minutes = abs(total_minutes) % 60
                offset_sign = '-' if client_timezone_offset > 0 else '+'

                formatted_time = local_dt.strftime(f'%Y-%m-%d %H:%M:%S{offset_sign}{offset_hours:02d}:{offset_minutes:02d}')

                xml_context_parts.append(f"  <Current_Time>{formatted_time}</Current_Time>")
            except Exception as e:
                logger.warning(f"Failed to parse timezone-aware timestamp '{client_timestamp_utc}' with offset '{client_timezone_offset}': {e}")
                # Fallback to raw UTC timestamp
                xml_context_parts.append(f"  <Current_Time>{client_timestamp_utc}</Current_Time>")
        # No timestamp information available
        pass

        # Add human input
        xml_context_parts.append("  <Human_Input>")
        xml_context_parts.append(f"    {current_input}")
        xml_context_parts.append("  </Human_Input>")
        xml_context_parts.append("</Context>")

        structured_context = "\n".join(xml_context_parts)

        # Add the structured context as the final user message
        # This combines dynamic context with user input in a single message
        messages.append({
            "role": "user",
            "content": structured_context
        })

        return messages

    async def _build_messages_with_history(self, session_id: str, system_prompt: str, current_input: str, client_timestamp_utc: str = "", client_timezone_offset: int = 0) -> List[Dict]:
        """Build messages list with conversation history from database.

        This method focuses on async I/O operations and delegates message formatting
        to the synchronous _format_llm_messages method.

        Args:
            session_id: The session ID to load history for
            system_prompt: The system prompt to include
            current_input: The current user input
            client_timestamp_utc: The client timestamp in ISO 8601 format
            client_timezone_offset: The client timezone offset in minutes

        Returns:
            List of message dictionaries for LLM context
        """
        history_from_db = []

        # Load recent conversation history if persistence service is available
        # This provides short-term memory by including recent messages in the context
        if self.persistence_service:
            try:
                # Get history context size from config
                history_limit = DEFAULT_HISTORY_LIMIT
                if self.config_service:
                    history_limit = self.config_service.get_int(CONFIG_HISTORY_SIZE_KEY, DEFAULT_HISTORY_LIMIT)

                # Retrieve historical messages
                history_from_db = await self.persistence_service.get_history(session_id, history_limit)
                logger.info(f"Added {len(history_from_db)} historical messages to context for session {session_id}")

            except Exception as e:
                logger.error(f"Failed to load conversation history for session {session_id}: {e}")
                # Continue without history if loading fails
                history_from_db = []

        # Format and return the messages using the synchronous method
        return self._format_llm_messages(system_prompt, history_from_db, current_input, client_timestamp_utc, client_timezone_offset)
