"""
Identity Service for NEXUS.

This service manages user identities and provides the "gatekeeper" functionality
for the sovereign personalization architecture. It determines whether a user
is a "visitor" (unregistered) or "member" (registered) based on their public_key.

Key responsibilities:
- Retrieve user identity by public_key
- Create new user identities
- Provide get_or_create functionality for identity management
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
            'metadata': metadata or {}
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



