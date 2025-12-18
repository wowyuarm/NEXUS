"""
Memory Learning Service for NEXUS.

Automatically learns user profiles from conversation history every N turns.
Subscribes to CONTEXT_BUILD_REQUEST events, increments turn counts, and triggers
LLM-based profile extraction when threshold is reached.
"""

import logging
from typing import Any

from nexus.core.bus import NexusBus
from nexus.core.models import Message
from nexus.core.topics import Topics
from nexus.services.config import ConfigService
from nexus.services.database.service import DatabaseService
from nexus.services.identity import IdentityService
from nexus.services.llm.service import LLMService
from nexus.services.persistence import PersistenceService

logger = logging.getLogger(__name__)


class MemoryLearningService:
    """Service for automatic user profile learning from conversation history."""

    def __init__(
        self,
        bus: NexusBus,
        identity_service: IdentityService,
        persistence_service: PersistenceService,
        llm_service: LLMService,
        config_service: ConfigService,
        database_service: DatabaseService,
    ):
        """Initialize MemoryLearningService.

        Args:
            bus: NexusBus for event subscription
            identity_service: For retrieving and updating user profiles
            persistence_service: For fetching conversation history
            llm_service: For extracting profile information via LLM
            config_service: For configuration (threshold, enabled state)
            database_service: For atomic turn count operations
        """
        self.bus = bus
        self.identity_service = identity_service
        self.persistence_service = persistence_service
        self.llm_service = llm_service
        self.config_service = config_service
        self.database_service = database_service
        logger.info("MemoryLearningService initialized")

    def subscribe_to_bus(self) -> None:
        """Subscribe to relevant bus topics."""
        self.bus.subscribe(
            Topics.CONTEXT_BUILD_REQUEST, self.handle_context_build_request
        )
        logger.info("MemoryLearningService subscribed to NexusBus")

    async def handle_context_build_request(self, message: Message) -> None:
        """Handle context build requests, increment turn count, trigger learning if needed.

        Args:
            message: Message containing Run object
        """
        try:
            run = message.content
            owner_key = message.owner_key

            # Check if learning is enabled
            if not self._is_learning_enabled():
                logger.debug("Memory learning is disabled, skipping")
                return

            # Increment turn count and check threshold
            should_learn = await self._should_learn(owner_key)
            if not should_learn:
                return

            # Trigger learning process
            await self._trigger_learning(owner_key, run.id)
            logger.info(
                f"Learning triggered for owner_key={owner_key}, run_id={run.id}"
            )

        except Exception as e:
            logger.error(
                f"Error handling context build request for run_id={message.run_id}: {e}"
            )

    def _is_learning_enabled(self) -> bool:
        """Check if memory learning is enabled via configuration.

        Returns:
            bool: True if learning is enabled, False otherwise
        """
        try:
            return self.config_service.get_bool("memory.learning.enabled", True)
        except Exception as e:
            logger.warning(
                f"Failed to read memory learning config, defaulting to enabled: {e}"
            )
            return True

    async def _should_learn(self, owner_key: str) -> bool:
        """Check if learning should be triggered for this user.

        Args:
            owner_key: User's public key

        Returns:
            bool: True if learning threshold reached, False otherwise
        """
        try:
            threshold = self.config_service.get_int(
                "memory.learning.threshold_turns", 20
            )
            if threshold <= 0:
                logger.warning(f"Invalid threshold {threshold}, disabling learning")
                return False

            if not self.database_service.provider:
                logger.error("Database provider not initialized")
                return False

            # Atomic increment and threshold check
            (
                should_learn,
                new_count,
            ) = await self.database_service.provider.increment_turn_count_and_check_threshold(
                owner_key, threshold
            )

            logger.debug(
                f"Turn count check for owner_key={owner_key}: "
                f"new_count={new_count}, threshold={threshold}, should_learn={should_learn}"
            )
            return should_learn

        except Exception as e:
            logger.error(
                f"Error checking learning threshold for owner_key={owner_key}: {e}"
            )
            return False

    async def _trigger_learning(self, owner_key: str, run_id: str) -> None:
        """Trigger the learning process for a user.

        Args:
            owner_key: User's public key
            run_id: Current run ID (for logging)
        """
        try:
            # 1. Get existing profile
            existing_profile = await self._get_existing_profile(owner_key)

            # 2. Get recent conversation history (last 20 messages)
            history = await self._get_recent_history(owner_key)

            # 3. Extract updated profile via LLM
            new_profile = await self._extract_profile_via_llm(
                owner_key, existing_profile, history
            )

            # 4. Update user profile in database
            await self._update_user_profile(owner_key, new_profile)

            logger.info(f"Profile updated for owner_key={owner_key}")

        except Exception as e:
            logger.error(f"Error triggering learning for owner_key={owner_key}: {e}")

    async def _get_existing_profile(self, owner_key: str) -> str:
        """Get existing user profile from identity.

        Args:
            owner_key: User's public key

        Returns:
            str: Existing profile content (empty string if none)
        """
        try:
            user_profile = await self.identity_service.get_user_profile(owner_key)
            prompt_overrides = user_profile.get("prompt_overrides", {})
            existing = prompt_overrides.get("friends_profile", "")
            return existing if isinstance(existing, str) else ""
        except Exception as e:
            logger.error(
                f"Error getting existing profile for owner_key={owner_key}: {e}"
            )
            return ""

    async def _get_full_user_profile(self, owner_key: str) -> dict:
        """Get full user profile dictionary from identity.

        Args:
            owner_key: User's public key

        Returns:
            dict: Full user profile document from identities collection
        """
        try:
            user_profile = await self.identity_service.get_user_profile(owner_key)
            return user_profile if isinstance(user_profile, dict) else {}
        except Exception as e:
            logger.error(
                f"Error getting full user profile for owner_key={owner_key}: {e}"
            )
            return {}

    async def _get_recent_history(self, owner_key: str) -> list[dict[str, Any]]:
        """Get recent conversation history for the user.

        Args:
            owner_key: User's public key

        Returns:
            List of message dicts (most recent first)
        """
        try:
            # Get last 20 messages (threshold matches learning interval)
            history = await self.persistence_service.get_history(owner_key, limit=20)
            return history if isinstance(history, list) else []
        except Exception as e:
            logger.error(f"Error getting history for owner_key={owner_key}: {e}")
            return []

    async def _extract_profile_via_llm(
        self, owner_key: str, existing_profile: str, history: list[dict[str, Any]]
    ) -> str:
        """Extract updated profile via LLM analysis.

        Args:
            owner_key: User's public key (for model configuration)
            existing_profile: Current profile text
            history: Recent conversation history

        Returns:
            str: Updated profile text for [FRIENDS_INFO] block
        """
        try:
            # Format history for LLM prompt
            formatted_history = self._format_history_for_prompt(history)

            # Build prompt
            prompt = self._build_learning_prompt(existing_profile, formatted_history)

            # Determine user_profile for LLM configuration
            llm_model = self.config_service.get("memory.learning.llm_model", "system")
            user_profile_for_llm = {}

            if llm_model == "user":
                # Use the user's own configuration (model preferences, temperature, etc.)
                full_profile = await self._get_full_user_profile(owner_key)
                user_profile_for_llm = full_profile
            # else: llm_model == "system" -> empty user_profile, LLM will use system defaults

            # Prepare messages for LLM call
            messages = [{"role": "user", "content": prompt}]

            # Call LLM synchronously
            new_profile: str = await self.llm_service.generate_text_sync(
                messages=messages, user_profile=user_profile_for_llm
            )

            # Clean up response (remove potential extra whitespace)
            if new_profile:
                new_profile = new_profile.strip()
                logger.info(f"LLM extracted new profile with length {len(new_profile)}")
                logger.debug(f"New profile preview: {new_profile[:200]}...")
                return new_profile
            else:
                logger.warning("LLM returned empty profile, keeping existing")
                return existing_profile

        except Exception as e:
            logger.error(f"Error extracting profile via LLM: {e}")
            return existing_profile  # Fallback to existing

    def _format_history_for_prompt(self, history: list[dict[str, Any]]) -> str:
        """Format history messages for LLM prompt.

        Args:
            history: List of message dicts

        Returns:
            str: Formatted history string
        """
        if not history:
            return "(No recent conversation history)"

        lines = []
        for msg in history[:20]:  # Limit to 20 messages
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            # Format role display
            if role == "human":
                role_display = "Human"
            elif role == "ai":
                role_display = "Nexus"
            else:
                role_display = role.capitalize()

            # Format timestamp
            time_str = ""
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        time_str = timestamp[:19]  # Truncate ISO string
                    else:
                        time_str = str(timestamp)
                except Exception:
                    pass

            # Truncate long content
            if len(content) > 200:
                content = content[:197] + "..."

            line = f"[{time_str}] {role_display}: {content}"
            lines.append(line)

        return "\n".join(lines)

    def _build_learning_prompt(
        self, existing_profile: str, formatted_history: str
    ) -> str:
        """Build LLM prompt for profile learning.

        Args:
            existing_profile: Current profile text
            formatted_history: Formatted conversation history

        Returns:
            str: Complete prompt for LLM
        """
        prompt = f"""你是一个真诚的朋友理解助手。你的任务是基于我与朋友的近期对话历史，来更新和完善我对这位朋友的认知。请你像我一样，用心回顾我们的对话，并根据这些交流，持续完善我们朋友的档案信息。

        现有朋友档案（我目前的理解）：
        {existing_profile if existing_profile else "(我还在学习和认识这位朋友，这里暂时是空白)"}

        近期对话历史（最近20条）：
        {formatted_history}

        更新要求：
        1. 保留已经确认的、有价值的认知，这些是重要的基础。
        2. 从最近的对话中，发现朋友新的兴趣、偏好、思考方式，以及他可能分享的背景信息。请尝试捕捉朋友的独特之处和潜在的关注点。
        3. 如果发现有任何过时或者不再准确的理解，请温柔地进行调整。
        4. 请确保你的输出简洁、自然，可以直接作为[FRIENDS_INFO]模块的内容，帮助我更好地记住和理解我的朋友。

        语言：使用对话历史中相同的语言，如果历史是中文则用中文，如果是英文则用英文。
        风格：真诚、温暖、有同理心，像一个真正的朋友在记录和理解对方。
        格式：请作为一个朋友自主权衡格式，保持段落清晰，信息有条理，用简洁的段落描述朋友的特点，避免冗长的列表。

        输出更新后的完整朋友档案（直接覆盖原内容）：
        """
        return prompt

    async def _update_user_profile(self, owner_key: str, new_profile: str) -> bool:
        """Update user profile in database.

        Args:
            owner_key: User's public key
            new_profile: New profile text

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            success = await self.identity_service.update_user_prompts(
                owner_key, {"friends_profile": new_profile}
            )
            if success:
                logger.info(f"Profile updated for owner_key={owner_key}")
            else:
                logger.error(f"Failed to update profile for owner_key={owner_key}")
            return success
        except Exception as e:
            logger.error(f"Error updating profile for owner_key={owner_key}: {e}")
            return False
