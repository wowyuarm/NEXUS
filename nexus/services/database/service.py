"""
Database service for NEXUS.

This service provides an async wrapper around database providers and handles
all database operations for the NEXUS system. It manages the database connection
and provides async methods for message persistence and retrieval.

Key classes:
- DatabaseService: Main service class providing async database operations
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from nexus.core.bus import NexusBus
from nexus.core.models import Message
from nexus.services.config import ConfigService
from .providers.mongo import MongoProvider

logger = logging.getLogger(__name__)


class DatabaseService:
    """Database service providing async database operations.

    This service acts as an async wrapper around database providers,
    ensuring that all database operations are non-blocking and properly
    integrated with the NEXUS event-driven architecture.
    """

    def __init__(self, bus: NexusBus, config_service: ConfigService):
        """Initialize DatabaseService with configuration.

        Args:
            bus: The NexusBus instance for event communication
            config_service: Configuration service for database settings
        """
        self.bus = bus
        self.config_service = config_service
        self.provider: Optional[MongoProvider] = None

        # Initialize database provider based on configuration
        self._initialize_provider()
        logger.info("DatabaseService initialized")

    def _initialize_provider(self) -> None:
        """Initialize the database provider based on configuration."""
        try:
            # Get database configuration using ConfigService dot notation
            mongo_uri = self.config_service.get("database.mongo_uri")
            db_name = self.config_service.get("database.db_name", "NEXUS_DB")

            if not mongo_uri:
                raise ValueError("MongoDB URI not found in configuration. Please set MONGO_URI in .env file.")

            # Create and connect MongoDB provider
            self.provider = MongoProvider(mongo_uri, db_name)
            self.provider.connect()

            logger.info(f"Database provider initialized: MongoDB ({db_name})")

        except Exception as e:
            logger.error(f"Failed to initialize database provider: {e}")
            raise

    def subscribe_to_bus(self) -> None:
        """Subscribe to bus topics (no direct subscriptions for now)."""
        # DatabaseService doesn't directly subscribe to topics
        # It's used by PersistenceService which handles the subscriptions
        logger.info("DatabaseService subscribed to NexusBus")

    async def insert_message_async(self, message: Message) -> bool:
        """Asynchronously insert a message into the database.

        Args:
            message: The Message object to be persisted

        Returns:
            bool: True if insertion was successful, False otherwise
        """
        if not self.provider:
            logger.error("Database provider not initialized")
            return False

        try:
            # Use asyncio.to_thread to run the sync database operation
            result = await asyncio.to_thread(self.provider.insert_message, message)
            return result

        except Exception as e:
            logger.error(f"Error during async message insertion: {e}")
            return False

    async def get_history_async(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Asynchronously retrieve message history for a session.

        Args:
            session_id: The session ID to query for
            limit: Maximum number of messages to return (default: 20)

        Returns:
            List[Dict[str, Any]]: List of message dictionaries, sorted by timestamp
                                 in descending order (newest first)
        """
        if not self.provider:
            logger.error("Database provider not initialized")
            return []

        try:
            # Use asyncio.to_thread to run the sync database operation
            messages = await asyncio.to_thread(
                self.provider.get_messages_by_session_id,
                session_id,
                limit
            )
            return messages

        except Exception as e:
            logger.error(f"Error during async history retrieval: {e}")
            return []



    async def run_forever(self) -> None:
        """Run background tasks if any (idle for now)."""
        # No background loop needed for DatabaseService
        # It's a stateless service that responds to method calls
        return

    def __del__(self):
        """Cleanup database connection on service destruction."""
        if self.provider:
            try:
                self.provider.disconnect()
            except Exception as e:
                logger.error(f"Error during database cleanup: {e}")
