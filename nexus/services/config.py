"""
Configuration service for NEXUS.

This service manages all configuration loading from database with environment awareness.
It provides a unified interface for accessing configuration values throughout the system
with fallback to minimal hardcoded defaults for resilience. The authoritative source for
all configuration is the 'configurations' collection in the database, which should be
initialized using scripts/database_manager.py.

Key features:
- Database-driven configuration management (development/production environments)
- Dot-notation access to nested configuration values (e.g., 'llm.providers.google.api_key')
- Environment variable substitution in configuration values (e.g., '${GEMINI_API_KEY}')
- Type-safe getters (get_bool, get_int, get_float)
- LLM catalog and provider configuration management
- User defaults for personalization (config and prompts)
- Async configuration updates through database service
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class ConfigService:
    """
    Database-driven configuration service for NEXUS.

    Loads configuration from database based on environment, with fallback to
    hardcoded defaults for resilience. Provides dot-notation access to
    configuration values.
    """

    def __init__(self, database_service):
        """Initialize the configuration service.

        Args:
            database_service: DatabaseService instance for config loading
        """
        self._config: dict[str, Any] = {}
        self._environment: str = "development"
        self._initialized: bool = False
        self._database_service = database_service
        logger.info("ConfigService initialized")

    async def initialize(self, environment: str = "development") -> None:
        """
        Load and parse configuration from database with fallback to hardcoded defaults.

        Args:
            environment: Target environment (development or production)

        This method should be called once during application startup.
        """
        try:
            self._environment = environment
            logger.info(
                f"Initializing ConfigService for environment: {self._environment}"
            )

            # Try to load configuration from database first
            try:
                db_config = await self._database_service.get_configuration_async(
                    self._environment
                )
                if db_config:
                    self._config = db_config
                    logger.info(
                        f"Configuration loaded from database for environment: {self._environment}"
                    )
                else:
                    logger.warning(
                        f"No configuration found in database for environment: {self._environment}"
                    )
                    self._load_minimal_default_config()
                    logger.info("Using minimal default configuration")
            except Exception as e:
                logger.error(f"Failed to load configuration from database: {e}")
                self._load_minimal_default_config()
                logger.info("Using minimal default configuration as fallback")

            self._initialized = True
            logger.info("ConfigService initialization completed")

        except Exception as e:
            logger.error(f"Failed to initialize ConfigService: {e}")
            raise

    def _load_minimal_default_config(self) -> None:
        """Load minimal hardcoded default configuration as emergency fallback.

        This configuration is intentionally minimal and should ONLY be used when
        database configuration loading fails. The authoritative source for all
        default values is the 'configurations' collection in the database, which
        should be initialized using scripts/init_configurations.py.
        """
        logger.warning(
            "Loading minimal emergency fallback configuration. "
            "Please ensure database is initialized with scripts/init_configurations.py"
        )

        # Environment-specific database name
        db_name = f"NEXUS_DB_{'DEV' if self._environment == 'development' else 'PROD'}"

        # Absolute minimum configuration to prevent system crash
        # Note: This will NOT provide full functionality - database initialization is required
        self._config = {
            "system": {"log_level": "INFO", "max_tool_iterations": 5},
            "database": {"mongo_uri": "${MONGO_URI}", "db_name": db_name},
            "llm": {
                "providers": {
                    "google": {
                        "api_key": "${GEMINI_API_KEY}",
                        "base_url": "https://generativelanguage.googleapis.com/v1beta",
                    }
                },
                "catalog": {
                    "gemini-2.5-flash": {"provider": "google", "id": "gemini-2.5-flash"}
                },
            },
            "user_defaults": {
                "config": {
                    "model": "gemini-2.5-flash",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
                "prompts": {},
            },
        }

    def _substitute_env_vars(self, value: Any) -> Any:
        """Recursively substitute environment variables in configuration values."""
        if isinstance(value, dict):
            return {k: self._substitute_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._substitute_env_vars(item) for item in value]
        elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            var_name = value[2:-1]
            return os.getenv(var_name, value)
        else:
            return value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key: Dot-separated key path (e.g., 'llm.providers.google.model')
            default: Default value if key is not found

        Returns:
            The configuration value or default (with environment variables substituted)
        """
        if not self._initialized:
            raise RuntimeError(
                "ConfigService not initialized. Call initialize() first."
            )

        keys = key.split(".")
        current = self._config

        try:
            for k in keys:
                current = current[k]
            # Substitute environment variables in the returned value
            return self._substitute_env_vars(current)
        except (KeyError, TypeError):
            logger.debug(
                f"Configuration key '{key}' not found, returning default: {default}"
            )
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get a boolean configuration value.

        Args:
            key: Dot-separated key path
            default: Default boolean value

        Returns:
            Boolean value
        """
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    def get_int(self, key: str, default: int = 0) -> int:
        """
        Get an integer configuration value.

        Args:
            key: Dot-separated key path
            default: Default integer value

        Returns:
            Integer value
        """
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(
                f"Could not convert '{value}' to int for key '{key}', returning default: {default}"
            )
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        Get a float configuration value.

        Args:
            key: Dot-separated key path
            default: Default float value

        Returns:
            Float value
        """
        value = self.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(
                f"Could not convert '{value}' to float for key '{key}', returning default: {default}"
            )
            return default

    def get_all(self) -> dict[str, Any]:
        """
        Get the entire configuration dictionary.

        Returns:
            Complete configuration dictionary (deep copy)
        """
        if not self._initialized:
            raise RuntimeError(
                "ConfigService not initialized. Call initialize() first."
            )
        import copy

        return copy.deepcopy(self._config)

    def get_genesis_template(self) -> dict[str, Any]:
        """
        Return the complete genesis template configuration.

        This exposes the full, environment-resolved configuration document
        loaded from the `configurations` collection to downstream services
        for inheritance-and-override composition.
        """
        if not self._initialized:
            raise RuntimeError(
                "ConfigService not initialized. Call initialize() first."
            )
        import copy

        return copy.deepcopy(self._config)

    def get_environment(self) -> str:
        """
        Get the current environment.

        Returns:
            Current environment name
        """
        if not self._initialized:
            raise RuntimeError(
                "ConfigService not initialized. Call initialize() first."
            )
        return self._environment

    def is_initialized(self) -> bool:
        """
        Check if the configuration service has been initialized.

        Returns:
            True if initialized, False otherwise
        """
        return self._initialized

    def get_llm_catalog(self) -> dict[str, Any]:
        """
        Get the LLM model catalog (model name -> provider mapping).

        Returns:
            Dictionary mapping model names to their provider information
        """
        result = self.get("llm.catalog", {})
        return result if isinstance(result, dict) else {}

    def get_model_resolution(self) -> dict[str, Any]:
        """Return structure used to resolve friendly model aliases to provider IDs.

        Expected structure inside catalog entries (optional):
        - aliases: ["Kimi-K2", "Kimi-Free"] etc.
        - id: provider-specific model id (if different from catalog key)
        """
        result = self.get("llm.catalog", {})
        return result if isinstance(result, dict) else {}

    def get_user_defaults(self) -> dict[str, Any]:
        """
        Get user default configuration (including config and prompts).

        Returns:
            Dictionary containing default config and prompts
        """
        result = self.get("user_defaults", {})
        return result if isinstance(result, dict) else {}

    def get_provider_config(self, provider_name: str) -> dict[str, Any]:
        """
        Get configuration for a specific LLM provider.

        Args:
            provider_name: Name of the provider (e.g., 'google', 'deepseek')

        Returns:
            Dictionary containing provider configuration
        """
        result = self.get(f"llm.providers.{provider_name}", {})
        return result if isinstance(result, dict) else {}

    async def update_configuration(self, config_data: dict[str, Any]) -> bool:
        """
        Update configuration in database for current environment.

        Args:
            config_data: New configuration data to store

        Returns:
            True if update was successful, False otherwise
        """
        if not self._database_service:
            logger.error("No database service available for configuration update")
            return False

        try:
            success = await self._database_service.upsert_configuration_async(
                self._environment, config_data
            )
            result: bool = bool(success) if success else False
            if result:
                self._config = config_data
                logger.info(
                    f"Configuration updated successfully for environment: {self._environment}"
                )
            return result
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            return False
