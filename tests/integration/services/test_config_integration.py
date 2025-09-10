"""Integration tests for the configuration system.

Tests the integration between ConfigService, DatabaseService, and MongoProvider
to ensure the complete database-first configuration workflow functions correctly.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pymongo.errors import OperationFailure, ConnectionFailure
from nexus.services.config import ConfigService
from nexus.services.database.service import DatabaseService
from nexus.services.database.providers.mongo import MongoProvider
from nexus.core.bus import NexusBus


class TestConfigurationIntegration:
    """Integration test suite for the configuration system."""

    @pytest.fixture
    def mock_bus(self):
        """Fixture providing a mock NexusBus."""
        return Mock(spec=NexusBus)

    @pytest.fixture
    def mock_config_service(self):
        """Fixture providing a ConfigService instance."""
        return ConfigService()

    @pytest.fixture
    def mock_mongo_provider(self):
        """Fixture providing a mock MongoProvider."""
        mock_provider = Mock(spec=MongoProvider)
        mock_provider.connect = Mock()
        mock_provider.disconnect = Mock()
        mock_provider.get_configuration = Mock()
        mock_provider.upsert_configuration = Mock()
        mock_provider.health_check = Mock(return_value=True)
        return mock_provider

    @pytest.fixture
    def database_service(self, mock_bus, mock_config_service, mock_mongo_provider, mocker):
        """Fixture providing a DatabaseService with mocked provider."""
        # Mock ConfigService to return database configuration
        mock_config_service.get.side_effect = lambda key, default=None: {
            "database.mongo_uri": "mongodb://localhost:27017/test",
            "database.db_name": "test_db",
            "database.connection_timeout": 30,
            "database.max_pool_size": 10
        }.get(key, default)
        
        # Mock MongoProvider creation
        mock_provider_class = mocker.patch('nexus.services.database.service.MongoProvider')
        mock_provider_class.return_value = mock_mongo_provider
        
        return DatabaseService(mock_bus, mock_config_service)

    @pytest.fixture
    def sample_database_config(self):
        """Fixture providing sample database configuration."""
        return {
            "system": {
                "name": "NEXUS-Production",
                "environment": "production",
                "log_level": "WARNING"
            },
            "llm": {
                "temperature": 0.3,
                "max_tokens": 2000
            },
            "database": {
                "max_pool_size": 20,
                "connection_timeout": 60
            }
        }

    @pytest.fixture
    def sample_update_config(self):
        """Fixture providing sample configuration update data."""
        return {
            "system": {
                "log_level": "DEBUG"
            },
            "llm": {
                "temperature": 0.9
            }
        }

    # End-to-End Configuration Loading Tests
    def test_complete_configuration_loading_workflow(self, mock_config_service, database_service, sample_database_config, mocker):
        """Test complete configuration loading workflow from database to ConfigService."""
        # Mock database response
        database_service.provider.get_configuration.return_value = sample_database_config
        
        # Mock asyncio event loop
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = sample_database_config
        mocker.patch('asyncio.get_event_loop', return_value=mock_loop)
        
        # Initialize ConfigService with DatabaseService
        mock_config_service.initialize(database_service)
        
        # Verify configuration was loaded from database
        assert mock_config_service.is_initialized() is True
        assert mock_config_service.get('system.name') == 'NEXUS-Production'
        assert mock_config_service.get('system.environment') == 'production'
        assert mock_config_service.get('system.log_level') == 'WARNING'
        assert mock_config_service.get('llm.temperature') == 0.3
        assert mock_config_service.get('llm.max_tokens') == 2000
        
        # Verify default values are preserved (not in database config)
        assert mock_config_service.get('llm.default_provider') == 'google'
        assert mock_config_service.get('system.version') == '1.0.0'
        
        # Verify database was called
        database_service.provider.get_configuration.assert_called_once_with("system_config")

    def test_configuration_loading_with_database_unavailable(self, mock_config_service, database_service, mocker):
        """Test configuration loading when database is unavailable."""
        # Mock database error
        mock_loop = Mock()
        mock_loop.run_until_complete.side_effect = Exception("Database unavailable")
        mocker.patch('asyncio.get_event_loop', return_value=mock_loop)
        
        # Mock logger to capture warnings
        mock_logger = mocker.patch('nexus.services.config.logger')
        
        # Initialize ConfigService with DatabaseService
        mock_config_service.initialize(database_service)
        
        # Verify initialization succeeded with defaults
        assert mock_config_service.is_initialized() is True
        assert mock_config_service.get('system.name') == 'NEXUS'
        assert mock_config_service.get('system.version') == '1.0.0'
        
        # Verify warning was logged
        mock_logger.warning.assert_called()
        warning_calls = [call for call in mock_logger.warning.call_args_list]
        assert any("Unable to load configuration from database" in str(call) for call in warning_calls)

    def test_configuration_loading_with_empty_database(self, mock_config_service, database_service, mocker):
        """Test configuration loading when database returns empty configuration."""
        # Mock database response (None)
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = None
        mocker.patch('asyncio.get_event_loop', return_value=mock_loop)
        
        # Mock logger to capture warnings
        mock_logger = mocker.patch('nexus.services.config.logger')
        
        # Initialize ConfigService with DatabaseService
        mock_config_service.initialize(database_service)
        
        # Verify initialization succeeded with defaults
        assert mock_config_service.is_initialized() is True
        assert mock_config_service.get('system.name') == 'NEXUS'
        assert mock_config_service.get('system.version') == '1.0.0'
        
        # Verify warning was logged
        mock_logger.warning.assert_called_once_with("No configuration found in database, using defaults")

    # Configuration Update Integration Tests
    @pytest.mark.asyncio
    async def test_configuration_update_workflow(self, mock_config_service, database_service, sample_update_config, mocker):
        """Test configuration update workflow through all layers."""
        # Setup ConfigService
        mock_config_service._database_service = database_service
        mock_config_service._initialized = True
        mock_config_service._config = {"system": {"log_level": "INFO"}, "llm": {"temperature": 0.7}}
        
        # Mock successful database update
        database_service.provider.upsert_configuration.return_value = True
        
        # Mock database service async method
        database_service.upsert_configuration_async = AsyncMock(return_value=True)
        
        # Update configuration through ConfigService
        result = await mock_config_service.update_configuration_async(sample_update_config)
        
        # Verify update succeeded
        assert result is True
        
        # Verify local cache was updated
        assert mock_config_service.get('system.log_level') == 'DEBUG'
        assert mock_config_service.get('llm.temperature') == 0.9
        
        # Verify database was called
        database_service.upsert_configuration_async.assert_called_once_with("system_config", sample_update_config)

    @pytest.mark.asyncio
    async def test_configuration_update_database_failure(self, mock_config_service, database_service, sample_update_config, mocker):
        """Test configuration update when database fails."""
        # Setup ConfigService
        mock_config_service._database_service = database_service
        mock_config_service._initialized = True
        mock_config_service._config = {"system": {"log_level": "INFO"}, "llm": {"temperature": 0.7}}
        
        # Mock database failure
        database_service.upsert_configuration_async = AsyncMock(return_value=False)
        
        # Mock logger
        mock_logger = mocker.patch('nexus.services.config.logger')
        
        # Update configuration through ConfigService
        result = await mock_config_service.update_configuration_async(sample_update_config)
        
        # Verify update failed
        assert result is False
        
        # Verify local cache was not updated
        assert mock_config_service.get('system.log_level') == 'INFO'
        assert mock_config_service.get('llm.temperature') == 0.7
        
        # Verify database was called
        database_service.upsert_configuration_async.assert_called_once_with("system_config", sample_update_config)

    # Deep Merge Integration Tests
    def test_deep_merge_integration(self, mock_config_service, database_service, mocker):
        """Test that deep merge works correctly across the integration."""
        # Create a complex database config that should merge with defaults
        complex_db_config = {
            "system": {
                "environment": "production",
                "custom_setting": "custom_value"
            },
            "llm": {
                "providers": {
                    "google": {
                        "model": "gemini-2.0-flash",
                        "api_key": "test_key"
                    },
                    "openrouter": {
                        "model": "custom-model"
                    }
                }
            },
            "new_section": {
                "new_key": "new_value"
            }
        }
        
        # Mock database response
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = complex_db_config
        mocker.patch('asyncio.get_event_loop', return_value=mock_loop)
        
        # Initialize ConfigService
        mock_config_service.initialize(database_service)
        
        # Verify deep merge worked correctly
        # Default values preserved
        assert mock_config_service.get('system.name') == 'NEXUS'
        assert mock_config_service.get('system.version') == '1.0.0'
        
        # Database values override defaults
        assert mock_config_service.get('system.environment') == 'production'
        assert mock_config_service.get('llm.providers.google.model') == 'gemini-2.0-flash'
        assert mock_config_service.get('llm.providers.google.api_key') == 'test_key'
        
        # New sections from database are added
        assert mock_config_service.get('new_section.new_key') == 'new_value'
        
        # Nested providers merge correctly
        assert mock_config_service.get('llm.providers.openrouter.model') == 'custom-model'
        # Default openrouter api_key should be preserved (None)
        assert mock_config_service.get('llm.providers.openrouter.api_key') is None

    # Test Database Name Override Integration
    def test_test_database_name_override_integration(self, mock_config_service, database_service, mocker):
        """Test test database name override works in integration."""
        # Mock environment variable
        mocker.patch.dict({'NEXUS_TEST_DB_NAME': 'test_integration_db'})
        
        # Mock database response
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = {"system": {"log_level": "DEBUG"}}
        mocker.patch('asyncio.get_event_loop', return_value=mock_loop)
        
        # Mock logger
        mock_logger = mocker.patch('nexus.services.config.logger')
        
        # Initialize ConfigService
        mock_config_service.initialize(database_service)
        
        # Verify database name was overridden
        assert mock_config_service.get('database.db_name') == 'test_integration_db'
        
        # Verify warning was logged
        mock_logger.warning.assert_called_with("Overriding database.db_name for testing: test_integration_db")

    # Error Handling Integration Tests
    def test_database_connection_error_handling(self, mock_config_service, database_service, mocker):
        """Test error handling when database connection fails during initialization."""
        # Mock database connection error
        mock_loop = Mock()
        mock_loop.run_until_complete.side_effect = ConnectionFailure("Connection failed")
        mocker.patch('asyncio.get_event_loop', return_value=mock_loop)
        
        # Mock logger
        mock_logger = mocker.patch('nexus.services.config.logger')
        
        # Initialize ConfigService
        mock_config_service.initialize(database_service)
        
        # Verify graceful fallback to defaults
        assert mock_config_service.is_initialized() is True
        assert mock_config_service.get('system.name') == 'NEXUS'
        assert mock_config_service.get('system.version') == '1.0.0'
        
        # Verify appropriate warning was logged
        mock_logger.warning.assert_called()
        warning_calls = [call for call in mock_logger.warning.call_args_list]
        assert any("Unable to load configuration from database" in str(call) for call in warning_calls)

    # Performance Integration Tests
    @pytest.mark.asyncio
    async def test_concurrent_configuration_access(self, mock_config_service, database_service, sample_update_config):
        """Test concurrent configuration access through the integration."""
        # Setup ConfigService
        mock_config_service._database_service = database_service
        mock_config_service._initialized = True
        mock_config_service._config = {"system": {"log_level": "INFO"}, "llm": {"temperature": 0.7}}
        
        # Mock database service async method
        database_service.upsert_configuration_async = AsyncMock(return_value=True)
        
        # Create multiple concurrent update tasks
        tasks = []
        for i in range(10):
            update_data = {
                "system": {"log_level": f"DEBUG_{i}"},
                "llm": {"temperature": 0.1 * i}
            }
            tasks.append(mock_config_service.update_configuration_async(update_data))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all tasks completed successfully
        assert len(results) == 10
        for result in results:
            assert not isinstance(result, Exception)
            assert result is True
        
        # Verify database was called multiple times
        assert database_service.upsert_configuration_async.call_count == 10

    # Configuration Consistency Tests
    def test_configuration_consistency_across_services(self, mock_config_service, database_service, sample_database_config, mocker):
        """Test that configuration remains consistent across services."""
        # Mock database response
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = sample_database_config
        mocker.patch('asyncio.get_event_loop', return_value=mock_loop)
        
        # Initialize ConfigService
        mock_config_service.initialize(database_service)
        
        # Verify configuration consistency
        config_from_service = mock_config_service.get_all()
        
        # Verify that all expected keys are present
        assert "system" in config_from_service
        assert "database" in config_from_service
        assert "llm" in config_from_service
        assert "websocket" in config_from_service
        assert "services" in config_from_service
        
        # Verify database overrides are applied
        assert config_from_service["system"]["name"] == "NEXUS-Production"
        assert config_from_service["system"]["environment"] == "production"
        assert config_from_service["llm"]["temperature"] == 0.3
        
        # Verify defaults are preserved
        assert config_from_service["system"]["version"] == "1.0.0"
        assert config_from_service["llm"]["default_provider"] == "google"
        
        # Verify configuration is immutable (returns copy)
        config_copy = mock_config_service.get_all()
        assert config_copy is not config_from_service
        assert config_copy == config_from_service

    # Migration Integration Tests
    def test_migration_integration_workflow(self, mock_config_service, database_service, sample_database_config, mocker):
        """Test migration workflow integration."""
        # Mock database response (simulating post-migration state)
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = sample_database_config
        mocker.patch('asyncio.get_event_loop', return_value=mock_loop)
        
        # Initialize ConfigService (simulating post-migration startup)
        mock_config_service.initialize(database_service)
        
        # Verify migrated configuration is loaded correctly
        assert mock_config_service.is_initialized() is True
        assert mock_config_service.get('system.name') == 'NEXUS-Production'
        assert mock_config_service.get('system.environment') == 'production'
        assert mock_config_service.get('llm.temperature') == 0.3
        
        # Verify that the configuration can be updated (post-migration operations)
        mock_config_service._config = mock_config_service._config.copy()
        assert mock_config_service.get('database.max_pool_size') == 20