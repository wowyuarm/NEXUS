"""
Context service for NEXUS.

Responsible for building conversational context prior to LLM calls. It subscribes
for context build requests and publishes the build outputs when ready.

Key features:
- Dynamic prompt composition: Merges user-specific overrides with system defaults
  for personalized AI personas (persona, system, tools prompts)
- Tool registry integration: Provides available tool definitions to the LLM
- Conversation history: Loads recent messages from database for short-term memory
- Context revolution paradigm: Implements "thinking loop invariance" by keeping
  system prompts and history immutable while injecting dynamic context (timestamp,
  user input) in structured XML format
- Run deduplication: Filters out current run messages to prevent duplicate inputs
- Timezone-aware timestamp formatting for accurate temporal context
"""

import logging
from typing import List, Dict
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Run, Role
from nexus.core.topics import Topics
from nexus.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Constants
CONTENT_SEPARATOR = "\n\n---\n\n"
FALLBACK_SYSTEM_PROMPT = "You are NEXUS, an AI assistant. Please respond helpfully and thoughtfully."

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
            message: Message containing Run object as content
        """
        try:
            logger.info(f"Handling context build request for run_id={message.run_id}")

            # Extract Run object from message content
            run = message.content
            if not isinstance(run, Run):
                logger.error(f"Expected Run object in context build request for run_id={message.run_id}")
                return

            # Extract user_profile from Run.metadata
            user_profile = run.metadata.get('user_profile', {}) if run.metadata else {}

            # Extract current input from Run.history (first message)
            current_input = self._extract_user_input_from_run(run)
            if not current_input:
                logger.error(f"No current_input found in Run.history for run_id={run.id}")
                return

            # Extract client timestamp from run metadata
            client_timestamp_utc = run.metadata.get('client_timestamp_utc', '') if run.metadata else ''
            client_timezone_offset = run.metadata.get('client_timezone_offset', 0) if run.metadata else 0

            # Compose effective prompts (default + user overrides)
            effective_prompts = self._compose_effective_prompts(user_profile)

            # Build system prompt from composed prompts
            system_prompt = self._build_system_prompt_from_prompts(effective_prompts)

            # Build messages list with history
            messages = await self._build_messages_with_history(
                message.owner_key,
                system_prompt,
                current_input,
                client_timestamp_utc,
                client_timezone_offset,
                run.id
            )

            # Get all available tool definitions
            tools = self.tool_registry.get_all_tool_definitions()

            # Create response message
            response_message = Message(
                run_id=run.id,
                owner_key=message.owner_key,
                role=Role.SYSTEM,
                content={
                    "status": "success",
                    "messages": messages,
                    "tools": tools
                }
            )

            # Publish the context build response
            await self.bus.publish(Topics.CONTEXT_BUILD_RESPONSE, response_message)
            logger.info(f"Published context build response for run_id={run.id}")

        except Exception as e:
            logger.error(f"Error handling context build request for run_id={message.run_id}: {e}")
            # Publish error response
            error_message = Message(
                run_id=message.run_id,
                owner_key=message.owner_key,
                role=Role.SYSTEM,
                content={
                    "status": "error",
                    "messages": [],
                    "tools": []
                }
            )
            await self.bus.publish(Topics.CONTEXT_BUILD_RESPONSE, error_message)

    def _extract_user_input_from_run(self, run: Run) -> str:
        """Extract user input from the first message in run history."""
        if run.history and isinstance(run.history[0].content, str):
            return run.history[0].content
        return ""

    def _compose_effective_prompts(self, user_profile: Dict) -> Dict[str, str]:
        """
        Compose effective prompts by merging defaults with user overrides.
        
        Args:
            user_profile: User profile containing prompt_overrides
            
        Returns:
            Dictionary with effective prompts (persona, system, tools)
        """
        # Get default prompts from ConfigService
        user_defaults = self.config_service.get_user_defaults() if self.config_service else {}
        default_prompts = user_defaults.get('prompts', {})
        
        # Get user overrides (always simple strings)
        prompt_overrides = user_profile.get('prompt_overrides', {})
        
        # Helper to extract content from prompt object or string (backward compatible)
        def get_prompt_content(prompt_value):
            if isinstance(prompt_value, dict):
                return prompt_value.get('content', '')
            return prompt_value if isinstance(prompt_value, str) else ''
        
        # Merge (overrides take precedence)
        effective_prompts = {
            'persona': prompt_overrides.get('persona', get_prompt_content(default_prompts.get('persona', ''))),
            'system': prompt_overrides.get('system', get_prompt_content(default_prompts.get('system', ''))),
            'tools': prompt_overrides.get('tools', get_prompt_content(default_prompts.get('tools', '')))
        }
        
        logger.info(f"Composed effective prompts with overrides: {list(prompt_overrides.keys())}")
        return effective_prompts

    def _build_system_prompt_from_prompts(self, prompts: Dict[str, str]) -> str:
        """
        Build complete system prompt from prompts dictionary.
        
        Args:
            prompts: Dictionary containing persona, system, and tools prompts
            
        Returns:
            Complete system prompt string
        """
        parts = []
        for key in ['persona', 'system', 'tools']:
            content = prompts.get(key, '').strip()
            if content:
                parts.append(content)
        
        final_prompt = CONTENT_SEPARATOR.join(parts) if parts else FALLBACK_SYSTEM_PROMPT
        logger.info("System prompt constructed successfully from prompts dictionary")
        return final_prompt

    def _format_llm_messages(
        self,
        system_prompt: str,
        history_from_db: List[Dict],
        current_input: str,
        client_timestamp_utc: str = "",
        client_timezone_offset: int = 0,
        current_run_id: str = ""
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
            client_timezone_offset: The client timezone offset in minutes
            current_run_id: The current run ID for deduplication purposes

        Returns:
            List of message dictionaries formatted for LLM context
        """
        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        # Filter out messages from the current run to prevent duplicate input
        # This implements run_id-based deduplication to ensure clean context
        filtered_history = history_from_db
        if current_run_id:
            filtered_history = [
                msg for msg in history_from_db
                if msg.get('run_id') != current_run_id
            ]

        # Convert database messages to LLM format and add to context
        # This preserves the "thinking loop invariance" - history is immutable
        for msg_data in reversed(filtered_history):  # Reverse to get chronological order
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

    async def _build_messages_with_history(self, owner_key: str, system_prompt: str, current_input: str, client_timestamp_utc: str = "", client_timezone_offset: int = 0, current_run_id: str = "") -> List[Dict]:
        """Build messages list with conversation history from database.

        This method focuses on async I/O operations and delegates message formatting
        to the synchronous _format_llm_messages method.

        Args:
            owner_key: The owner's public key to load history for
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
                history_from_db = await self.persistence_service.get_history(owner_key, history_limit)
                logger.info(f"Added {len(history_from_db)} historical messages to context for owner_key={owner_key}")

            except Exception as e:
                logger.error(f"Failed to load conversation history for owner_key={owner_key}: {e}")
                # Continue without history if loading fails
                history_from_db = []

        # Format and return the messages using the synchronous method
        return self._format_llm_messages(system_prompt, history_from_db, current_input, client_timestamp_utc, client_timezone_offset, current_run_id)
