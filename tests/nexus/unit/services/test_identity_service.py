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

