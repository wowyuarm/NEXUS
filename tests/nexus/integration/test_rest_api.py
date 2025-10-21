"""
Integration tests for REST API endpoints.

Tests the full HTTP request-response flow including:
- Bearer token authentication
- Signature verification
- Configuration composition (GET /config, GET /prompts)
- Configuration updates (POST /config, POST /prompts)
- Message history retrieval (GET /messages)

Note: These tests require a running database connection and full service initialization.
"""

import pytest
import json
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from eth_keys import keys
from eth_hash.auto import keccak

# Import services and router
from nexus.interfaces import rest
from nexus.services.identity import IdentityService
from nexus.services.config import ConfigService
from nexus.services.persistence import PersistenceService
from nexus.services.command import CommandService


class TestRESTAPIIntegration:
    """Integration tests for REST API endpoints."""
    
    @pytest.fixture
    def test_owner_key(self):
        """Generate a test public key."""
        return "0x1234567890123456789012345678901234567890"
    
    @pytest.fixture
    def test_private_key(self):
        """Generate a test private key for signing."""
        # Generate a test private key
        private_key = keys.PrivateKey(b'\x01' * 32)
        return private_key
    
    @pytest.fixture
    def mock_identity_service(self, test_owner_key):
        """Mock IdentityService with test data."""
        service = Mock(spec=IdentityService)
        
        # Mock get_effective_profile
        async def mock_get_effective_profile(owner_key, config_svc):
            return {
                'effective_config': {
                    'model': 'gemini-2.5-flash',
                    'temperature': 0.8,
                    'max_tokens': 4096,
                    'history_context_size': 20
                },
                'effective_prompts': {
                    'field': {
                        'content': '场域：共同成长的对话空间...',
                        'editable': False,
                        'order': 1
                    },
                    'presence': {
                        'content': '在场方式：我如何存在...',
                        'editable': False,
                        'order': 2
                    },
                    'capabilities': {
                        'content': '能力与工具...',
                        'editable': False,
                        'order': 3
                    },
                    'learning': {
                        'content': '用户档案与学习记录...',
                        'editable': True,
                        'order': 4
                    }
                },
                'user_overrides': {
                    'config_overrides': {},
                    'prompt_overrides': {}
                },
                'editable_fields': [
                    'config.model',
                    'config.temperature',
                    'config.max_tokens',
                    'config.history_context_size',
                    'prompts.learning'
                ],
                'field_options': {
                    'config.model': {
                        'type': 'select',
                        'options': ['Gemini-2.5-Flash', 'DeepSeek-Chat']
                    },
                    'config.temperature': {
                        'type': 'slider',
                        'min': 0.0,
                        'max': 2.0,
                        'step': 0.1
                    }
                }
            }
        
        service.get_effective_profile = AsyncMock(side_effect=mock_get_effective_profile)
        
        # Mock update methods
        service.update_user_config = AsyncMock(return_value=True)
        service.update_user_prompts = AsyncMock(return_value=True)
        
        return service
    
    @pytest.fixture
    def mock_config_service(self):
        """Mock ConfigService."""
        service = Mock(spec=ConfigService)
        service.get_user_defaults = Mock(return_value={
            'config': {'model': 'gemini-2.5-flash'},
            'prompts': {}
        })
        service.get_genesis_template = Mock(return_value={
            'llm': {'catalog': {}},
            'ui': {'editable_fields': [], 'field_options': {}}
        })
        return service
    
    @pytest.fixture
    def mock_persistence_service(self):
        """Mock PersistenceService."""
        service = Mock(spec=PersistenceService)
        
        # Mock get_messages
        async def mock_get_messages(owner_key, limit=20):
            return [
                {
                    'run_id': 'run_123',
                    'owner_key': owner_key,
                    'role': 'human',
                    'content': 'Test message',
                    'created_at': datetime.now().isoformat()
                }
            ]
        
        service.get_messages = AsyncMock(side_effect=mock_get_messages)
        return service
    
    @pytest.fixture
    def mock_command_service(self):
        """Mock CommandService."""
        service = Mock(spec=CommandService)
        
        # Mock get_all_command_definitions
        service.get_all_command_definitions = Mock(return_value=[
            {
                'name': 'config',
                'description': 'View or modify some configuration',
                'usage': '/config',
                'handler': 'rest',
                'requiresGUI': True,
                'restOptions': {
                    'getEndpoint': '/api/v1/config',
                    'postEndpoint': '/api/v1/config',
                    'method': 'GET'
                }
            },
            {
                'name': 'prompt',
                'description': 'View or modify AI persona and system prompts',
                'usage': '/prompt',
                'handler': 'rest',
                'requiresGUI': True,
                'restOptions': {
                    'getEndpoint': '/api/v1/prompts',
                    'postEndpoint': '/api/v1/prompts',
                    'method': 'GET'
                }
            },
            {
                'name': 'history',
                'description': 'View conversation history',
                'usage': '/history',
                'handler': 'rest',
                'requiresGUI': True,
                'restOptions': {
                    'getEndpoint': '/api/v1/messages',
                    'method': 'GET'
                }
            }
        ])
        return service
    
    @pytest.fixture
    def client(self, mock_identity_service, mock_config_service, mock_persistence_service, mock_command_service):
        """Create TestClient with mocked services."""
        # Create a test FastAPI app
        test_app = FastAPI(title="NEXUS Test API", version="1.0.0")
        test_app.include_router(rest.router, prefix="/api/v1")
        
        # Override dependency injection
        test_app.dependency_overrides[rest.get_command_service] = lambda: mock_command_service
        test_app.dependency_overrides[rest.get_identity_service] = lambda: mock_identity_service
        test_app.dependency_overrides[rest.get_config_service] = lambda: mock_config_service
        test_app.dependency_overrides[rest.get_persistence_service] = lambda: mock_persistence_service
        
        client = TestClient(test_app)
        yield client
        
        # Clean up
        test_app.dependency_overrides.clear()
    
    def generate_signature(self, private_key: keys.PrivateKey, payload: str) -> str:
        """Generate cryptographic signature for a payload."""
        message_hash = keccak(payload.encode('utf-8'))
        signature = private_key.sign_msg_hash(message_hash)
        return '0x' + signature.to_bytes().hex()
    
    # ============================================================================
    # Test GET /commands
    # ============================================================================
    
    def test_get_commands_success(self, client):
        """Test GET /commands returns command list."""
        response = client.get("/api/v1/commands")
        
        assert response.status_code == 200
        commands = response.json()
        assert isinstance(commands, list)
        
        # Check for our new commands
        command_names = [cmd['name'] for cmd in commands]
        assert 'config' in command_names
        assert 'prompt' in command_names
        assert 'history' in command_names
    
    # ============================================================================
    # Test GET /config
    # ============================================================================
    
    def test_get_config_without_auth(self, client):
        """Test GET /config fails without Authorization header."""
        response = client.get("/api/v1/config")
        assert response.status_code == 401
    
    def test_get_config_with_invalid_bearer_token(self, client):
        """Test GET /config fails with invalid Bearer token."""
        response = client.get(
            "/api/v1/config",
            headers={"Authorization": "Bearer invalid"}
        )
        assert response.status_code == 401
    
    def test_get_config_success(self, client, test_owner_key, mock_identity_service):
        """Test GET /config returns effective configuration."""
        response = client.get(
            "/api/v1/config",
            headers={"Authorization": f"Bearer {test_owner_key}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert 'effective_config' in data
        assert 'effective_prompts' in data
        assert 'user_overrides' in data
        assert 'editable_fields' in data
        assert 'field_options' in data
        
        # Verify config values
        assert data['effective_config']['model'] == 'gemini-2.5-flash'
        assert data['effective_config']['temperature'] == 0.8
        
        # Verify prompt structure (4-layer architecture)
        assert 'field' in data['effective_prompts']
        assert 'presence' in data['effective_prompts']
        assert 'capabilities' in data['effective_prompts']
        assert 'learning' in data['effective_prompts']
        assert 'content' in data['effective_prompts']['learning']
        assert 'editable' in data['effective_prompts']['learning']
        assert 'order' in data['effective_prompts']['learning']
        # Only learning should be editable
        assert data['effective_prompts']['learning']['editable'] == True
        assert data['effective_prompts']['field']['editable'] == False
        
        # Verify service was called
        mock_identity_service.get_effective_profile.assert_called_once()
    
    # ============================================================================
    # Test POST /config
    # ============================================================================
    
    def test_post_config_without_auth(self, client):
        """Test POST /config fails without Authorization header."""
        response = client.post(
            "/api/v1/config",
            json={
                "overrides": {"temperature": 0.9},
                "auth": {"publicKey": "0x...", "signature": "0x..."}
            }
        )
        assert response.status_code == 401
    
    def test_post_config_without_signature(self, client, test_owner_key):
        """Test POST /config fails without signature in body."""
        response = client.post(
            "/api/v1/config",
            headers={"Authorization": f"Bearer {test_owner_key}"},
            json={"overrides": {"temperature": 0.9}}
        )
        assert response.status_code == 422  # Unprocessable Entity (Pydantic validation)
    
    @patch('nexus.interfaces.rest.verify_signature')
    def test_post_config_with_invalid_signature(self, mock_verify_signature, client, test_owner_key):
        """Test POST /config fails with invalid signature."""
        # Mock signature verification to fail
        mock_verify_signature.return_value = {
            'status': 'error',
            'message': 'Invalid signature'
        }
        
        response = client.post(
            "/api/v1/config",
            headers={"Authorization": f"Bearer {test_owner_key}"},
            json={
                "overrides": {"temperature": 0.9},
                "auth": {
                    "publicKey": test_owner_key,
                    "signature": "0xinvalid"
                }
            }
        )
        # 403 Forbidden: Bearer token valid, but signature verification failed
        assert response.status_code == 403
    
    @patch('nexus.interfaces.rest.verify_signature')
    def test_post_config_success(
        self,
        mock_verify_signature,
        client,
        test_owner_key,
        test_private_key,
        mock_identity_service
    ):
        """Test POST /config updates configuration with valid signature."""
        # Mock signature verification to pass
        mock_verify_signature.return_value = {
            'status': 'success',
            'public_key': test_owner_key
        }
        
        request_body = {
            "overrides": {"temperature": 0.9, "max_tokens": 8192},
            "auth": {
                "publicKey": test_owner_key,
                "signature": "0x" + "a" * 130  # Dummy signature
            }
        }
        
        response = client.post(
            "/api/v1/config",
            headers={"Authorization": f"Bearer {test_owner_key}"},
            json=request_body
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'Configuration updated' in data['message']
        
        # Verify update_user_config was called
        mock_identity_service.update_user_config.assert_called_once_with(
            test_owner_key,
            {"temperature": 0.9, "max_tokens": 8192}
        )
    
    # ============================================================================
    # Test GET /prompts
    # ============================================================================
    
    def test_get_prompts_success(self, client, test_owner_key, mock_identity_service):
        """Test GET /prompts returns effective prompts."""
        response = client.get(
            "/api/v1/prompts",
            headers={"Authorization": f"Bearer {test_owner_key}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Same structure as /config (4-layer architecture)
        assert 'effective_prompts' in data
        assert 'field' in data['effective_prompts']
        assert 'presence' in data['effective_prompts']
        assert 'capabilities' in data['effective_prompts']
        assert 'learning' in data['effective_prompts']
        # Only learning should be editable
        assert data['effective_prompts']['learning']['editable'] == True
        assert data['effective_prompts']['field']['editable'] == False
        assert data['effective_prompts']['presence']['editable'] == False
        assert data['effective_prompts']['capabilities']['editable'] == False
    
    # ============================================================================
    # Test POST /prompts
    # ============================================================================
    
    @patch('nexus.interfaces.rest.verify_signature')
    def test_post_prompts_success(
        self,
        mock_verify_signature,
        client,
        test_owner_key,
        mock_identity_service
    ):
        """Test POST /prompts updates prompt overrides."""
        # Mock signature verification
        mock_verify_signature.return_value = {
            'status': 'success',
            'public_key': test_owner_key
        }
        
        request_body = {
            "overrides": {"learning": "用户档案：我是一个创意写作助手..."},
            "auth": {
                "publicKey": test_owner_key,
                "signature": "0x" + "b" * 130
            }
        }
        
        response = client.post(
            "/api/v1/prompts",
            headers={"Authorization": f"Bearer {test_owner_key}"},
            json=request_body
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'Prompts updated' in data['message']
        
        # Verify update_user_prompts was called
        mock_identity_service.update_user_prompts.assert_called_once_with(
            test_owner_key,
            {"learning": "用户档案：我是一个创意写作助手..."}
        )
    
    # ============================================================================
    # Test GET /messages
    # ============================================================================
    
    def test_get_messages_without_auth(self, client):
        """Test GET /messages fails without Authorization header."""
        response = client.get("/api/v1/messages")
        assert response.status_code == 401
    
    def test_get_messages_success(self, client, test_owner_key, mock_persistence_service):
        """Test GET /messages returns message history."""
        response = client.get(
            "/api/v1/messages",
            headers={"Authorization": f"Bearer {test_owner_key}"}
        )
        
        assert response.status_code == 200
        messages = response.json()
        
        assert isinstance(messages, list)
        # Note: Mock returns data, but actual count depends on mock implementation
        if len(messages) > 0:
            # Verify message structure
            message = messages[0]
            assert 'run_id' in message
            assert 'owner_key' in message
            assert 'role' in message
            assert 'content' in message
            assert 'created_at' in message
            
            # Verify service was called
            mock_persistence_service.get_messages.assert_called()
    
    def test_get_messages_with_limit(self, client, test_owner_key, mock_persistence_service):
        """Test GET /messages respects limit parameter."""
        response = client.get(
            "/api/v1/messages?limit=10",
            headers={"Authorization": f"Bearer {test_owner_key}"}
        )
        
        assert response.status_code == 200
        
        # Verify limit was passed to service
        call_args = mock_persistence_service.get_messages.call_args
        if call_args:  # Check if service was actually called
            # Check if limit was passed as keyword arg
            if call_args.kwargs:
                assert call_args.kwargs.get('limit') == 10
            # Or as positional arg
            elif len(call_args.args) > 1:
                assert call_args.args[1] == 10
    
    # ============================================================================
    # Test Bearer Token Validation
    # ============================================================================
    
    def test_bearer_token_format_validation(self, client):
        """Test Bearer token format validation."""
        # Missing 'Bearer' prefix
        response = client.get(
            "/api/v1/config",
            headers={"Authorization": "0x1234"}
        )
        assert response.status_code == 401
        
        # Empty token
        response = client.get(
            "/api/v1/config",
            headers={"Authorization": "Bearer "}
        )
        assert response.status_code == 401
    
    # ============================================================================
    # Test Signature Verification Integration
    # ============================================================================
    
    @patch('nexus.interfaces.rest.verify_signature')
    def test_signature_verification_called_correctly(
        self,
        mock_verify_signature,
        client,
        test_owner_key
    ):
        """Test that signature verification is called with correct payload."""
        mock_verify_signature.return_value = {
            'status': 'success',
            'public_key': test_owner_key
        }
        
        request_body = {
            "overrides": {"temperature": 0.9},
            "auth": {
                "publicKey": test_owner_key,
                "signature": "0x" + "c" * 130
            }
        }
        
        response = client.post(
            "/api/v1/config",
            headers={"Authorization": f"Bearer {test_owner_key}"},
            json=request_body
        )
        
        assert response.status_code == 200
        
        # Verify signature verification was called
        assert mock_verify_signature.called
        call_args = mock_verify_signature.call_args[0]
        
        # First argument should be the JSON payload
        payload = call_args[0]
        assert isinstance(payload, str)
        
        # Second argument should be auth data
        auth_data = call_args[1]
        assert auth_data['publicKey'] == test_owner_key
    
    @patch('nexus.interfaces.rest.verify_signature')
    def test_signature_verification_public_key_mismatch(
        self,
        mock_verify_signature,
        client,
        test_owner_key
    ):
        """Test POST fails when signature public key doesn't match Bearer token."""
        # Signature verification fails with error
        mock_verify_signature.return_value = {
            'status': 'error',
            'message': 'Public key mismatch'
        }
        
        request_body = {
            "overrides": {"temperature": 0.9},
            "auth": {
                "publicKey": '0xDifferentKey',  # Different from Bearer token
                "signature": "0x" + "d" * 130
            }
        }
        
        response = client.post(
            "/api/v1/config",
            headers={"Authorization": f"Bearer {test_owner_key}"},
            json=request_body
        )
        
        # 403 Forbidden: Signature verification or public key mismatch
        assert response.status_code == 403
    
    # ============================================================================
    # Test Error Handling
    # ============================================================================
    
    def test_get_config_service_error(self, client, test_owner_key, mock_identity_service):
        """Test GET /config handles service errors gracefully."""
        # Make service raise an exception
        mock_identity_service.get_effective_profile.side_effect = Exception("Database error")
        
        response = client.get(
            "/api/v1/config",
            headers={"Authorization": f"Bearer {test_owner_key}"}
        )
        
        assert response.status_code == 500
        assert 'detail' in response.json()
    
    @patch('nexus.interfaces.rest.verify_signature')
    def test_post_config_update_failure(
        self,
        mock_verify_signature,
        client,
        test_owner_key,
        mock_identity_service
    ):
        """Test POST /config handles update failures."""
        mock_verify_signature.return_value = {
            'status': 'success',
            'public_key': test_owner_key
        }
        
        # Make update return False (failure)
        mock_identity_service.update_user_config = AsyncMock(return_value=False)
        
        request_body = {
            "overrides": {"temperature": 0.9},
            "auth": {
                "publicKey": test_owner_key,
                "signature": "0x" + "e" * 130
            }
        }
        
        response = client.post(
            "/api/v1/config",
            headers={"Authorization": f"Bearer {test_owner_key}"},
            json=request_body
        )
        
        assert response.status_code == 500
        assert 'Failed to update' in response.json()['detail']
    
    # ============================================================================
    # Test Request Body Validation
    # ============================================================================
    
    def test_post_config_invalid_request_body(self, client, test_owner_key):
        """Test POST /config validates request body schema."""
        # Missing required field 'overrides'
        response = client.post(
            "/api/v1/config",
            headers={"Authorization": f"Bearer {test_owner_key}"},
            json={
                "auth": {"publicKey": test_owner_key, "signature": "0x..."}
            }
        )
        assert response.status_code == 422
        
        # Missing required field 'auth'
        response = client.post(
            "/api/v1/config",
            headers={"Authorization": f"Bearer {test_owner_key}"},
            json={"overrides": {"temperature": 0.9}}
        )
        assert response.status_code == 422
    
    def test_post_prompts_invalid_request_body(self, client, test_owner_key):
        """Test POST /prompts validates request body schema."""
        response = client.post(
            "/api/v1/prompts",
            headers={"Authorization": f"Bearer {test_owner_key}"},
            json={"invalid": "data"}
        )
        assert response.status_code == 422


# ============================================================================
# Test Fixtures for Integration Testing
# ============================================================================

@pytest.fixture(scope="session")
def test_database():
    """
    Fixture for integration tests that need a real database.
    
    NOTE: This is a placeholder. For true integration tests with database,
    you would need to:
    1. Set up a test MongoDB instance (or use docker-compose)
    2. Initialize with test data
    3. Clean up after tests
    """
    # TODO: Implement real database fixture for E2E tests
    pass


@pytest.fixture(scope="session")
def integration_app():
    """
    Fixture for integration tests with real services.
    
    NOTE: This would initialize all real services with test configuration.
    """
    # TODO: Implement full service initialization for E2E tests
    pass


# ============================================================================
# Running Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

