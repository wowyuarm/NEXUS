"""
Identity Service for NEXUS.

This service manages user identities and provides the "gatekeeper" functionality
for the sovereign personalization architecture. It determines whether a user
is a "visitor" (unregistered) or "member" (registered) based on their public_key.

Key responsibilities:
- Identity retrieval: Get identity by public_key to distinguish visitors from members
- Identity creation: Create new identities with empty config/prompt overrides
- Get-or-create pattern: Convenience method for identity initialization
- User profile management: Retrieve structured user_profile with config_overrides
  and prompt_overrides for downstream personalization
- Config updates: Update user configuration overrides (model, temperature, max_tokens)
- Prompt updates: Update user prompt overrides (persona, system, tools)

Sovereign personalization architecture:
Each user's identity document contains:
- public_key: Ethereum-style public key (user identity)
- config_overrides: User-specific LLM configuration (overrides system defaults)
- prompt_overrides: User-specific prompt customizations (persona, system, tools)
- created_at: Identity creation timestamp

The IdentityService acts as the gatekeeper by providing identity verification
to OrchestratorService, which halts unregistered visitors and injects user_profile
into Run metadata for registered members.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from nexus.services.database.service import DatabaseService

logger = logging.getLogger(__name__)


class IdentityService:
    """Service for managing user identities in the sovereign personalization system.
    
    This service acts as the gatekeeper between "visitor" and "member" states,
    providing identity verification and creation capabilities.
    """

    def __init__(self, db_service: DatabaseService):
        """Initialize IdentityService.

        Args:
            db_service: DatabaseService instance for identity persistence
        """
        self.db_service = db_service
        logger.info("IdentityService initialized")

    async def get_identity(self, public_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve an identity by its public key.

        Args:
            public_key: The public key to search for

        Returns:
            Optional[Dict[str, Any]]: Identity document if found, None otherwise
        """
        logger.debug(f"Retrieving identity for public_key={public_key}")
        
        # Call database service in thread pool (it's synchronous)
        identity = await asyncio.to_thread(
            self.db_service.provider.find_identity_by_public_key,
            public_key
        )
        
        if identity:
            logger.info(f"Identity found for public_key={public_key}")
        else:
            logger.debug(f"No identity found for public_key={public_key}")
        
        return identity

    async def create_identity(self, public_key: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Create a new identity.

        Args:
            public_key: The public key for the new identity
            metadata: Optional metadata to attach to the identity

        Returns:
            bool: True if creation was successful, False otherwise
        """
        logger.info(f"Creating new identity for public_key={public_key}")
        
        identity_data = {
            'public_key': public_key,
            'created_at': datetime.now(timezone.utc),
            'metadata': metadata or {},
            'config_overrides': {},
            'prompt_overrides': {}
        }
        
        # Call database service in thread pool (it's synchronous)
        success = await asyncio.to_thread(
            self.db_service.provider.create_identity,
            identity_data
        )
        
        if success:
            logger.info(f"Successfully created identity for public_key={public_key}")
        else:
            logger.error(f"Failed to create identity for public_key={public_key}")
        
        return success

    async def get_or_create_identity(self, public_key: str) -> Optional[Dict[str, Any]]:
        """Get an existing identity or create a new one if it doesn't exist.

        This is a convenience method that combines get and create operations.

        Args:
            public_key: The public key to search for or create

        Returns:
            Optional[Dict[str, Any]]: Identity document, or None if creation failed.
                                    Contains '_just_created' flag if newly created.
        """
        logger.debug(f"Get or create identity for public_key={public_key}")
        
        # Try to get existing identity
        identity = await self.get_identity(public_key)
        
        if identity:
            logger.debug(f"Found existing identity for public_key={public_key}")
            return identity
        
        # Create new identity
        logger.info(f"Identity not found, creating new identity for public_key={public_key}")
        success = await self.create_identity(public_key)
        
        if not success:
            logger.error(f"Failed to create identity for public_key={public_key}")
            return None
        
        # Retrieve the newly created identity
        new_identity = await self.get_identity(public_key)
        if new_identity:
            # Add marker to indicate this was just created
            new_identity['_just_created'] = True
        return new_identity

    async def get_user_profile(self, public_key: str) -> Dict[str, Any]:
        """Get user profile including overrides.
        
        This is the primary method for retrieving a user's personalization settings.
        Returns a structured user_profile dict containing config_overrides and prompt_overrides.
        
        Args:
            public_key: The user's public key
            
        Returns:
            Dict containing user_profile with overrides, or minimal profile if not found
        """
        logger.debug(f"Retrieving user profile for public_key={public_key}")
        
        identity = await self.get_identity(public_key)
        
        if not identity:
            logger.warning(f"No identity found for public_key={public_key}, returning minimal profile")
            return {
                'public_key': public_key,
                'config_overrides': {},
                'prompt_overrides': {},
                'created_at': None
            }
        
        # Extract user profile from identity document
        user_profile = {
            'public_key': identity['public_key'],
            'config_overrides': identity.get('config_overrides', {}),
            'prompt_overrides': identity.get('prompt_overrides', {}),
            'created_at': identity.get('created_at')
        }
        
        logger.info(f"User profile retrieved for public_key={public_key}")
        return user_profile

    async def update_user_config(self, public_key: str, config_overrides: Dict[str, Any]) -> bool:
        """Update user configuration overrides.
        
        Args:
            public_key: The user's public key
            config_overrides: Dict of config values to override (model, temperature, etc.)
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        logger.info(f"Updating config overrides for public_key={public_key}")
        
        success = await asyncio.to_thread(
            self.db_service.provider.update_identity_field,
            public_key,
            'config_overrides',
            config_overrides
        )
        
        if success:
            logger.info(f"Successfully updated config_overrides for public_key={public_key}")
        else:
            logger.error(f"Failed to update config_overrides for public_key={public_key}")
        
        return success

    async def update_user_prompts(self, public_key: str, prompt_overrides: Dict[str, str]) -> bool:
        """Update user prompt overrides.
        
        Args:
            public_key: The user's public key
            prompt_overrides: Dict of prompt keys to override (persona, system, tools, etc.)
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        logger.info(f"Updating prompt overrides for public_key={public_key}")
        
        success = await asyncio.to_thread(
            self.db_service.provider.update_identity_field,
            public_key,
            'prompt_overrides',
            prompt_overrides
        )
        
        if success:
            logger.info(f"Successfully updated prompt_overrides for public_key={public_key}")
        else:
            logger.error(f"Failed to update prompt_overrides for public_key={public_key}")
        
        return success

    async def delete_identity(self, public_key: str) -> bool:
        """Delete an identity from the database.
        
        This is typically called when a user wants to permanently remove their identity.
        
        Args:
            public_key: The user's public key
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        logger.info(f"Deleting identity for public_key={public_key}")
        
        success = await asyncio.to_thread(
            self.db_service.provider.delete_identity,
            public_key
        )
        
        if success:
            logger.info(f"Successfully deleted identity for public_key={public_key}")
        else:
            logger.warning(f"Failed to delete identity (may not exist) for public_key={public_key}")
        
        return success



