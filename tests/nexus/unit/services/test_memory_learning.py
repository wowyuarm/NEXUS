"""
Unit tests for MemoryLearningService.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from nexus.core.models import Message, Role, Run
from nexus.services.memory_learning import MemoryLearningService


class TestMemoryLearningService:
    """Test suite for MemoryLearningService."""

    @pytest.fixture
    def mock_bus(self):
        return Mock()

    @pytest.fixture
    def mock_identity_service(self):
        return AsyncMock()

    @pytest.fixture
    def mock_persistence_service(self):
        return AsyncMock()

    @pytest.fixture
    def mock_llm_service(self):
        return AsyncMock()

    @pytest.fixture
    def mock_config_service(self):
        config = Mock()
        config.get_bool = Mock(return_value=True)
        config.get_int = Mock(return_value=20)
        config.get = Mock(return_value="system")
        return config

    @pytest.fixture
    def mock_database_service(self):
        db = Mock()
        db.provider = Mock()
        return db

    @pytest.fixture
    def memory_learning_service(
        self,
        mock_bus,
        mock_identity_service,
        mock_persistence_service,
        mock_llm_service,
        mock_config_service,
        mock_database_service,
    ):
        return MemoryLearningService(
            bus=mock_bus,
            identity_service=mock_identity_service,
            persistence_service=mock_persistence_service,
            llm_service=mock_llm_service,
            config_service=mock_config_service,
            database_service=mock_database_service,
        )

    @pytest.mark.asyncio
    async def test_handle_context_build_request_below_threshold(
        self, memory_learning_service, mock_database_service
    ):
        """Test that learning is not triggered when count < threshold."""
        # Mock turn count check to return False (below threshold)
        mock_database_service.provider.increment_turn_count_and_check_threshold = AsyncMock(
            return_value=(False, 5)
        )

        # Mock message with Run object
        run = Run(id="test_run", owner_key="0x123", history=[])
        message = Message(run_id="test_run", owner_key="0x123", role=Role.SYSTEM, content=run)

        # Call handler
        await memory_learning_service.handle_context_build_request(message)

        # Verify turn count was checked
        mock_database_service.provider.increment_turn_count_and_check_threshold.assert_called_once_with(
            "0x123", 20
        )

    @pytest.mark.asyncio
    async def test_handle_context_build_request_at_threshold(
        self, memory_learning_service, mock_database_service
    ):
        """Test that learning is triggered when threshold reached."""
        # Mock turn count check to return True (threshold reached)
        mock_database_service.provider.increment_turn_count_and_check_threshold = AsyncMock(
            return_value=(True, 20)
        )

        # Mock the learning process methods
        with patch.object(memory_learning_service, '_trigger_learning', new_callable=AsyncMock) as mock_trigger:
            # Mock message with Run object
            run = Run(id="test_run", owner_key="0x123", history=[])
            message = Message(run_id="test_run", owner_key="0x123", role=Role.SYSTEM, content=run)

            # Call handler
            await memory_learning_service.handle_context_build_request(message)

            # Verify turn count was checked and learning triggered
            mock_database_service.provider.increment_turn_count_and_check_threshold.assert_called_once_with(
                "0x123", 20
            )
            mock_trigger.assert_called_once_with("0x123", "test_run")

    @pytest.mark.asyncio
    async def test_extract_profile_via_llm_format(self, memory_learning_service):
        """Test that LLM prompt includes existing profile and formatted history."""
        owner_key = "0x123"
        existing_profile = "User likes coding in Python."
        history = [
            {"role": "human", "content": "I prefer Python over Java.", "timestamp": "2025-12-18T10:00:00Z"},
            {"role": "ai", "content": "Python is a great choice.", "timestamp": "2025-12-18T10:01:00Z"},
        ]

        # Mock config
        memory_learning_service.config_service.get = Mock(return_value="system")
        # Mock LLM service to return a new profile
        mock_response = "User enjoys programming in Python and prefers it over Java."
        memory_learning_service.llm_service.generate_text_sync = AsyncMock(return_value=mock_response)
        # Mock _get_full_user_profile to return empty dict (not used for "system" mode)
        memory_learning_service._get_full_user_profile = AsyncMock(return_value={})

        # Call the method
        result = await memory_learning_service._extract_profile_via_llm(owner_key, existing_profile, history)

        # Should return the mocked LLM response
        assert result == mock_response

        # Verify config was read
        memory_learning_service.config_service.get.assert_called_with("memory.learning.llm_model", "system")
        # Verify LLM was called with correct messages
        memory_learning_service.llm_service.generate_text_sync.assert_called_once()
        call_args = memory_learning_service.llm_service.generate_text_sync.call_args
        assert call_args.kwargs["user_profile"] == {}  # Empty for "system" mode
        messages = call_args.kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert existing_profile in messages[0]["content"]
        assert "I prefer Python over Java" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_update_user_profile_calls_identity_service(
        self, memory_learning_service, mock_identity_service
    ):
        """Test that profile update calls identity service."""
        owner_key = "0x123"
        new_profile = "Updated profile with new preferences."

        mock_identity_service.update_user_prompts = AsyncMock(return_value=True)

        result = await memory_learning_service._update_user_profile(owner_key, new_profile)

        assert result is True
        mock_identity_service.update_user_prompts.assert_called_once_with(
            owner_key, {"friends_profile": new_profile}
        )

    @pytest.mark.asyncio
    async def test_learning_disabled_by_config(self, memory_learning_service, mock_config_service):
        """Test that learning is skipped when disabled in config."""
        # Mock config to return False for enabled
        mock_config_service.get_bool.return_value = False

        # Mock message
        run = Run(id="test_run", owner_key="0x123", history=[])
        message = Message(run_id="test_run", owner_key="0x123", role=Role.SYSTEM, content=run)

        # Mock turn count check (should not be called)
        memory_learning_service.database_service.provider.increment_turn_count_and_check_threshold = AsyncMock()

        await memory_learning_service.handle_context_build_request(message)

        # Verify turn count was NOT checked
        memory_learning_service.database_service.provider.increment_turn_count_and_check_threshold.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_existing_profile_success(self, memory_learning_service, mock_identity_service):
        """Test retrieving existing profile from identity service."""
        owner_key = "0x123"
        expected_profile = "User profile content"

        mock_identity_service.get_user_profile = AsyncMock(return_value={
            "public_key": owner_key,
            "prompt_overrides": {"friends_profile": expected_profile}
        })

        result = await memory_learning_service._get_existing_profile(owner_key)

        assert result == expected_profile
        mock_identity_service.get_user_profile.assert_called_once_with(owner_key)

    @pytest.mark.asyncio
    async def test_get_existing_profile_empty(self, memory_learning_service, mock_identity_service):
        """Test retrieving empty profile."""
        owner_key = "0x123"

        mock_identity_service.get_user_profile = AsyncMock(return_value={
            "public_key": owner_key,
            "prompt_overrides": {}
        })

        result = await memory_learning_service._get_existing_profile(owner_key)

        assert result == ""
        mock_identity_service.get_user_profile.assert_called_once_with(owner_key)

    @pytest.mark.asyncio
    async def test_get_recent_history_success(self, memory_learning_service, mock_persistence_service):
        """Test retrieving recent conversation history."""
        owner_key = "0x123"
        expected_history = [
            {"role": "human", "content": "Hello", "timestamp": "2025-12-18T10:00:00Z"},
            {"role": "ai", "content": "Hi there", "timestamp": "2025-12-18T10:01:00Z"},
        ]

        mock_persistence_service.get_history = AsyncMock(return_value=expected_history)

        result = await memory_learning_service._get_recent_history(owner_key)

        assert result == expected_history
        mock_persistence_service.get_history.assert_called_once_with(owner_key, limit=20)

    @pytest.mark.asyncio
    async def test_format_history_for_prompt(self, memory_learning_service):
        """Test formatting history for LLM prompt."""
        history = [
            {"role": "human", "content": "I like Python.", "timestamp": "2025-12-18T10:00:00Z"},
            {"role": "ai", "content": "Python is great.", "timestamp": "2025-12-18T10:01:00Z"},
            {"role": "tool", "content": "Tool result", "timestamp": "2025-12-18T10:02:00Z"},  # Should be included
        ]

        formatted = memory_learning_service._format_history_for_prompt(history)

        assert "[2025-12-18T10:00:00] Human: I like Python." in formatted
        assert "[2025-12-18T10:01:00] Nexus: Python is great." in formatted
        assert "[2025-12-18T10:02:00] Tool: Tool result" in formatted

    @pytest.mark.asyncio
    async def test_format_history_for_prompt_empty(self, memory_learning_service):
        """Test formatting empty history."""
        result = memory_learning_service._format_history_for_prompt([])
        assert result == "(No recent conversation history)"

    @pytest.mark.asyncio
    async def test_format_history_truncation(self, memory_learning_service):
        """Test that long messages are truncated."""
        long_content = "A" * 250  # 250 characters
        history = [
            {"role": "human", "content": long_content, "timestamp": "2025-12-18T10:00:00Z"},
        ]

        formatted = memory_learning_service._format_history_for_prompt(history)
        assert len(formatted) < 250 + 50  # Original length plus timestamp/role
        assert "..." in formatted

    def test_build_learning_prompt(self, memory_learning_service):
        """Test building LLM prompt with existing profile and history."""
        existing_profile = "User enjoys programming."
        formatted_history = "[2025-12-18T10:00:00] Human: I like Python.\n[2025-12-18T10:01:00] Nexus: That's great."

        prompt = memory_learning_service._build_learning_prompt(existing_profile, formatted_history)

        assert "现有朋友档案（我目前的理解）：" in prompt
        assert existing_profile in prompt
        assert "近期对话历史（最近20条）：" in prompt
        assert formatted_history in prompt
        assert "输出更新后的完整朋友档案（直接覆盖原内容）：" in prompt

    def test_build_learning_prompt_empty_profile(self, memory_learning_service):
        """Test building prompt with empty profile."""
        prompt = memory_learning_service._build_learning_prompt("", "Some history")
        assert "(我还在学习和认识这位朋友，这里暂时是空白)" in prompt