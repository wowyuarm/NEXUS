"""
Database provider abstract base class for NEXUS.

This module defines the abstract interface that all database providers must implement.
It ensures consistent behavior across different database backends (MongoDB, PostgreSQL, etc.).

Key classes:
- DatabaseProvider: Abstract base class defining the database interface
"""

from abc import ABC, abstractmethod
from typing import Any

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
    def get_messages_by_owner_key(
        self, owner_key: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Retrieve messages for a specific owner (user identity).

        Args:
            owner_key: The owner's public key to query for
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

    @abstractmethod
    def get_configuration(self, environment: str) -> dict[str, Any] | None:
        """Get configuration for a specific environment.

        Args:
            environment: The environment name (e.g., 'development', 'production')

        Returns:
            Optional[Dict[str, Any]]: Configuration dictionary if found, None otherwise
        """
        pass

    @abstractmethod
    def upsert_configuration(
        self, environment: str, config_data: dict[str, Any]
    ) -> bool:
        """Insert or update configuration for a specific environment.

        Args:
            environment: The environment name (e.g., 'development', 'production')
            config_data: Configuration data to store

        Returns:
            bool: True if operation was successful, False otherwise
        """
        pass

    @abstractmethod
    def find_identity_by_public_key(self, public_key: str) -> dict[str, Any] | None:
        """Find an identity by its public key.

        Args:
            public_key: The public key to search for

        Returns:
            Optional[Dict[str, Any]]: Identity document if found, None otherwise
        """
        pass

    @abstractmethod
    def create_identity(self, identity_data: dict[str, Any]) -> bool:
        """Create a new identity in the database.

        Args:
            identity_data: Dictionary containing identity data (must include 'public_key')

        Returns:
            bool: True if creation was successful, False otherwise
        """
        pass
