"""Unit tests for ConfigService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from nexus.services.config import ConfigService
from nexus.services.database.service import DatabaseService


class TestConfigService:
    """Test suite for ConfigService functionality."""

    @pytest.fixture
    def mock_database_service(self):
        """Fixture providing a mock DatabaseService."""
        mock_db = MagicMock(spec=DatabaseService)
        mock_db.get_configuration_async = AsyncMock()
        mock_db.upsert_configuration_async = AsyncMock()
        return mock_db

    @pytest.fixture
    def config_service(self, mock_database_service):
        """Fixture providing a ConfigService with mocked database."""
        return ConfigService(mock_database_service)

    @pytest.fixture
    def sample_config(self):
        """Sample configuration data for testing."""
        return {
            "server": {
                "host": "127.0.0.1",
                "port": 8000
            },
            "database": {
                "mongo_uri": "mongodb://localhost:27017",
                "db_name": "NEXUS_DB_TEST"
            },
            "llm": {
                "providers": {
                    "google": {
                        "model": "gemini-pro",
                        "api_key": "test_key"
                    }
                }
            },
            "system": {
                "log_level": "INFO",
                "max_tokens": 4000,
                "debug_mode": True
            }
        }

    @pytest.mark.asyncio
    async def test_initialize_with_database_success(self, config_service, mock_database_service, sample_config):
        """Test successful initialization with database configuration."""
        # Setup mock to return sample config
        mock_database_service.get_configuration_async.return_value = sample_config
        
        # Test initialization
        await config_service.initialize()
        
        # Verify database was called with correct environment
        mock_database_service.get_configuration_async.assert_called_once_with("development")
        
        # Verify service is initialized
        assert config_service.is_initialized() is True
        assert config_service.get_environment() == "development"
        
        # Verify configuration was loaded
        assert config_service.get("server.host") == "127.0.0.1"
        assert config_service.get("server.port") == 8000
        assert config_service.get("llm.providers.google.model") == "gemini-pro"

    @pytest.mark.asyncio
    async def test_initialize_with_production_environment(self, config_service, mock_database_service, sample_config):
        """Test initialization with production environment."""
        # Set production environment
        with patch.dict('os.environ', {"NEXUS_ENV": "production"}):
            mock_database_service.get_configuration_async.return_value = sample_config
            
            await config_service.initialize()
            
            # Verify production environment was used
            mock_database_service.get_configuration_async.assert_called_once_with("production")
            assert config_service.get_environment() == "production"

    @pytest.mark.asyncio
    async def test_initialize_database_returns_none(self, config_service, mock_database_service):
        """Test initialization when database returns None (no config found)."""
        # Setup mock to return None
        mock_database_service.get_configuration_async.return_value = None
        
        await config_service.initialize()
        
        # Verify default config was loaded
        assert config_service.is_initialized() is True
        assert config_service.get_environment() == "development"
        
        # Verify default values are present
        assert config_service.get("server.host") == "127.0.0.1"
        assert config_service.get("server.port") == 8000

    @pytest.mark.asyncio
    async def test_initialize_database_error(self, config_service, mock_database_service):
        """Test initialization when database access fails."""
        # Setup mock to raise exception
        mock_database_service.get_configuration_async.side_effect = Exception("Database connection failed")
        
        await config_service.initialize()
        
        # Verify default config was loaded as fallback
        assert config_service.is_initialized() is True
        assert config_service.get_environment() == "development"
        
        # Verify default values are present
        assert config_service.get("server.host") == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_initialize_without_database_service(self):
        """Test initialization without database service (fallback only)."""
        config_service = ConfigService(database_service=None)
        
        await config_service.initialize()
        
        # Verify default config was loaded
        assert config_service.is_initialized() is True
        assert config_service.get_environment() == "development"
        
        # Verify default values are present
        assert config_service.get("server.host") == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_get_methods_after_initialization(self, config_service, mock_database_service, sample_config):
        """Test all get methods work correctly after initialization."""
        mock_database_service.get_configuration_async.return_value = sample_config
        
        await config_service.initialize()
        
        # Test basic get
        assert config_service.get("server.host") == "127.0.0.1"
        assert config_service.get("nonexistent.key", "default") == "default"
        
        # Test get_bool
        assert config_service.get_bool("system.debug_mode") is True
        
        # Test get_int
        assert config_service.get_int("server.port") == 8000
        
        # Test get_float
        assert config_service.get_float("server.port") == 8000.0
        
        # Test get_all
        all_config = config_service.get_all()
        assert isinstance(all_config, dict)
        assert "server" in all_config

    @pytest.mark.asyncio
    async def test_get_before_initialization(self, config_service):
        """Test that get methods raise error before initialization."""
        with pytest.raises(RuntimeError, match="ConfigService not initialized"):
            config_service.get("some.key")
        
        with pytest.raises(RuntimeError, match="ConfigService not initialized"):
            config_service.get_bool("some.key")
        
        with pytest.raises(RuntimeError, match="ConfigService not initialized"):
            config_service.get_int("some.key")
        
        with pytest.raises(RuntimeError, match="ConfigService not initialized"):
            config_service.get_float("some.key")
        
        with pytest.raises(RuntimeError, match="ConfigService not initialized"):
            config_service.get_all()

    @pytest.mark.asyncio
    async def test_get_environment(self, config_service):
        """Test environment detection."""
        # Test before initialization
        with pytest.raises(RuntimeError, match="ConfigService not initialized"):
            config_service.get_environment()
        
        # Test after initialization
        await config_service.initialize()
        assert config_service.get_environment() == "development"