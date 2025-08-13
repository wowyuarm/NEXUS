"""
Configuration service for NEXUS.

This service manages all configuration loading from config.default.yml and .env files.
It supports environment variable substitution and provides a unified interface for
accessing configuration values throughout the system.
"""

import os
import re
import logging
from typing import Any, Dict
import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigService:
    """
    Unified configuration service for NEXUS.
    
    Loads configuration from config.default.yml and .env files,
    supports environment variable substitution, and provides
    dot-notation access to configuration values.
    """
    
    def __init__(self):
        """Initialize the configuration service."""
        self._config: Dict[str, Any] = {}
        self._env_vars: Dict[str, str] = {}
        self._initialized = False
        logger.info("ConfigService initialized")
    
    def initialize(self) -> None:
        """
        Load and parse configuration from files.
        
        This method should be called once during application startup.
        """
        try:
            # Load environment variables from .env file
            self._load_env_vars()
            
            # Load YAML configuration
            self._load_yaml_config()
            
            # Substitute environment variables in config
            self._substitute_env_vars()
            
            self._initialized = True
            logger.info("ConfigService initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize ConfigService: {e}")
            raise
    
    def _load_env_vars(self) -> None:
        """Load environment variables from .env file."""
        # Get project root directory (parent of nexus directory)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        env_path = os.path.join(project_root, ".env")
        
        if os.path.exists(env_path):
            load_dotenv(env_path)
            logger.info(f"Loaded environment variables from {env_path}")
        else:
            logger.warning(f"No .env file found at {env_path}")
        
        # Store all environment variables for substitution
        self._env_vars = dict(os.environ)
    
    def _load_yaml_config(self) -> None:
        """Load configuration from config.default.yml file."""
        # Get project root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        config_path = os.path.join(project_root, "config.default.yml")
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}
        
        logger.info(f"Loaded YAML configuration from {config_path}")
    
    def _substitute_env_vars(self) -> None:
        """Recursively substitute environment variables in configuration."""
        self._config = self._substitute_recursive(self._config)
    
    def _substitute_recursive(self, obj: Any) -> Any:
        """
        Recursively substitute environment variables in nested structures.
        
        Args:
            obj: The object to process (dict, list, str, or other)
            
        Returns:
            The object with environment variables substituted
        """
        if isinstance(obj, dict):
            return {key: self._substitute_recursive(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_recursive(item) for item in obj]
        elif isinstance(obj, str):
            return self._substitute_env_in_string(obj)
        else:
            return obj
    
    def _substitute_env_in_string(self, text: str) -> str:
        """
        Substitute environment variables in a string.
        
        Supports ${VAR_NAME} syntax.
        
        Args:
            text: String that may contain environment variable references
            
        Returns:
            String with environment variables substituted
        """
        def replace_var(match):
            var_name = match.group(1)
            return self._env_vars.get(var_name, match.group(0))
        
        # Pattern to match ${VAR_NAME}
        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, replace_var, text)
    
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
    
    def is_initialized(self) -> bool:
        """
        Check if the configuration service has been initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self._initialized
