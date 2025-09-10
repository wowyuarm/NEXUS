"""Integration tests for full configuration flow."""

import os
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from nexus.services.config import ConfigService
from nexus.services.database.service import DatabaseService
from nexus.services.database.providers.mongo import MongoProvider
from nexus.core.bus import NexusBus


class TestFullConfigurationFlow:
    """Integration tests for the complete configuration flow."""

    @pytest.fixture
    def mock_bus(self):
        """Fixture providing a mock NexusBus."""
        return MagicMock(spec=NexusBus)

    @pytest.fixture
    def mock_mongo_provider(self):
        """Fixture providing a mock MongoProvider."""
        mock_provider = MagicMock(spec=MongoProvider)
        mock_provider.get_configuration = MagicMock()
        mock_provider.upsert_configuration = MagicMock()
        mock_provider.connect = MagicMock()
        mock_provider.disconnect = MagicMock()
        return mock_provider

    @pytest.fixture
    def sample_configs(self):
        """Sample configurations for different environments."""
        return {
            "development": {
                "server": {
                    "host": "127.0.0.1",
                    "port": 8000
                },
                "database": {
                    "mongo_uri": "mongodb://localhost:27017",
                    "db_name": "NEXUS_DB_DEV"
                },
                "system": {
                    "log_level": "INFO",
                    "max_tokens": 4000
                }
            },
            "production": {
                "server": {
                    "host": "0.0.0.0",
                    "port": 8000
                },
                "database": {
                    "mongo_uri": "mongodb://prod.example.com:27017",
                    "db_name": "NEXUS_DB_PROD"
                },
                "system": {
                    "log_level": "WARNING",
                    "max_tokens": 4000
                }
            }
        }

    @pytest.mark.asyncio
    async def test_full_configuration_flow_development(self, mock_bus, mock_mongo_provider, sample_configs):
        """Test complete configuration flow for development environment."""
        # Setup temporary config for database initialization
        temp_config = ConfigService()
        await temp_config.initialize()
        
        # Setup database service with mocked provider
        database_service = DatabaseService(mock_bus, temp_config)
        database_service.provider = mock_mongo_provider
        
        # Setup provider to return development config
        mock_mongo_provider.get_configuration.return_value = sample_configs["development"]
        
        # Create main config service with database service
        config_service = ConfigService(database_service)
        
        # Test initialization with development environment
        with patch.dict(os.environ, {"NEXUS_ENV": "development"}):
            await config_service.initialize()
            
            # Verify the flow worked correctly
            assert config_service.is_initialized() is True
            assert config_service.get_environment() == "development"
            
            # Verify database was queried
            mock_mongo_provider.get_configuration.assert_called_once_with("development")
            
            # Verify configuration values
            assert config_service.get("server.host") == "127.0.0.1"
            assert config_service.get("database.db_name") == "NEXUS_DB_DEV"
            assert config_service.get("system.log_level") == "INFO"

    @pytest.mark.asyncio
    async def test_full_configuration_flow_production(self, mock_bus, mock_mongo_provider, sample_configs):
        """Test complete configuration flow for production environment."""
        # Setup temporary config for database initialization
        temp_config = ConfigService()
        await temp_config.initialize()
        
        # Setup database service with mocked provider
        database_service = DatabaseService(mock_bus, temp_config)
        database_service.provider = mock_mongo_provider
        
        # Setup provider to return production config
        mock_mongo_provider.get_configuration.return_value = sample_configs["production"]
        
        # Create main config service with database service
        config_service = ConfigService(database_service)
        
        # Test initialization with production environment
        with patch.dict(os.environ, {"NEXUS_ENV": "production"}):
            await config_service.initialize()
            
            # Verify the flow worked correctly
            assert config_service.is_initialized() is True
            assert config_service.get_environment() == "production"
            
            # Verify database was queried
            mock_mongo_provider.get_configuration.assert_called_once_with("production")
            
            # Verify configuration values
            assert config_service.get("server.host") == "0.0.0.0"
            assert config_service.get("database.db_name") == "NEXUS_DB_PROD"
            assert config_service.get("system.log_level") == "WARNING"

    @pytest.mark.asyncio
    async def test_configuration_update_flow(self, mock_bus, mock_mongo_provider, sample_configs):
        """Test configuration update flow through the complete system."""
        # Setup temporary config for database initialization
        temp_config = ConfigService()
        await temp_config.initialize()
        
        # Setup database service with mocked provider
        database_service = DatabaseService(mock_bus, temp_config)
        database_service.provider = mock_mongo_provider
        
        # Setup provider to return initial config and accept updates
        mock_mongo_provider.get_configuration.return_value = sample_configs["development"]
        mock_mongo_provider.upsert_configuration.return_value = True
        
        # Create main config service with database service
        config_service = ConfigService(database_service)
        
        with patch.dict(os.environ, {"NEXUS_ENV": "development"}):
            # Initialize with original config
            await config_service.initialize()
            
            # Verify original values
            assert config_service.get("server.host") == "127.0.0.1"
            assert config_service.get("system.max_tokens") == 4000
            
            # Update configuration
            new_config = {
                "server": {
                    "host": "192.168.1.100",
                    "port": 9000
                },
                "system": {
                    "log_level": "DEBUG",
                    "max_tokens": 8000
                }
            }
            
            result = await config_service.update_configuration(new_config)
            
            # Verify update was successful
            assert result is True
            mock_mongo_provider.upsert_configuration.assert_called_once_with("development", new_config)
            
            # Verify values were updated
            assert config_service.get("server.host") == "192.168.1.100"
            assert config_service.get("server.port") == 9000
            assert config_service.get("system.log_level") == "DEBUG"
            assert config_service.get("system.max_tokens") == 8000

    @pytest.mark.asyncio
    async def test_database_failure_fallback_flow(self, mock_bus, mock_mongo_provider):
        """Test fallback to default configuration when database fails."""
        # Setup temporary config for database initialization
        temp_config = ConfigService()
        await temp_config.initialize()
        
        # Setup database service with mocked provider that fails
        database_service = DatabaseService(mock_bus, temp_config)
        database_service.provider = mock_mongo_provider
        mock_mongo_provider.get_configuration.side_effect = Exception("Database connection failed")
        
        # Create main config service with database service
        config_service = ConfigService(database_service)
        
        with patch.dict(os.environ, {"NEXUS_ENV": "development"}):
            # Initialize should fallback to default config
            await config_service.initialize()
            
            # Verify fallback worked
            assert config_service.is_initialized() is True
            assert config_service.get_environment() == "development"
            
            # Verify default values are present
            assert config_service.get("server.host") == "127.0.0.1"
            assert config_service.get("server.port") == 8000
            assert config_service.get("database.db_name") == "NEXUS_DB_DEV"

    @pytest.mark.asyncio
    async def test_no_database_service_flow(self):
        """Test configuration flow without database service."""
        # Create config service without database
        config_service = ConfigService(database_service=None)
        
        with patch.dict(os.environ, {"NEXUS_ENV": "production"}):
            # Initialize should use default config
            await config_service.initialize()
            
            # Verify default config was loaded
            assert config_service.is_initialized() is True
            assert config_service.get_environment() == "production"
            
            # Verify production defaults
            assert config_service.get("server.host") == "0.0.0.0"
            assert config_service.get("database.db_name") == "NEXUS_DB_PROD"
            assert config_service.get("system.log_level") == "WARNING"

    @pytest.mark.asyncio
    async def test_environment_switching_flow(self, mock_bus, mock_mongo_provider, sample_configs):
        """Test switching between different environments."""
        # Setup provider to return different configs for different environments
        def mock_get_config(environment):
            return sample_configs.get(environment)
        
        mock_mongo_provider.get_configuration.side_effect = mock_get_config
        mock_mongo_provider.upsert_configuration.return_value = True
        
        # Test development environment
        with patch.dict(os.environ, {"NEXUS_ENV": "development"}):
            # Setup services
            temp_config = ConfigService()
            await temp_config.initialize()
            
            database_service = DatabaseService(mock_bus, temp_config)
            database_service.provider = mock_mongo_provider
            
            config_service = ConfigService(database_service)
            await config_service.initialize()
            
            # Verify development config
            assert config_service.get_environment() == "development"
            assert config_service.get("server.host") == "127.0.0.1"
        
        # Test production environment (new service instance)
        with patch.dict(os.environ, {"NEXUS_ENV": "production"}):
            temp_config = ConfigService()
            await temp_config.initialize()
            
            database_service = DatabaseService(mock_bus, temp_config)
            database_service.provider = mock_mongo_provider
            
            config_service = ConfigService(database_service)
            await config_service.initialize()
            
            # Verify production config
            assert config_service.get_environment() == "production"
            assert config_service.get("server.host") == "0.0.0.0"
        
        # Verify both environments were queried
        expected_calls = [
            ("development",),
            ("production",)
        ]
        actual_calls = [call[0] for call in mock_mongo_provider.get_configuration.call_args_list]
        assert actual_calls == expected_calls

    @pytest.mark.asyncio
    async def test_configuration_data_validation_flow(self, mock_bus, mock_mongo_provider):
        """Test that configuration data is properly validated and handled."""
        # Setup temporary config for database initialization
        temp_config = ConfigService()
        await temp_config.initialize()
        
        # Setup database service with mocked provider
        database_service = DatabaseService(mock_bus, temp_config)
        database_service.provider = mock_mongo_provider
        
        # Test with various configuration structures
        test_configs = [
            # Minimal valid config
            {"server": {"host": "localhost", "port": 8000}},
            # Complex nested config
            {
                "server": {"host": "localhost", "port": 8000},
                "features": {
                    "auth": {"enabled": True, "providers": ["google", "github"]},
                    "logging": {"level": "INFO", "files": ["app.log", "error.log"]}
                },
                "integrations": [
                    {"name": "slack", "enabled": False},
                    {"name": "discord", "enabled": True}
                ]
            },
            # Empty config
            {}
        ]
        
        for i, test_config in enumerate(test_configs):
            # Setup provider to return test config
            mock_mongo_provider.get_configuration.return_value = test_config
            mock_mongo_provider.upsert_configuration.return_value = True
            
            # Create and initialize config service
            config_service = ConfigService(database_service)
            await config_service.initialize()
            
            # Verify config was loaded correctly
            assert config_service.is_initialized() is True
            
            # Verify we can retrieve the config
            retrieved_config = config_service.get_all()
            assert retrieved_config == test_config
            
            # Test update with same config
            update_result = await config_service.update_configuration(test_config)
            assert update_result is True

    @pytest.mark.asyncio
    async def test_concurrent_configuration_access(self, mock_bus, mock_mongo_provider, sample_configs):
        """Test concurrent access to configuration methods."""
        # Setup temporary config for database initialization
        temp_config = ConfigService()
        await temp_config.initialize()
        
        # Setup database service with mocked provider
        database_service = DatabaseService(mock_bus, temp_config)
        database_service.provider = mock_mongo_provider
        mock_mongo_provider.get_configuration.return_value = sample_configs["development"]
        mock_mongo_provider.upsert_configuration.return_value = True
        
        # Create config service
        config_service = ConfigService(database_service)
        await config_service.initialize()
        
        # Test concurrent reads
        async def read_config():
            return config_service.get("server.host")
        
        # Test concurrent writes
        async def update_config(value):
            new_config = {"server": {"host": value}}
            return await config_service.update_configuration(new_config)
        
        # Run concurrent operations
        read_tasks = [read_config() for _ in range(10)]
        update_tasks = [update_config(f"host_{i}") for i in range(5)]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*read_tasks, *update_tasks, return_exceptions=True)
        
        # Verify no exceptions occurred
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Concurrent operations failed: {exceptions}"