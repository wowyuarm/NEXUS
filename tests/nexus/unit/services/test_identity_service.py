"""
Unit tests for IdentityService.

These tests verify that IdentityService correctly handles identity operations
including retrieval and creation of user identities.
All external dependencies are mocked to ensure isolation.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from nexus.services.identity import IdentityService


class TestIdentityService:
    """Test suite for IdentityService class."""

    def test_initialization(self):
        """Test that IdentityService initializes with correct attributes."""
        mock_db_service = Mock()
        service = IdentityService(db_service=mock_db_service)
        
        assert service.db_service == mock_db_service

    @pytest.mark.asyncio
    async def test_get_identity_not_found(self):
        """Test get_identity returns None when identity doesn't exist."""
        # Mock database service with provider
        mock_provider = Mock()
        mock_provider.find_identity_by_public_key = Mock(return_value=None)
        
        mock_db_service = Mock()
        mock_db_service.provider = mock_provider
        
        service = IdentityService(db_service=mock_db_service)
        
        result = await service.get_identity("nonexistent_public_key")
        
        assert result is None
        mock_provider.find_identity_by_public_key.assert_called_once_with("nonexistent_public_key")

    @pytest.mark.asyncio
    async def test_get_identity_found(self):
        """Test get_identity returns identity when it exists."""
        # Mock database service with provider
        mock_identity = {
            'public_key': 'test_public_key_123',
            'created_at': datetime.now(),
            'metadata': {'name': 'Test User'}
        }
        
        mock_provider = Mock()
        mock_provider.find_identity_by_public_key = Mock(return_value=mock_identity)
        
        mock_db_service = Mock()
        mock_db_service.provider = mock_provider
        
        service = IdentityService(db_service=mock_db_service)
        
        result = await service.get_identity("test_public_key_123")
        
        assert result == mock_identity
        assert result['public_key'] == 'test_public_key_123'
        mock_provider.find_identity_by_public_key.assert_called_once_with("test_public_key_123")

    @pytest.mark.asyncio
    async def test_create_identity_success(self):
        """Test create_identity successfully creates a new identity with overrides fields."""
        # Mock database service with provider
        mock_provider = Mock()
        mock_provider.create_identity = Mock(return_value=True)
        
        mock_db_service = Mock()
        mock_db_service.provider = mock_provider
        
        service = IdentityService(db_service=mock_db_service)
        
        result = await service.create_identity("test_public_key_123")
        
        assert result is True
        mock_provider.create_identity.assert_called_once()
        
        # Verify the identity_data structure
        call_args = mock_provider.create_identity.call_args[0][0]
        assert call_args['public_key'] == 'test_public_key_123'
        assert 'created_at' in call_args
        assert 'metadata' in call_args
        
        # Verify overrides fields are initialized as empty dicts
        assert 'config_overrides' in call_args
        assert call_args['config_overrides'] == {}
        assert 'prompt_overrides' in call_args
        assert call_args['prompt_overrides'] == {}

    @pytest.mark.asyncio
    async def test_create_identity_failure(self):
        """Test create_identity returns False when creation fails."""
        # Mock database service with provider
        mock_provider = Mock()
        mock_provider.create_identity = Mock(return_value=False)
        
        mock_db_service = Mock()
        mock_db_service.provider = mock_provider
        
        service = IdentityService(db_service=mock_db_service)
        
        result = await service.create_identity("test_public_key_123")
        
        assert result is False
        mock_provider.create_identity.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_identity_existing(self):
        """Test get_or_create_identity returns existing identity."""
        # Mock database service with provider
        mock_identity = {
            'public_key': 'test_public_key_123',
            'created_at': datetime.now(),
            'metadata': {}
        }
        
        mock_provider = Mock()
        mock_provider.find_identity_by_public_key = Mock(return_value=mock_identity)
        mock_provider.create_identity = Mock()
        
        mock_db_service = Mock()
        mock_db_service.provider = mock_provider
        
        service = IdentityService(db_service=mock_db_service)
        
        result = await service.get_or_create_identity("test_public_key_123")
        
        assert result == mock_identity
        mock_provider.find_identity_by_public_key.assert_called_once_with("test_public_key_123")
        # Should NOT call create_identity
        mock_provider.create_identity.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_identity_new(self):
        """Test get_or_create_identity creates and returns new identity."""
        # Mock database service with provider
        # After creation, simulate finding the newly created identity
        created_identity = {
            'public_key': 'test_public_key_123',
            'created_at': datetime.now(),
            'metadata': {}
        }
        
        mock_provider = Mock()
        # First call returns None (not found), second call returns the created identity
        mock_provider.find_identity_by_public_key = Mock(side_effect=[None, created_identity])
        mock_provider.create_identity = Mock(return_value=True)
        
        mock_db_service = Mock()
        mock_db_service.provider = mock_provider
        
        service = IdentityService(db_service=mock_db_service)
        
        result = await service.get_or_create_identity("test_public_key_123")
        
        assert result is not None
        assert result['public_key'] == 'test_public_key_123'
        
        # Should call find twice (before and after creation) and create once
        assert mock_provider.find_identity_by_public_key.call_count == 2
        mock_provider.create_identity.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_effective_profile_new_user(self):
        """Test get_effective_profile returns default config for new user (no overrides)."""
        # Mock identity service with no overrides
        mock_provider = Mock()
        mock_provider.find_identity_by_public_key = Mock(return_value={
            'public_key': 'test_key',
            'config_overrides': {},
            'prompt_overrides': {},
            'created_at': datetime.now()
        })
        
        mock_db_service = Mock()
        mock_db_service.provider = mock_provider
        
        # Mock config service
        mock_config_service = Mock()
        mock_config_service.get_user_defaults = Mock(return_value={
            'config': {
                'model': 'gemini-2.5-flash',
                'temperature': 0.7,
                'max_tokens': 4096
            },
            'prompts': {
                'persona': {'content': 'Default persona', 'editable': True, 'order': 1},
                'system': {'content': 'Default system', 'editable': False, 'order': 2},
                'tools': {'content': 'Default tools', 'editable': False, 'order': 3}
            }
        })
        mock_config_service.get_genesis_template = Mock(return_value={
            'llm': {'catalog': {}},
            'ui': {
                'editable_fields': ['config.model', 'config.temperature'],
                'field_options': {}
            }
        })
        
        service = IdentityService(db_service=mock_db_service)
        
        # Get effective profile
        profile = await service.get_effective_profile('test_key', mock_config_service)
        
        # Verify effective config matches defaults (no overrides)
        assert profile['effective_config']['model'] == 'gemini-2.5-flash'
        assert profile['effective_config']['temperature'] == 0.7
        assert profile['effective_config']['max_tokens'] == 4096
        
        # Verify effective prompts match defaults (now returns structured objects)
        assert profile['effective_prompts']['persona']['content'] == 'Default persona'
        assert profile['effective_prompts']['persona']['editable'] == True
        assert profile['effective_prompts']['persona']['order'] == 1
        assert profile['effective_prompts']['system']['content'] == 'Default system'
        assert profile['effective_prompts']['system']['editable'] == False
        assert profile['effective_prompts']['tools']['content'] == 'Default tools'
        
        # Verify user overrides are empty
        assert profile['user_overrides']['config_overrides'] == {}
        assert profile['user_overrides']['prompt_overrides'] == {}
        
        # Verify UI metadata
        assert 'editable_fields' in profile
        assert 'field_options' in profile

    @pytest.mark.asyncio
    async def test_get_effective_profile_with_config_overrides(self):
        """Test get_effective_profile merges config overrides correctly."""
        # Mock identity with config overrides
        mock_provider = Mock()
        mock_provider.find_identity_by_public_key = Mock(return_value={
            'public_key': 'test_key',
            'config_overrides': {
                'model': 'deepseek-chat',
                'temperature': 0.9
            },
            'prompt_overrides': {},
            'created_at': datetime.now()
        })
        
        mock_db_service = Mock()
        mock_db_service.provider = mock_provider
        
        # Mock config service with defaults
        mock_config_service = Mock()
        mock_config_service.get_user_defaults = Mock(return_value={
            'config': {
                'model': 'gemini-2.5-flash',
                'temperature': 0.7,
                'max_tokens': 4096
            },
            'prompts': {}
        })
        mock_config_service.get_genesis_template = Mock(return_value={
            'llm': {'catalog': {}},
            'ui': {'editable_fields': [], 'field_options': {}}
        })
        
        service = IdentityService(db_service=mock_db_service)
        profile = await service.get_effective_profile('test_key', mock_config_service)
        
        # Verify overridden values
        assert profile['effective_config']['model'] == 'deepseek-chat'
        assert profile['effective_config']['temperature'] == 0.9
        
        # Verify non-overridden value stays default
        assert profile['effective_config']['max_tokens'] == 4096
        
        # Verify overrides are preserved
        assert profile['user_overrides']['config_overrides']['model'] == 'deepseek-chat'

    @pytest.mark.asyncio
    async def test_get_effective_profile_with_prompt_overrides(self):
        """Test get_effective_profile merges prompt overrides correctly."""
        # Mock identity with prompt overrides
        mock_provider = Mock()
        mock_provider.find_identity_by_public_key = Mock(return_value={
            'public_key': 'test_key',
            'config_overrides': {},
            'prompt_overrides': {
                'persona': 'Custom persona override'
            },
            'created_at': datetime.now()
        })
        
        mock_db_service = Mock()
        mock_db_service.provider = mock_provider
        
        # Mock config service
        mock_config_service = Mock()
        mock_config_service.get_user_defaults = Mock(return_value={
            'config': {},
            'prompts': {
                'persona': {'content': 'Default persona', 'editable': True, 'order': 1},
                'system': {'content': 'Default system', 'editable': False, 'order': 2},
                'tools': {'content': 'Default tools', 'editable': False, 'order': 3}
            }
        })
        mock_config_service.get_genesis_template = Mock(return_value={
            'llm': {'catalog': {}},
            'ui': {'editable_fields': [], 'field_options': {}}
        })
        
        service = IdentityService(db_service=mock_db_service)
        profile = await service.get_effective_profile('test_key', mock_config_service)
        
        # Verify overridden persona (content is overridden, but metadata preserved)
        assert profile['effective_prompts']['persona']['content'] == 'Custom persona override'
        assert profile['effective_prompts']['persona']['editable'] == True  # Preserved from default
        assert profile['effective_prompts']['persona']['order'] == 1  # Preserved from default
        
        # Verify non-overridden prompts stay default
        assert profile['effective_prompts']['system']['content'] == 'Default system'
        assert profile['effective_prompts']['tools']['content'] == 'Default tools'
        
        # Verify overrides are preserved
        assert profile['user_overrides']['prompt_overrides']['persona'] == 'Custom persona override'

    @pytest.mark.asyncio
    async def test_get_effective_profile_complete_overrides(self):
        """Test get_effective_profile with both config and prompt overrides."""
        # Mock identity with complete overrides
        mock_provider = Mock()
        mock_provider.find_identity_by_public_key = Mock(return_value={
            'public_key': 'test_key',
            'config_overrides': {
                'model': 'deepseek-chat',
                'temperature': 0.95,
                'max_tokens': 8192
            },
            'prompt_overrides': {
                'persona': 'Custom persona',
                'system': 'Custom system'
            },
            'created_at': datetime.now()
        })
        
        mock_db_service = Mock()
        mock_db_service.provider = mock_provider
        
        # Mock config service
        mock_config_service = Mock()
        mock_config_service.get_user_defaults = Mock(return_value={
            'config': {
                'model': 'gemini-2.5-flash',
                'temperature': 0.7,
                'max_tokens': 4096
            },
            'prompts': {
                'persona': {'content': 'Default persona', 'editable': True, 'order': 1},
                'system': {'content': 'Default system', 'editable': False, 'order': 2},
                'tools': {'content': 'Default tools', 'editable': False, 'order': 3}
            }
        })
        mock_config_service.get_genesis_template = Mock(return_value={
            'llm': {'catalog': {}},
            'ui': {'editable_fields': [], 'field_options': {}}
        })
        
        service = IdentityService(db_service=mock_db_service)
        profile = await service.get_effective_profile('test_key', mock_config_service)
        
        # Verify all config overrides
        assert profile['effective_config']['model'] == 'deepseek-chat'
        assert profile['effective_config']['temperature'] == 0.95
        assert profile['effective_config']['max_tokens'] == 8192
        
        # Verify all prompt overrides (content overridden, metadata preserved)
        assert profile['effective_prompts']['persona']['content'] == 'Custom persona'
        assert profile['effective_prompts']['system']['content'] == 'Custom system'
        assert profile['effective_prompts']['tools']['content'] == 'Default tools'  # Not overridden

    @pytest.mark.asyncio
    async def test_update_user_config_success(self):
        """Test update_user_config successfully updates configuration."""
        # Mock successful update
        mock_provider = Mock()
        mock_provider.update_identity_field = Mock(return_value=True)
        
        mock_db_service = Mock()
        mock_db_service.provider = mock_provider
        
        service = IdentityService(db_service=mock_db_service)
        
        overrides = {'model': 'deepseek-chat', 'temperature': 0.9}
        result = await service.update_user_config('test_key', overrides)
        
        assert result is True
        mock_provider.update_identity_field.assert_called_once_with(
            'test_key',
            'config_overrides',
            overrides
        )

    @pytest.mark.asyncio
    async def test_update_user_prompts_success(self):
        """Test update_user_prompts successfully updates prompts."""
        # Mock successful update
        mock_provider = Mock()
        mock_provider.update_identity_field = Mock(return_value=True)
        
        mock_db_service = Mock()
        mock_db_service.provider = mock_provider
        
        service = IdentityService(db_service=mock_db_service)
        
        overrides = {'persona': 'My custom persona'}
        result = await service.update_user_prompts('test_key', overrides)
        
        assert result is True
        mock_provider.update_identity_field.assert_called_once_with(
            'test_key',
            'prompt_overrides',
            overrides
        )

