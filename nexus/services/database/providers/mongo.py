"""
MongoDB provider implementation for NEXUS.

This module implements the MongoDB-specific database provider that handles
all MongoDB operations including connection management, message persistence,
and history retrieval.

Key classes:
- MongoProvider: Concrete implementation of DatabaseProvider for MongoDB
"""

import logging
from typing import List, Dict, Any, Optional
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, OperationFailure

from .base import DatabaseProvider
from nexus.core.models import Message

logger = logging.getLogger(__name__)


class MongoProvider(DatabaseProvider):
    """MongoDB implementation of the DatabaseProvider interface.

    This provider handles all MongoDB-specific operations including
    connection management, message persistence, and query operations.
    """

    def __init__(self, mongo_uri: str, db_name: str):
        """Initialize MongoDB provider.

        Args:
            mongo_uri: MongoDB connection URI
            db_name: Name of the database to use
        """
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client: Optional[MongoClient] = None
        self.database: Optional[Database] = None
        self.messages_collection: Optional[Collection] = None
        self.config_collection: Optional[Collection] = None
        self.identities_collection: Optional[Collection] = None
        logger.info(f"MongoProvider initialized for database: {db_name}")

    def connect(self) -> None:
        """Establish connection to MongoDB.

        Raises:
            ConnectionFailure: If unable to connect to MongoDB
        """
        try:
            self.client = MongoClient(self.mongo_uri)
            # Test the connection
            self.client.admin.command('ping')

            self.database = self.client[self.db_name]
            self.messages_collection = self.database.messages
            self.config_collection = self.database.configurations
            self.identities_collection = self.database.identities

            # Create index on owner_key and timestamp for efficient message queries
            self.messages_collection.create_index([
                ("owner_key", 1),
                ("timestamp", DESCENDING)
            ])

            # Create unique index on environment for configuration collection
            self.config_collection.create_index([
                ("environment", 1)
            ], unique=True)

            # Create unique index on public_key for identities collection
            self.identities_collection.create_index([
                ("public_key", 1)
            ], unique=True)

            logger.info(f"Successfully connected to MongoDB: {self.db_name}")

        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during MongoDB connection: {e}")
            raise

    def disconnect(self) -> None:
        """Close connection to MongoDB."""
        if self.client:
            self.client.close()
            self.client = None
            self.database = None
            self.messages_collection = None
            self.config_collection = None
            self.identities_collection = None
            logger.info("MongoDB connection closed")

    def insert_message(self, message: Message) -> bool:
        """Insert a message into the MongoDB messages collection.

        Args:
            message: The Message object to be persisted

        Returns:
            bool: True if insertion was successful, False otherwise
        """
        if self.messages_collection is None:
            logger.error("MongoDB not connected. Cannot insert message.")
            return False

        try:
            # Convert Message to dict for MongoDB storage
            message_dict = message.model_dump()

            # Convert datetime to MongoDB-compatible format
            if message_dict.get('timestamp'):
                message_dict['timestamp'] = message.timestamp

            result = self.messages_collection.insert_one(message_dict)

            if result.inserted_id:
                logger.info(f"Message inserted successfully: msg_id={message.id}, run_id={message.run_id}")
                return True
            else:
                logger.error(f"Failed to insert message: msg_id={message.id}")
                return False

        except OperationFailure as e:
            logger.error(f"MongoDB operation failed during message insertion: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during message insertion: {e}")
            return False

    def get_messages_by_owner_key(self, owner_key: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve messages for a specific owner (user identity) from MongoDB.

        Args:
            owner_key: The owner's public key to query for
            limit: Maximum number of messages to return (default: 20)

        Returns:
            List[Dict[str, Any]]: List of message dictionaries, sorted by timestamp
                                 in descending order (newest first)
        """
        if self.messages_collection is None:
            logger.error("MongoDB not connected. Cannot retrieve messages.")
            return []

        try:
            # Query messages for the owner, sorted by timestamp descending
            cursor = self.messages_collection.find(
                {"owner_key": owner_key}
            ).sort("timestamp", DESCENDING).limit(limit)

            messages = list(cursor)

            # Convert ObjectId to string for JSON serialization
            for message in messages:
                if '_id' in message:
                    message['_id'] = str(message['_id'])

            logger.info(f"Retrieved {len(messages)} messages for owner_key={owner_key}")
            return messages

        except OperationFailure as e:
            logger.error(f"MongoDB operation failed during message retrieval: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during message retrieval: {e}")
            return []

    def health_check(self) -> bool:
        """Check if the MongoDB connection is healthy.

        Returns:
            bool: True if database is accessible and healthy, False otherwise
        """
        if self.client is None:
            logger.warning("MongoDB client not initialized")
            return False

        try:
            # Ping the database to check connectivity
            self.client.admin.command('ping')
            logger.debug("MongoDB health check passed")
            return True

        except ConnectionFailure as e:
            logger.error(f"MongoDB health check failed - connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"MongoDB health check failed - unexpected error: {e}")
            return False

    def get_configuration(self, environment: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific environment.

        Args:
            environment: The environment name (e.g., 'development', 'production')

        Returns:
            Optional[Dict[str, Any]]: Configuration dictionary if found, None otherwise
        """
        if self.config_collection is None:
            logger.error("MongoDB not connected. Cannot retrieve configuration.")
            return None

        try:
            config_doc = self.config_collection.find_one({"environment": environment})
            
            if config_doc:
                # Use direct structure only - configuration fields are stored at top level
                config_data = dict(config_doc)
                config_data.pop("_id", None)
                config_data.pop("environment", None)
                logger.info(f"Retrieved configuration for environment: {environment}")
                return config_data
            
            logger.warning(f"No configuration found for environment: {environment}")
            return None

        except OperationFailure as e:
            logger.error(f"MongoDB operation failed during configuration retrieval: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during configuration retrieval: {e}")
            return None

    def upsert_configuration(self, environment: str, config_data: Dict[str, Any]) -> bool:
        """Insert or update configuration for a specific environment.

        Args:
            environment: The environment name (e.g., 'development', 'production')
            config_data: Configuration data to store (will be stored directly at top level)

        Returns:
            bool: True if operation was successful, False otherwise
        """
        if self.config_collection is None:
            logger.error("MongoDB not connected. Cannot upsert configuration.")
            return False

        try:
            # Prepare document with environment field and config fields at top level
            document = {"environment": environment}
            document.update(config_data)

            # Upsert with direct structure (no config_data wrapper)
            result = self.config_collection.replace_one(
                {"environment": environment},
                document,
                upsert=True
            )

            if result.upserted_id or result.modified_count > 0:
                logger.info(f"Configuration upserted successfully for environment: {environment}")
                return True
            else:
                logger.error(f"Failed to upsert configuration for environment: {environment}")
                return False

        except OperationFailure as e:
            logger.error(f"MongoDB operation failed during configuration upsert: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during configuration upsert: {e}")
            return False

    def find_identity_by_public_key(self, public_key: str) -> Optional[Dict[str, Any]]:
        """Find an identity by its public key.

        Args:
            public_key: The public key to search for

        Returns:
            Optional[Dict[str, Any]]: Identity document if found, None otherwise
        """
        if self.identities_collection is None:
            logger.error("MongoDB not connected. Cannot retrieve identity.")
            return None

        try:
            identity_doc = self.identities_collection.find_one({"public_key": public_key})
            
            if identity_doc:
                # Convert ObjectId to string for JSON serialization
                if '_id' in identity_doc:
                    identity_doc['_id'] = str(identity_doc['_id'])
                logger.info(f"Identity found for public_key={public_key}")
                return identity_doc
            else:
                logger.debug(f"No identity found for public_key={public_key}")
                return None

        except OperationFailure as e:
            logger.error(f"MongoDB operation failed during identity retrieval: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during identity retrieval: {e}")
            return None

    def create_identity(self, identity_data: Dict[str, Any]) -> bool:
        """Create a new identity in the database.

        Args:
            identity_data: Dictionary containing identity data (must include 'public_key')

        Returns:
            bool: True if creation was successful, False otherwise
        """
        if self.identities_collection is None:
            logger.error("MongoDB not connected. Cannot create identity.")
            return False

        try:
            result = self.identities_collection.insert_one(identity_data)

            if result.inserted_id:
                logger.info(f"Identity created successfully: public_key={identity_data.get('public_key')}")
                return True
            else:
                logger.error(f"Failed to create identity: public_key={identity_data.get('public_key')}")
                return False

        except OperationFailure as e:
            logger.error(f"MongoDB operation failed during identity creation: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during identity creation: {e}")
            return False

    def update_identity_field(self, public_key: str, field_name: str, field_value: Any) -> bool:
        """Update a specific field in an identity document.

        Args:
            public_key: The public key identifying the identity
            field_name: Name of the field to update (e.g., 'config_overrides', 'prompt_overrides')
            field_value: New value for the field

        Returns:
            bool: True if update was successful, False otherwise
        """
        if self.identities_collection is None:
            logger.error("MongoDB not connected. Cannot update identity.")
            return False

        try:
            result = self.identities_collection.update_one(
                {"public_key": public_key},
                {"$set": {field_name: field_value}}
            )

            if result.modified_count > 0:
                logger.info(f"Successfully updated {field_name} for public_key: {public_key}")
                return True
            elif result.matched_count > 0:
                logger.info(f"Identity found but {field_name} unchanged for public_key: {public_key}")
                return True
            else:
                logger.warning(f"No identity found for public_key: {public_key}")
                return False

        except OperationFailure as e:
            logger.error(f"MongoDB operation failed during identity update: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during identity update: {e}")
            return False