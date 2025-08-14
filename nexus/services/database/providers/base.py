"""
Database provider abstract base class for NEXUS.

This module defines the abstract interface that all database providers must implement.
It ensures consistent behavior across different database backends (MongoDB, PostgreSQL, etc.).

Key classes:
- DatabaseProvider: Abstract base class defining the database interface
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from nexus.core.models import Message


class DatabaseProvider(ABC):
    """Abstract base class for database providers.

    All database providers must inherit from this class and implement
    all abstract methods to ensure consistent interface across different
    database backends.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the database.

        This method should handle connection initialization, authentication,
        and any necessary setup. Should raise appropriate exceptions if
        connection fails.
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the database.

        This method should properly close the database connection and
        clean up any resources.
        """
        pass

    @abstractmethod
    def insert_message(self, message: Message) -> bool:
        """Insert a message into the database.

        Args:
            message: The Message object to be persisted

        Returns:
            bool: True if insertion was successful, False otherwise

        Note:
            This is a synchronous method. The calling service should wrap
            this in asyncio.to_thread() for async execution.
        """
        pass

    @abstractmethod
    def get_messages_by_session_id(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve messages for a specific session.

        Args:
            session_id: The session ID to query for
            limit: Maximum number of messages to return (default: 20)

        Returns:
            List[Dict[str, Any]]: List of message dictionaries, sorted by timestamp
                                 in descending order (newest first)

        Note:
            This is a synchronous method. The calling service should wrap
            this in asyncio.to_thread() for async execution.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the database connection is healthy.

        Returns:
            bool: True if database is accessible and healthy, False otherwise
        """
        pass