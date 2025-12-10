"""
Database service for NEXUS.

This service provides an async wrapper around database providers and handles
all database operations for the NEXUS system. It manages the database connection
and provides async methods for message persistence and retrieval.

Key features:
- Async wrapper: Wraps synchronous MongoDB operations using asyncio.to_thread
  to prevent blocking the event loop
- Connection management: Handles database connection lifecycle (connect, disconnect)
- Message persistence: Async interface for inserting messages into the database
- History retrieval: Async interface for loading conversation history by owner_key
- Configuration management: Async methods for loading and updating environment-specific
  configuration from the 'configurations' collection
- Provider abstraction: Uses pluggable database providers (currently MongoProvider)
  for flexibility and testability

Database collections:
- messages: Conversation history (human inputs, AI responses, tool results)
- identities: User identities with config/prompt overrides
- configurations: Environment-specific system configuration (development, production)

Key classes:
- DatabaseService: Main service class providing async database operations
"""

import asyncio
import logging
from typing import Any

from nexus.core.bus import NexusBus
from nexus.core.models import Message

from .providers.mongo import MongoProvider

logger = logging.getLogger(__name__)


class DatabaseService:
    """Database service providing async database operations.

    This service acts as an async wrapper around database providers,
    ensuring that all database operations are non-blocking and properly
    integrated with the NEXUS event-driven architecture.
    """

    def __init__(self, bus: NexusBus, mongo_uri: str, db_name: str):
        """Initialize DatabaseService with configuration.

        Args:
            bus: The NexusBus instance for event communication
            mongo_uri: MongoDB connection URI
            db_name: Database name
        """
        self.bus = bus
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.provider: MongoProvider | None = None
        self._connected = False

        # Initialize database provider
        self._initialize_provider()
        logger.info("DatabaseService initialized (connection not established)")

    def _initialize_provider(self) -> None:
        """Initialize the database provider."""
        try:
            if not self.mongo_uri:
                raise ValueError(
                    "MongoDB URI not provided. Please set MONGO_URI in .env file."
                )

            # Create MongoDB provider (but don't connect yet)
            self.provider = MongoProvider(self.mongo_uri, self.db_name)

            logger.info(f"Database provider initialized: MongoDB ({self.db_name})")

        except Exception as e:
            logger.error(f"Failed to initialize database provider: {e}")
            raise

    def connect(self) -> bool:
        """
        Establish connection to the database.

        Returns:
            True if connection was successful, False otherwise
        """
        if not self.provider:
            logger.error("Database provider not initialized")
            return False

        try:
            self.provider.connect()
            self._connected = True
            logger.info("Database connection established successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            self._connected = False
            return False

    def is_connected(self) -> bool:
        """
        Check if database connection is established.

        Returns:
            True if connected, False otherwise
        """
        return self._connected and self.provider is not None

    def disconnect(self) -> None:
        """Close database connection."""
        if self.provider:
            try:
                self.provider.disconnect()
                self._connected = False
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error during database disconnect: {e}")

    def subscribe_to_bus(self) -> None:
        """Subscribe to bus topics (no direct subscriptions for now)."""
        # DatabaseService doesn't directly subscribe to topics
        # It's used by PersistenceService which handles the subscriptions
        logger.info("DatabaseService subscribed to NexusBus")

    async def insert_message_async(self, message: Message) -> bool:
        """Asynchronously insert a message into the database.

        Args:
            message: The message object to insert

        Returns:
            bool: True if insertion was successful, False otherwise
        """
        if not self.is_connected() or not self.provider:
            logger.error("Database not connected. Cannot insert message.")
            return False

        try:
            # Use asyncio.to_thread to run the sync database operation
            result = await asyncio.to_thread(self.provider.insert_message, message)
            return result

        except Exception as e:
            logger.error(f"Error during async message insertion: {e}")
            return False

    async def get_history_by_owner_key(
        self, owner_key: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Asynchronously retrieve message history for an owner (user identity).

        Args:
            owner_key: The owner's public key to query for
            limit: Maximum number of messages to return (default: 20)

        Returns:
            List[Dict[str, Any]]: List of message dictionaries, sorted by timestamp
                                 in descending order (newest first)
        """
        if not self.is_connected() or not self.provider:
            logger.error("Database not connected. Cannot retrieve history.")
            return []

        try:
            # Use asyncio.to_thread to run the sync database operation
            messages = await asyncio.to_thread(
                self.provider.get_messages_by_owner_key, owner_key, limit
            )
            return messages

        except Exception as e:
            logger.error(f"Error during async history retrieval: {e}")
            return []

    async def get_configuration_async(self, environment: str) -> dict[str, Any] | None:
        """Asynchronously get configuration for a specific environment.

        Args:
            environment: The environment name (e.g., 'development', 'production')

        Returns:
            Optional[Dict[str, Any]]: Configuration dictionary if found, None otherwise
        """
        if not self.is_connected() or not self.provider:
            logger.error("Database not connected. Cannot retrieve configuration.")
            return None

        try:
            # Use asyncio.to_thread to run the sync database operation
            config = await asyncio.to_thread(
                self.provider.get_configuration, environment
            )
            return config

        except Exception as e:
            logger.error(f"Error during async configuration retrieval: {e}")
            return None

    async def upsert_configuration_async(
        self, environment: str, config_data: dict[str, Any]
    ) -> bool:
        """Asynchronously insert or update configuration for a specific environment.

        Args:
            environment: The environment name (e.g., 'development', 'production')
            config_data: Configuration data to store

        Returns:
            bool: True if operation was successful, False otherwise
        """
        if not self.is_connected() or not self.provider:
            logger.error("Database not connected. Cannot upsert configuration.")
            return False

        try:
            # Use asyncio.to_thread to run the sync database operation
            result = await asyncio.to_thread(
                self.provider.upsert_configuration, environment, config_data
            )
            return result

        except Exception as e:
            logger.error(f"Error during async configuration upsert: {e}")
            return False

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
