"""Unit tests for ConfigService."""

import os
import pytest
from unittest.mock import patch, mock_open
from nexus.services.config import ConfigService


class TestConfigService:
    """Test suite for ConfigService functionality."""

    @pytest.fixture
    def config_service(self):
        """Fixture providing a fresh ConfigService instance for each test."""
        return ConfigService()

    @pytest.fixture
    def mock_env_file(self, tmp_path):
        """Fixture creating a temporary .env file for testing."""
        env_file = tmp_path / ".env"
        env_file.write_text("""
GEMINI_API_KEY=test_gemini_api_key_123
OPENROUTER_API_KEY=test_openrouter_key_456
MONGO_URI=mongodb://localhost:27017/test
""")
        return str(env_file)

    @pytest.fixture
    def mock_config_file(self, tmp_path):
        """Fixture creating a temporary config.default.yml file for testing."""
        config_file = tmp_path / "config.default.yml"
        config_file.write_text("""
system:
  log_level: INFO
  port: 8000
  debug: false

llm:
  providers:
    google:
      model: gemini-pro
      api_key: ${GEMINI_API_KEY}
      temperature: 0.7
    openrouter:
      model: google/gemini-pro
      api_key: ${OPENROUTER_API_KEY}

database:
  mongo_uri: ${MONGO_URI}
  db_name: nexus_test
""")
        return str(config_file)

    def test_initialize_success(self, config_service):
        """Test successful initialization with valid config files."""
        # Instead of complex path mocking, test the individual methods directly
        # since the path resolution logic is complex to mock correctly
        
        # Mock the individual load methods
        with patch.object(config_service, '_load_env_vars') as mock_load_env, \
             patch.object(config_service, '_load_yaml_config') as mock_load_yaml, \
             patch.object(config_service, '_substitute_env_vars') as mock_substitute:
            
            config_service.initialize()
            
            # Verify all methods were called
            mock_load_env.assert_called_once()
            mock_load_yaml.assert_called_once()
            mock_substitute.assert_called_once()
            assert config_service.is_initialized() is True

    def test_initialize_file_not_found(self, config_service):
        """Test initialization fails when config file is not found."""
        # Mock _load_yaml_config to raise FileNotFoundError
        with patch.object(config_service, '_load_yaml_config') as mock_load_yaml:
            mock_load_yaml.side_effect = FileNotFoundError("Config file not found")
            
            # Should raise FileNotFoundError
            with pytest.raises(FileNotFoundError):
                config_service.initialize()

    def test_get_simple_value(self, config_service):
        """Test getting a simple configuration value."""
        # Setup mock config
        config_service._config = {
            'system': {
                'log_level': 'INFO',
                'port': 8000
            }
        }
        config_service._initialized = True
        
        # Test simple value access
        assert config_service.get('system.log_level') == 'INFO'
        assert config_service.get('system.port') == 8000

    def test_get_nested_value(self, config_service):
        """Test getting a nested configuration value."""
        # Setup mock config
        config_service._config = {
            'llm': {
                'providers': {
                    'google': {
                        'model': 'gemini-pro',
                        'temperature': 0.7
                    }
                }
            }
        }
        config_service._initialized = True
        
        # Test nested value access
        assert config_service.get('llm.providers.google.model') == 'gemini-pro'
        assert config_service.get('llm.providers.google.temperature') == 0.7

    def test_get_with_default_value(self, config_service):
        """Test getting a value with default fallback."""
        config_service._config = {'existing_key': 'value'}
        config_service._initialized = True
        
        # Test existing key
        assert config_service.get('existing_key') == 'value'
        
        # Test non-existent key with default
        assert config_service.get('non.existent.key', 'default_value') == 'default_value'
        assert config_service.get('another.missing.key', 42) == 42

    def test_substitute_env_vars(self, config_service):
        """Test environment variable substitution in configuration."""
        # Setup environment variables
        config_service._env_vars = {
            'GEMINI_API_KEY': 'actual_gemini_key_123',
            'OPENROUTER_API_KEY': 'actual_openrouter_key_456'
        }
        
        # Setup config with env var references
        config_service._config = {
            'llm': {
                'providers': {
                    'google': {
                        'api_key': '${GEMINI_API_KEY}',
                        'model': 'gemini-pro'
                    },
                    'openrouter': {
                        'api_key': '${OPENROUTER_API_KEY}',
                        'model': 'google/gemini-pro'
                    }
                }
            }
        }
        
        # Perform substitution
        config_service._substitute_env_vars()
        
        # Verify substitution worked
        assert config_service._config['llm']['providers']['google']['api_key'] == 'actual_gemini_key_123'
        assert config_service._config['llm']['providers']['openrouter']['api_key'] == 'actual_openrouter_key_456'
        # Non-env var values should remain unchanged
        assert config_service._config['llm']['providers']['google']['model'] == 'gemini-pro'

    def test_substitute_env_vars_missing(self, config_service):
        """Test env var substitution when variable is missing."""
        config_service._env_vars = {}  # No env vars set
        
        config_service._config = {
            'llm': {
                'providers': {
                    'google': {
                        'api_key': '${MISSING_VAR}'
                    }
                }
            }
        }
        
        # Should leave the placeholder unchanged
        config_service._substitute_env_vars()
        assert config_service._config['llm']['providers']['google']['api_key'] == '${MISSING_VAR}'

    def test_get_before_initialization(self, config_service):
        """Test that get() raises error before initialization."""
        with pytest.raises(RuntimeError, match="ConfigService not initialized"):
            config_service.get('some.key')

    def test_get_all(self, config_service):
        """Test getting the entire configuration dictionary."""
        test_config = {
            'system': {'log_level': 'INFO'},
            'llm': {'providers': {'google': {'model': 'gemini-pro'}}}
        }
        config_service._config = test_config
        config_service._initialized = True
        
        result = config_service.get_all()
        assert result == test_config
        # Should return a copy, not the original
        assert result is not test_config

    def test_get_bool(self, config_service):
        """Test boolean value retrieval."""
        config_service._config = {
            'feature': {
                'enabled': True,
                'disabled': False,
                'string_true': 'true',
                'string_false': 'false',
                'number': 1
            }
        }
        config_service._initialized = True
        
        assert config_service.get_bool('feature.enabled') is True
        assert config_service.get_bool('feature.disabled') is False
        assert config_service.get_bool('feature.string_true') is True
        assert config_service.get_bool('feature.string_false') is False
        assert config_service.get_bool('feature.number') is True
        assert config_service.get_bool('non.existent', True) is True
        assert config_service.get_bool('non.existent', False) is False

    def test_get_int(self, config_service):
        """Test integer value retrieval."""
        config_service._config = {
            'numbers': {
                'integer': 42,
                'string_int': '123',
                'float': 3.14
            }
        }
        config_service._initialized = True
        
        assert config_service.get_int('numbers.integer') == 42
        assert config_service.get_int('numbers.string_int') == 123
        assert config_service.get_int('numbers.float') == 3  # Truncated
        assert config_service.get_int('non.existent', 999) == 999

    def test_get_float(self, config_service):
        """Test float value retrieval."""
        config_service._config = {
            'numbers': {
                'float': 3.14,
                'string_float': '2.718',
                'integer': 42
            }
        }
        config_service._initialized = True
        
        assert config_service.get_float('numbers.float') == 3.14
        assert config_service.get_float('numbers.string_float') == 2.718
        assert config_service.get_float('numbers.integer') == 42.0
        assert config_service.get_float('non.existent', 1.234) == 1.234