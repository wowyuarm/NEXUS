"""
Configuration service for NEXUS.

This service manages all configuration loading from database with environment awareness.
It provides a unified interface for accessing configuration values throughout the system
with fallback to hardcoded defaults for resilience.
"""

import os
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ConfigService:
    """
    Database-driven configuration service for NEXUS.
    
    Loads configuration from database based on environment, with fallback to
    hardcoded defaults for resilience. Provides dot-notation access to
    configuration values.
    """
    
    def __init__(self, database_service=None):
        """Initialize the configuration service.
        
        Args:
            database_service: Optional DatabaseService instance for config loading
        """
        self._config: Dict[str, Any] = {}
        self._environment: str = "development"
        self._initialized = False
        self._database_service = database_service
        logger.info("ConfigService initialized")
    
    async def initialize(self) -> None:
        """
        Load and parse configuration from database.
        
        This method should be called once during application startup.
        """
        try:
            # Determine current environment
            self._environment = os.getenv("NEXUS_ENV", "development")
            logger.info(f"Initializing ConfigService for environment: {self._environment}")
            
            # Try to load configuration from database
            if self._database_service:
                try:
                    db_config = await self._database_service.get_configuration_async(self._environment)
                    if db_config:
                        self._config = db_config
                        logger.info(f"Configuration loaded from database for environment: {self._environment}")
                    else:
                        logger.warning(f"No configuration found in database for environment: {self._environment}")
                        self._load_default_config()
                except Exception as e:
                    logger.error(f"Failed to load configuration from database: {e}")
                    self._load_default_config()
            else:
                logger.warning("No database service provided, using default configuration")
                self._load_default_config()
            
            self._initialized = True
            logger.info("ConfigService initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize ConfigService: {e}")
            raise
    
    def _load_default_config(self) -> None:
        """Load hardcoded default configuration for resilience."""
        logger.warning("Loading default configuration for resilience")
        
        if self._environment == "development":
            self._config = {
                "server": {
                    "host": "127.0.0.1",
                    "port": 8000
                },
                "database": {
                    "mongo_uri": os.getenv("MONGO_URI", "mongodb://localhost:27017"),
                    "db_name": "NEXUS_DB_DEV"
                },
                "llm": {
                    "providers": {
                        "google": {
                            "model": "gemini-2.5-flash",
                            "api_key": os.getenv("GEMINI_API_KEY", "")
                        },
                        "openrouter": {
                            "model": "moonshotai/kimi-k2",
                            "api_key": os.getenv("OPENROUTER_API_KEY", "")
                        }
                    }
                },
                "system": {
                    "log_level": "INFO",
                    "max_tokens": 4000,
                    "temperature": 0.7
                }
            }
        elif self._environment == "production":
            self._config = {
                "server": {
                    "host": "0.0.0.0",
                    "port": 8000
                },
                "database": {
                    "mongo_uri": os.getenv("MONGO_URI", ""),
                    "db_name": "NEXUS_DB_PROD"
                },
                "llm": {
                    "providers": {
                        "google": {
                            "model": "gemini-2.5-flash",
                            "api_key": os.getenv("GEMINI_API_KEY", "")
                        },
                        "openrouter": {
                            "model": "moonshotai/kimi-k2",
                            "api_key": os.getenv("OPENROUTER_API_KEY", "")
                        }
                    }
                },
                "system": {
                    "log_level": "WARNING",
                    "max_tokens": 4000,
                    "temperature": 0.7
                }
            }
        else:
            # Fallback for unknown environments
            self._config = {
                "server": {
                    "host": "127.0.0.1",
                    "port": 8000
                },
                "database": {
                    "mongo_uri": os.getenv("MONGO_URI", ""),
                    "db_name": "NEXUS_DB"
                },
                "system": {
                    "log_level": "INFO"
                }
            }
        
        logger.info(f"Default configuration loaded for environment: {self._environment}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key: Dot-separated key path (e.g., 'llm.providers.google.model')
            default: Default value if key is not found
            
        Returns:
            The configuration value or default
        """
        if not self._initialized:
            raise RuntimeError("ConfigService not initialized. Call initialize() first.")
        
        keys = key.split('.')
        current = self._config
        
        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            logger.debug(f"Configuration key '{key}' not found, returning default: {default}")
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
            return value.lower() in ('true', '1', 'yes', 'on')
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
            logger.warning(f"Could not convert '{value}' to int for key '{key}', returning default: {default}")
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
            logger.warning(f"Could not convert '{value}' to float for key '{key}', returning default: {default}")
            return default
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get the entire configuration dictionary.
        
        Returns:
            Complete configuration dictionary
        """
        if not self._initialized:
            raise RuntimeError("ConfigService not initialized. Call initialize() first.")
        return self._config.copy()
    
    def get_environment(self) -> str:
        """
        Get the current environment.
        
        Returns:
            Current environment name
        """
        return self._environment
    
    def is_initialized(self) -> bool:
        """
        Check if the configuration service has been initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self._initialized
    
    async def update_configuration(self, config_data: Dict[str, Any]) -> bool:
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
            success = await self._database_service.upsert_configuration_async(self._environment, config_data)
            if success:
                self._config = config_data
                logger.info(f"Configuration updated successfully for environment: {self._environment}")
            return success
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            return False