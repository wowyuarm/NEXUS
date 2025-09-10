"""Integration tests for configuration migration script."""

import pytest
import os
import tempfile
import yaml
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add the nexus directory to the Python path for testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "nexus"))

from nexus.scripts.migrate_config_to_db import load_yaml_config, substitute_env_vars, migrate_config_to_db


class TestConfigurationMigration:
    """Test suite for configuration migration script."""

    @pytest.fixture
    def sample_config_data(self):
        """Fixture providing sample configuration data."""
        return {
            "system": {
                "name": "NEXUS",
                "version": "1.0.0",
                "log_level": "INFO"
            },
            "llm": {
                "providers": {
                    "google": {
                        "model": "gemini-1.5-flash",
                        "api_key": "${GEMINI_API_KEY}",
                        "temperature": 0.7
                    },
                    "openrouter": {
                        "model": "anthropic/claude-3.5-sonnet",
                        "api_key": "${OPENROUTER_API_KEY}",
                        "temperature": 0.7
                    }
                }
            },
            "database": {
                "mongo_uri": "${MONGO_URI}",
                "db_name": "${DB_NAME}",
                "connection_timeout": 30
            }
        }

    @pytest.fixture
    def sample_config_file(self, tmp_path, sample_config_data):
        """Fixture creating a temporary config file."""
        config_file = tmp_path / "config.default.yml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)
        return str(config_file)

    @pytest.fixture
    def mock_mongo_provider(self):
        """Fixture providing a mock MongoProvider."""
        mock_provider = Mock()
        mock_provider.connect = Mock()
        mock_provider.disconnect = Mock()
        mock_provider.get_configuration = Mock()
        mock_provider.upsert_configuration = Mock()
        return mock_provider

    def test_load_yaml_config_success(self, sample_config_file, sample_config_data):
        """Test successful YAML configuration loading."""
        config = load_yaml_config(sample_config_file)
        assert config == sample_config_data

    def test_load_yaml_config_file_not_found(self):
        """Test YAML loading with non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_yaml_config("/nonexistent/config.yml")

    def test_load_yaml_config_invalid_yaml(self, tmp_path):
        """Test YAML loading with invalid YAML content."""
        config_file = tmp_path / "invalid.yml"
        with open(config_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        with pytest.raises(yaml.YAMLError):
            load_yaml_config(str(config_file))

    def test_substitute_env_vars_success(self, sample_config_data):
        """Test successful environment variable substitution."""
        env_vars = {
            'GEMINI_API_KEY': 'test_gemini_key',
            'OPENROUTER_API_KEY': 'test_openrouter_key',
            'MONGO_URI': 'mongodb://localhost:27017/test',
            'DB_NAME': 'test_db'
        }
        
        result = substitute_env_vars(sample_config_data, env_vars)
        
        assert result['llm']['providers']['google']['api_key'] == 'test_gemini_key'
        assert result['llm']['providers']['openrouter']['api_key'] == 'test_openrouter_key'
        assert result['database']['mongo_uri'] == 'mongodb://localhost:27017/test'
        assert result['database']['db_name'] == 'test_db'
        
        # Non-env var values should remain unchanged
        assert result['system']['name'] == 'NEXUS'
        assert result['llm']['providers']['google']['model'] == 'gemini-1.5-flash'

    def test_substitute_env_vars_missing(self, sample_config_data):
        """Test environment variable substitution with missing variables."""
        env_vars = {
            'GEMINI_API_KEY': 'test_gemini_key'
            # Missing other variables
        }
        
        result = substitute_env_vars(sample_config_data, env_vars)
        
        # Substituted variable
        assert result['llm']['providers']['google']['api_key'] == 'test_gemini_key'
        
        # Missing variables should remain as placeholders
        assert result['llm']['providers']['openrouter']['api_key'] == '${OPENROUTER_API_KEY}'
        assert result['database']['mongo_uri'] == '${MONGO_URI}'
        assert result['database']['db_name'] == '${DB_NAME}'

    def test_substitute_env_vars_empty_config(self):
        """Test environment variable substitution with empty configuration."""
        result = substitute_env_vars({}, {'TEST_VAR': 'test_value'})
        assert result == {}

    def test_substitute_env_vars_nested_structures(self):
        """Test environment variable substitution in nested structures."""
        config = {
            "level1": {
                "level2": {
                    "env_var": "${TEST_VAR}",
                    "normal": "value"
                },
                "list": [
                    {"item": "${LIST_VAR}"},
                    "normal_item"
                ]
            },
            "simple_var": "${SIMPLE_VAR}"
        }
        
        env_vars = {
            'TEST_VAR': 'test_value',
            'LIST_VAR': 'list_value',
            'SIMPLE_VAR': 'simple_value'
        }
        
        result = substitute_env_vars(config, env_vars)
        
        assert result['level1']['level2']['env_var'] == 'test_value'
        assert result['level1']['level2']['normal'] == 'value'
        assert result['level1']['list'][0]['item'] == 'list_value'
        assert result['level1']['list'][1] == 'normal_item'
        assert result['simple_var'] == 'simple_value'

    @patch('nexus.scripts.migrate_config_to_db.MongoProvider')
    def test_migrate_config_to_db_success(self, mock_provider_class, sample_config_file, 
                                         sample_config_data, mock_mongo_provider):
        """Test successful configuration migration to database."""
        # Setup mock provider
        mock_provider_class.return_value = mock_mongo_provider
        mock_mongo_provider.upsert_configuration.return_value = True
        mock_mongo_provider.get_configuration.return_value = sample_config_data
        
        # Mock environment variables
        test_env = {
            'MONGO_URI': 'mongodb://localhost:27017/test',
            'DB_NAME': 'test_db'
        }
        
        with patch.dict(os.environ, test_env):
            result = migrate_config_to_db(
                'mongodb://localhost:27017/test',
                'test_db',
                sample_config_file
            )
        
        assert result is True
        
        # Verify provider was created and connected
        mock_provider_class.assert_called_once_with('mongodb://localhost:27017/test', 'test_db')
        mock_mongo_provider.connect.assert_called_once()
        
        # Verify configuration was upserted
        mock_mongo_provider.upsert_configuration.assert_called_once_with(
            "system_config", sample_config_data
        )
        
        # Verify verification was performed
        mock_mongo_provider.get_configuration.assert_called_once_with("system_config")
        
        # Verify cleanup
        mock_mongo_provider.disconnect.assert_called_once()

    @patch('nexus.scripts.migrate_config_to_db.MongoProvider')
    def test_migrate_config_to_db_upsert_failure(self, mock_provider_class, sample_config_file, 
                                                mock_mongo_provider):
        """Test migration failure when upsert fails."""
        # Setup mock provider
        mock_provider_class.return_value = mock_mongo_provider
        mock_mongo_provider.upsert_configuration.return_value = False
        
        # Mock environment variables
        test_env = {
            'MONGO_URI': 'mongodb://localhost:27017/test',
            'DB_NAME': 'test_db'
        }
        
        with patch.dict(os.environ, test_env):
            result = migrate_config_to_db(
                'mongodb://localhost:27017/test',
                'test_db',
                sample_config_file
            )
        
        assert result is False
        mock_mongo_provider.disconnect.assert_called_once()

    @patch('nexus.scripts.migrate_config_to_db.MongoProvider')
    def test_migrate_config_to_db_verification_failure(self, mock_provider_class, sample_config_file, 
                                                      sample_config_data, mock_mongo_provider):
        """Test migration failure when verification fails."""
        # Setup mock provider
        mock_provider_class.return_value = mock_mongo_provider
        mock_mongo_provider.upsert_configuration.return_value = True
        mock_mongo_provider.get_configuration.return_value = None  # Verification fails
        
        # Mock environment variables
        test_env = {
            'MONGO_URI': 'mongodb://localhost:27017/test',
            'DB_NAME': 'test_db'
        }
        
        with patch.dict(os.environ, test_env):
            result = migrate_config_to_db(
                'mongodb://localhost:27017/test',
                'test_db',
                sample_config_file
            )
        
        assert result is False

    @patch('nexus.scripts.migrate_config_to_db.MongoProvider')
    def test_migrate_config_to_db_connection_error(self, mock_provider_class, sample_config_file):
        """Test migration failure when connection fails."""
        # Setup mock provider to raise connection error
        mock_provider_class.side_effect = Exception("Connection failed")
        
        # Mock environment variables
        test_env = {
            'MONGO_URI': 'mongodb://localhost:27017/test',
            'DB_NAME': 'test_db'
        }
        
        with patch.dict(os.environ, test_env):
            result = migrate_config_to_db(
                'mongodb://localhost:27017/test',
                'test_db',
                sample_config_file
            )
        
        assert result is False

    def test_migrate_config_to_db_missing_env_vars(self, sample_config_file):
        """Test migration failure when environment variables are missing."""
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            result = migrate_config_to_db(
                'mongodb://localhost:27017/test',
                'test_db',
                sample_config_file
            )
        
        assert result is False

    @patch('nexus.scripts.migrate_config_to_db.MongoProvider')
    def test_migrate_config_to_db_large_config(self, mock_provider_class, tmp_path, mock_mongo_provider):
        """Test migration with large configuration file."""
        # Create large configuration
        large_config = {
            "system": {
                "name": "NEXUS",
                "version": "1.0.0"
            },
            "large_data": {f"key_{i}": f"value_{i}" for i in range(1000)}
        }
        
        config_file = tmp_path / "large_config.yml"
        with open(config_file, 'w') as f:
            yaml.dump(large_config, f)
        
        # Setup mock provider
        mock_provider_class.return_value = mock_mongo_provider
        mock_mongo_provider.upsert_configuration.return_value = True
        mock_mongo_provider.get_configuration.return_value = large_config
        
        # Mock environment variables
        test_env = {
            'MONGO_URI': 'mongodb://localhost:27017/test',
            'DB_NAME': 'test_db'
        }
        
        with patch.dict(os.environ, test_env):
            result = migrate_config_to_db(
                'mongodb://localhost:27017/test',
                'test_db',
                str(config_file)
            )
        
        assert result is True
        mock_mongo_provider.upsert_configuration.assert_called_once_with(
            "system_config", large_config
        )

    @patch('nexus.scripts.migrate_config_to_db.MongoProvider')
    def test_migrate_config_to_db_exception_handling(self, mock_provider_class, sample_config_file, 
                                                    mock_mongo_provider):
        """Test exception handling during migration."""
        # Setup mock provider to raise exception during upsert
        mock_provider_class.return_value = mock_mongo_provider
        mock_mongo_provider.upsert_configuration.side_effect = Exception("Database error")
        
        # Mock environment variables
        test_env = {
            'MONGO_URI': 'mongodb://localhost:27017/test',
            'DB_NAME': 'test_db'
        }
        
        with patch.dict(os.environ, test_env):
            result = migrate_config_to_db(
                'mongodb://localhost:27017/test',
                'test_db',
                sample_config_file
            )
        
        assert result is False
        mock_mongo_provider.disconnect.assert_called_once()

    @patch('nexus.scripts.migrate_config_to_db.MongoProvider')
    def test_migrate_config_to_db_cleanup_on_error(self, mock_provider_class, sample_config_file, 
                                                   mock_mongo_provider):
        """Test that resources are cleaned up even when migration fails."""
        # Setup mock provider to raise exception during connect
        mock_provider_class.return_value = mock_mongo_provider
        mock_mongo_provider.connect.side_effect = Exception("Connection error")
        
        # Mock environment variables
        test_env = {
            'MONGO_URI': 'mongodb://localhost:27017/test',
            'DB_NAME': 'test_db'
        }
        
        with patch.dict(os.environ, test_env):
            result = migrate_config_to_db(
                'mongodb://localhost:27017/test',
                'test_db',
                sample_config_file
            )
        
        assert result is False
        # Disconnect should still be called
        mock_mongo_provider.disconnect.assert_called_once()

    def test_migrate_config_to_db_file_not_found(self):
        """Test migration with non-existent configuration file."""
        result = migrate_config_to_db(
            'mongodb://localhost:27017/test',
            'test_db',
            '/nonexistent/config.yml'
        )
        
        assert result is False