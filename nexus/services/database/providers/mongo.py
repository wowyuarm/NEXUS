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

            # Create index on session_id and timestamp for efficient queries
            self.messages_collection.create_index([
                ("session_id", 1),
                ("timestamp", DESCENDING)
            ])

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

    def get_messages_by_session_id(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve messages for a specific session from MongoDB.

        Args:
            session_id: The session ID to query for
            limit: Maximum number of messages to return (default: 20)

        Returns:
            List[Dict[str, Any]]: List of message dictionaries, sorted by timestamp
                                 in descending order (newest first)
        """
        if self.messages_collection is None:
            logger.error("MongoDB not connected. Cannot retrieve messages.")
            return []

        try:
            # Query messages for the session, sorted by timestamp descending
            cursor = self.messages_collection.find(
                {"session_id": session_id}
            ).sort("timestamp", DESCENDING).limit(limit)

            messages = list(cursor)

            # Convert ObjectId to string for JSON serialization
            for message in messages:
                if '_id' in message:
                    message['_id'] = str(message['_id'])

            logger.info(f"Retrieved {len(messages)} messages for session_id={session_id}")
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