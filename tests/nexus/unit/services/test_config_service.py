"""
Unit tests for ConfigService.

These tests verify that ConfigService correctly handles configuration loading
from database with fallback to hardcoded defaults. All external dependencies
are mocked to ensure isolation and test the "database-first, code fallback" logic.
"""

import pytest
from unittest.mock import Mock, AsyncMock
import logging

from nexus.services.config import ConfigService


class TestConfigService:
    """Test suite for ConfigService class."""

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock database service for testing."""
        mock_db = Mock()
        mock_db.get_configuration_async = AsyncMock()
        mock_db.upsert_configuration_async = AsyncMock()
        return mock_db

    @pytest.fixture
    def config_service(self, mock_database_service):
        """Create a ConfigService instance with mocked dependencies."""
        return ConfigService(database_service=mock_database_service)

    @pytest.mark.asyncio
    async def test_initialize_loads_from_db_successfully(
        self, config_service, mock_database_service
    ):
        """Test that ConfigService loads configuration from database successfully."""
        # Arrange: Mock database service to return configuration
        expected_config = {
            "server": {"host": "0.0.0.0", "port": 9000},
            "database": {
                "mongo_uri": "mongodb://test:27017",
                "db_name": "NEXUS_DB_TEST",
            },
            "llm": {"provider": "openrouter", "temperature": 0.5, "max_tokens": 8000},
        }
        mock_database_service.get_configuration_async.return_value = expected_config

        # Act: Initialize ConfigService with development environment
        await config_service.initialize("development")

        # Assert: Verify configuration was loaded from database
        assert config_service.is_initialized()
        assert config_service.get_environment() == "development"
        assert config_service.get("server.host") == "0.0.0.0"
        assert config_service.get("server.port") == 9000
        assert config_service.get("database.mongo_uri") == "mongodb://test:27017"
        assert config_service.get("llm.provider") == "openrouter"
        assert config_service.get("llm.temperature") == 0.5

        # Verify database service was called with correct environment
        mock_database_service.get_configuration_async.assert_called_once_with(
            "development"
        )

    @pytest.mark.asyncio
    async def test_initialize_falls_back_to_defaults_on_db_failure(
        self, config_service, mock_database_service, caplog
    ):
        """Test that ConfigService falls back to defaults when database fails."""
        # Arrange: Mock database service to raise an exception
        mock_database_service.get_configuration_async.side_effect = Exception(
            "Database connection failed"
        )

        # Act: Initialize ConfigService with development environment
        with caplog.at_level(logging.INFO):
            await config_service.initialize("development")

        # Assert: Verify fallback to minimal emergency configuration
        assert config_service.is_initialized()
        assert config_service.get_environment() == "development"

        # Verify minimal emergency configuration values are loaded
        assert config_service.get("database.db_name") == "NEXUS_DB_DEV"
        assert config_service.get("system.log_level") == "INFO"
        assert config_service.get("system.max_tool_iterations") == 5
        assert config_service.get("user_defaults.config.model") == "gemini-2.5-flash"
        assert config_service.get("user_defaults.config.temperature") == 0.7
        assert config_service.get("user_defaults.config.max_tokens") == 4096
        # Catalog key contains hyphen, must access via dict
        catalog = config_service.get("llm.catalog")
        assert catalog is not None
        assert "gemini-2.5-flash" in catalog
        assert catalog["gemini-2.5-flash"]["provider"] == "google"
        # Note: api_key will be environment-variable-substituted, so just verify it's not None
        api_key = config_service.get("llm.providers.google.api_key")
        assert api_key is not None

        # Verify error was logged
        assert "Failed to load configuration from database" in caplog.text
        assert "minimal emergency fallback configuration" in caplog.text

    @pytest.mark.asyncio
    async def test_initialize_falls_back_to_defaults_on_empty_db_config(
        self, config_service, mock_database_service, caplog
    ):
        """Test that ConfigService falls back to defaults when database returns None/empty config."""
        # Arrange: Mock database service to return None
        mock_database_service.get_configuration_async.return_value = None

        # Act: Initialize ConfigService
        with caplog.at_level(logging.WARNING):
            await config_service.initialize("production")

        # Assert: Verify fallback to minimal emergency configuration
        assert config_service.is_initialized()
        assert config_service.get_environment() == "production"

        # Verify production-specific database name
        assert config_service.get("database.db_name") == "NEXUS_DB_PROD"

        # Verify warning was logged
        assert (
            "No configuration found in database for environment: production"
            in caplog.text
        )
        assert "minimal emergency fallback configuration" in caplog.text

    def test_get_configuration_before_initialization_raises_error(self, config_service):
        """Test that accessing configuration before initialization raises RuntimeError."""
        # Act & Assert: Verify RuntimeError is raised
        with pytest.raises(RuntimeError, match="ConfigService not initialized"):
            config_service.get("server.host")

        with pytest.raises(RuntimeError, match="ConfigService not initialized"):
            config_service.get_environment()

        with pytest.raises(RuntimeError, match="ConfigService not initialized"):
            config_service.get_all()

    @pytest.mark.asyncio
    async def test_get_with_dot_notation_and_defaults(
        self, config_service, mock_database_service
    ):
        """Test dot notation access and default value handling."""
        # Arrange: Mock database with partial configuration
        partial_config = {
            "server": {
                "host": "localhost"
                # port is missing
            }
        }
        mock_database_service.get_configuration_async.return_value = partial_config
        await config_service.initialize("development")

        # Act & Assert: Test existing keys
        assert config_service.get("server.host") == "localhost"

        # Test missing keys with defaults
        assert config_service.get("server.port", 3000) == 3000
        assert config_service.get("nonexistent.key", "default_value") == "default_value"
        assert config_service.get("deeply.nested.missing.key") is None

    @pytest.mark.asyncio
    async def test_get_bool_conversion(self, config_service, mock_database_service):
        """Test boolean value conversion from configuration."""
        # Arrange: Mock database with various boolean representations
        config_with_bools = {
            "flags": {
                "bool_true": True,
                "bool_false": False,
                "string_true": "true",
                "string_false": "false",
                "string_yes": "yes",
                "string_no": "no",
                "string_1": "1",
                "string_0": "0",
                "number_1": 1,
                "number_0": 0,
            }
        }
        mock_database_service.get_configuration_async.return_value = config_with_bools
        await config_service.initialize("development")

        # Act & Assert: Test boolean conversions
        assert config_service.get_bool("flags.bool_true") is True
        assert config_service.get_bool("flags.bool_false") is False
        assert config_service.get_bool("flags.string_true") is True
        assert config_service.get_bool("flags.string_false") is False
        assert config_service.get_bool("flags.string_yes") is True
        assert config_service.get_bool("flags.string_no") is False
        assert config_service.get_bool("flags.string_1") is True
        assert config_service.get_bool("flags.string_0") is False
        assert config_service.get_bool("flags.number_1") is True
        assert config_service.get_bool("flags.number_0") is False

        # Test missing key with default
        assert config_service.get_bool("missing.key", True) is True

    @pytest.mark.asyncio
    async def test_get_int_conversion(
        self, config_service, mock_database_service, caplog
    ):
        """Test integer value conversion from configuration."""
        # Arrange: Mock database with various numeric representations
        config_with_numbers = {
            "numbers": {
                "valid_int": 42,
                "string_int": "123",
                "invalid_string": "not_a_number",
                "float_value": 3.14,
            }
        }
        mock_database_service.get_configuration_async.return_value = config_with_numbers
        await config_service.initialize("development")

        # Act & Assert: Test integer conversions
        assert config_service.get_int("numbers.valid_int") == 42
        assert config_service.get_int("numbers.string_int") == 123
        assert config_service.get_int("numbers.float_value") == 3  # Truncated

        # Test invalid conversion with warning
        with caplog.at_level(logging.WARNING):
            result = config_service.get_int("numbers.invalid_string", 999)
            assert result == 999
            assert "Could not convert 'not_a_number' to int" in caplog.text

    @pytest.mark.asyncio
    async def test_get_float_conversion(
        self, config_service, mock_database_service, caplog
    ):
        """Test float value conversion from configuration."""
        # Arrange: Mock database with various numeric representations
        config_with_floats = {
            "floats": {
                "valid_float": 3.14,
                "string_float": "2.71",
                "int_value": 42,
                "invalid_string": "not_a_float",
            }
        }
        mock_database_service.get_configuration_async.return_value = config_with_floats
        await config_service.initialize("development")

        # Act & Assert: Test float conversions
        assert config_service.get_float("floats.valid_float") == 3.14
        assert config_service.get_float("floats.string_float") == 2.71
        assert config_service.get_float("floats.int_value") == 42.0

        # Test invalid conversion with warning
        with caplog.at_level(logging.WARNING):
            result = config_service.get_float("floats.invalid_string", 1.23)
            assert result == 1.23
            assert "Could not convert 'not_a_float' to float" in caplog.text

    @pytest.mark.asyncio
    async def test_environment_variable_substitution(
        self, config_service, mock_database_service, mocker
    ):
        """Test environment variable substitution in configuration values."""
        # Arrange: Mock environment variables
        mocker.patch.dict(
            "os.environ",
            {"TEST_API_KEY": "secret_key_123", "TEST_URL": "https://api.example.com"},
        )

        config_with_env_vars = {
            "api": {
                "key": "${TEST_API_KEY}",
                "url": "${TEST_URL}",
                "missing_var": "${MISSING_VAR}",
                "regular_value": "no_substitution",
            }
        }
        mock_database_service.get_configuration_async.return_value = (
            config_with_env_vars
        )
        await config_service.initialize("development")

        # Act & Assert: Test environment variable substitution
        assert config_service.get("api.key") == "secret_key_123"
        assert config_service.get("api.url") == "https://api.example.com"
        assert (
            config_service.get("api.missing_var") == "${MISSING_VAR}"
        )  # Unchanged if env var doesn't exist
        assert config_service.get("api.regular_value") == "no_substitution"

    @pytest.mark.asyncio
    async def test_update_configuration_success(
        self, config_service, mock_database_service
    ):
        """Test successful configuration update."""
        # Arrange: Initialize service first
        initial_config = {"server": {"host": "localhost", "port": 8000}}
        mock_database_service.get_configuration_async.return_value = initial_config
        await config_service.initialize("development")

        # Mock successful update
        mock_database_service.upsert_configuration_async.return_value = True

        new_config = {"server": {"host": "0.0.0.0", "port": 9000}}

        # Act: Update configuration
        result = await config_service.update_configuration(new_config)

        # Assert: Verify update was successful
        assert result is True
        assert config_service.get("server.host") == "0.0.0.0"
        assert config_service.get("server.port") == 9000

        # Verify database service was called correctly
        mock_database_service.upsert_configuration_async.assert_called_once_with(
            "development", new_config
        )

    @pytest.mark.asyncio
    async def test_update_configuration_failure(
        self, config_service, mock_database_service, caplog
    ):
        """Test configuration update failure handling."""
        # Arrange: Initialize service first
        initial_config = {"server": {"host": "localhost"}}
        mock_database_service.get_configuration_async.return_value = initial_config
        await config_service.initialize("development")

        # Mock failed update
        mock_database_service.upsert_configuration_async.side_effect = Exception(
            "Database error"
        )

        new_config = {"server": {"host": "0.0.0.0"}}

        # Act: Attempt to update configuration
        with caplog.at_level(logging.ERROR):
            result = await config_service.update_configuration(new_config)

        # Assert: Verify update failed gracefully
        assert result is False
        assert (
            config_service.get("server.host") == "localhost"
        )  # Configuration unchanged
        assert "Failed to update configuration" in caplog.text

    @pytest.mark.asyncio
    async def test_update_configuration_no_database_service(self, caplog):
        """Test configuration update when no database service is available."""
        # Arrange: Create ConfigService without database service
        config_service = ConfigService(database_service=None)

        new_config = {"server": {"host": "0.0.0.0"}}

        # Act: Attempt to update configuration
        with caplog.at_level(logging.ERROR):
            result = await config_service.update_configuration(new_config)

        # Assert: Verify update failed gracefully
        assert result is False
        assert "No database service available for configuration update" in caplog.text

    @pytest.mark.asyncio
    async def test_get_all_returns_copy_of_config(
        self, config_service, mock_database_service
    ):
        """Test that get_all returns a copy of the configuration to prevent external modification."""
        # Arrange: Initialize with test configuration
        test_config = {
            "server": {"host": "localhost", "port": 8000},
            "database": {"name": "test_db"},
        }
        mock_database_service.get_configuration_async.return_value = test_config
        await config_service.initialize("development")

        # Act: Get all configuration
        config_copy = config_service.get_all()

        # Assert: Verify it's a copy and modifications don't affect original
        assert config_copy == test_config
        config_copy["server"]["host"] = "modified"
        assert config_service.get("server.host") == "localhost"  # Original unchanged

    @pytest.mark.asyncio
    async def test_get_llm_catalog(self, config_service, mock_database_service):
        """Test get_llm_catalog returns correct model catalog."""
        # Arrange: Mock database with llm catalog
        config_with_catalog = {
            "llm": {
                "catalog": {
                    "gemini-2.5-flash": {"provider": "google"},
                    "deepseek-chat": {"provider": "deepseek"},
                    "kimi-k2": {"provider": "openrouter"},
                }
            }
        }
        mock_database_service.get_configuration_async.return_value = config_with_catalog
        await config_service.initialize("development")

        # Act: Get LLM catalog
        catalog = config_service.get_llm_catalog()

        # Assert: Verify catalog structure
        assert isinstance(catalog, dict)
        assert len(catalog) == 3
        assert catalog["gemini-2.5-flash"]["provider"] == "google"
        assert catalog["deepseek-chat"]["provider"] == "deepseek"
        assert catalog["kimi-k2"]["provider"] == "openrouter"

    @pytest.mark.asyncio
    async def test_get_llm_catalog_empty(self, config_service, mock_database_service):
        """Test get_llm_catalog returns empty dict when catalog doesn't exist."""
        # Arrange: Mock database without catalog
        config_without_catalog = {"server": {"host": "localhost"}}
        mock_database_service.get_configuration_async.return_value = (
            config_without_catalog
        )
        await config_service.initialize("development")

        # Act: Get LLM catalog
        catalog = config_service.get_llm_catalog()

        # Assert: Verify empty dict is returned
        assert catalog == {}

    @pytest.mark.asyncio
    async def test_get_user_defaults(self, config_service, mock_database_service):
        """Test get_user_defaults returns config and prompts defaults."""
        # Arrange: Mock database with user defaults
        config_with_defaults = {
            "user_defaults": {
                "config": {"model": "gemini-2.5-flash", "temperature": 0.8},
                "prompts": {
                    "persona": "You are Xi, an AI assistant...",
                    "system": "System instructions...",
                    "tools": "Available tools...",
                },
            }
        }
        mock_database_service.get_configuration_async.return_value = (
            config_with_defaults
        )
        await config_service.initialize("development")

        # Act: Get user defaults
        user_defaults = config_service.get_user_defaults()

        # Assert: Verify user defaults structure
        assert isinstance(user_defaults, dict)
        assert "config" in user_defaults
        assert "prompts" in user_defaults
        assert user_defaults["config"]["model"] == "gemini-2.5-flash"
        assert user_defaults["config"]["temperature"] == 0.8
        assert user_defaults["prompts"]["persona"] == "You are Xi, an AI assistant..."
        assert user_defaults["prompts"]["system"] == "System instructions..."
        assert user_defaults["prompts"]["tools"] == "Available tools..."

    @pytest.mark.asyncio
    async def test_get_user_defaults_empty(self, config_service, mock_database_service):
        """Test get_user_defaults returns empty dict when defaults don't exist."""
        # Arrange: Mock database without user defaults
        config_without_defaults = {"server": {"host": "localhost"}}
        mock_database_service.get_configuration_async.return_value = (
            config_without_defaults
        )
        await config_service.initialize("development")

        # Act: Get user defaults
        user_defaults = config_service.get_user_defaults()

        # Assert: Verify empty dict is returned
        assert user_defaults == {}

    @pytest.mark.asyncio
    async def test_get_provider_config(self, config_service, mock_database_service):
        """Test get_provider_config returns correct provider configuration."""
        # Arrange: Mock database with provider configurations
        config_with_providers = {
            "llm": {
                "providers": {
                    "google": {
                        "api_key": "${GEMINI_API_KEY}",
                        "base_url": "https://generativelanguage.googleapis.com/v1beta",
                        "model": "gemini-2.5-flash",
                    },
                    "deepseek": {
                        "api_key": "${DEEPSEEK_API_KEY}",
                        "base_url": "https://api.deepseek.com",
                        "model": "deepseek-chat",
                    },
                }
            }
        }
        mock_database_service.get_configuration_async.return_value = (
            config_with_providers
        )
        await config_service.initialize("development")

        # Act: Get provider configs
        google_config = config_service.get_provider_config("google")
        deepseek_config = config_service.get_provider_config("deepseek")

        # Assert: Verify provider configurations
        # Note: api_key values may be substituted from environment variables.
        # We only assert presence and other stable fields here.
        assert isinstance(google_config, dict)
        assert isinstance(google_config.get("api_key"), str)
        assert (
            google_config["base_url"]
            == "https://generativelanguage.googleapis.com/v1beta"
        )
        assert google_config["model"] == "gemini-2.5-flash"

        assert isinstance(deepseek_config, dict)
        assert isinstance(deepseek_config.get("api_key"), str)
        assert deepseek_config["base_url"] == "https://api.deepseek.com"
        assert deepseek_config["model"] == "deepseek-chat"

    @pytest.mark.asyncio
    async def test_get_provider_config_nonexistent(
        self, config_service, mock_database_service
    ):
        """Test get_provider_config returns empty dict for nonexistent provider."""
        # Arrange: Mock database with limited providers
        config_with_providers = {"llm": {"providers": {"google": {"api_key": "test"}}}}
        mock_database_service.get_configuration_async.return_value = (
            config_with_providers
        )
        await config_service.initialize("development")

        # Act: Get nonexistent provider config
        nonexistent_config = config_service.get_provider_config("nonexistent_provider")

        # Assert: Verify empty dict is returned
        assert nonexistent_config == {}
