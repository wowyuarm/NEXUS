"""
Unit tests for MongoProvider database operations.

These tests verify that MongoProvider correctly handles database operations
including connection management, message persistence, and query operations.
All external dependencies are mocked to ensure isolation.
"""

from unittest.mock import Mock

import pytest
from pymongo.errors import ConnectionFailure, OperationFailure

from nexus.core.models import Message, Role
from nexus.services.database.providers.mongo import MongoProvider


class TestMongoProvider:
    """Test suite for MongoProvider class."""

    def test_initialization(self):
        """Test that MongoProvider initializes with correct attributes."""
        provider = MongoProvider("mongodb://localhost:27017", "test_db")

        assert provider.mongo_uri == "mongodb://localhost:27017"
        assert provider.db_name == "test_db"
        assert provider.client is None
        assert provider.database is None
        assert provider.messages_collection is None
        assert provider.config_collection is None

    def test_connection_failure(self, mocker):
        """Test that connection failures are handled correctly."""
        # Mock pymongo.MongoClient to raise ConnectionFailure
        mock_client = Mock()
        mocker.patch(
            "nexus.services.database.providers.mongo.MongoClient",
            return_value=mock_client,
        )
        mock_client.admin.command.side_effect = ConnectionFailure("Connection failed")

        provider = MongoProvider("mongodb://localhost:27017", "test_db")

        with pytest.raises(ConnectionFailure):
            provider.connect()

        assert provider.client is not None  # Client was created but connection failed
        assert provider.database is None

    def test_connection_success(self, mocker):
        """Test successful connection to MongoDB."""
        # Create a simple test that verifies the connection process works
        mock_client = Mock()
        mock_client.admin.command.return_value = None

        # Create mock database and collections
        mock_database = Mock()
        mock_messages_collection = Mock()
        mock_config_collection = Mock()
        mock_identities_collection = Mock()

        # Attach collections as attributes as used by provider (attr access)
        mock_database.messages = mock_messages_collection
        mock_database.configurations = mock_config_collection
        mock_database.identities = mock_identities_collection

        # Also support item access for database retrieval from client
        def mock_database_getitem(name):
            if name == "messages":
                return mock_messages_collection
            elif name == "configurations":
                return mock_config_collection
            elif name == "identities":
                return mock_identities_collection
            raise KeyError(name)

        mock_database.__getitem__ = Mock(side_effect=mock_database_getitem)

        # Mock the client access to return our database
        def mock_client_getitem(name):
            if name == "test_db":
                return mock_database
            raise KeyError(name)

        mock_client.__getitem__ = Mock(side_effect=mock_client_getitem)

        # Patch MongoClient
        mock_mongo_client = mocker.patch(
            "nexus.services.database.providers.mongo.MongoClient"
        )
        mock_mongo_client.return_value = mock_client

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.connect()

        # Verify the basic connection process
        mock_client.admin.command.assert_called_once_with("ping")
        mock_client.__getitem__.assert_called_once_with("test_db")

        # Verify indexes were created
        mock_messages_collection.create_index.assert_called_once()
        mock_config_collection.create_index.assert_called_once()
        mock_identities_collection.create_index.assert_called_once()

    def test_insert_message_success(self, mocker):
        """Test successful message insertion."""
        # Mock MongoDB collection
        mock_collection = Mock()
        mock_result = Mock()
        mock_result.inserted_id = "test_message_id"
        mock_collection.insert_one.return_value = mock_result

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.messages_collection = mock_collection

        # Create test message
        message = Message(
            run_id="test_run",
            owner_key="test_public_key_123",
            role=Role.HUMAN,
            content="Test message",
        )

        result = provider.insert_message(message)

        assert result is True
        mock_collection.insert_one.assert_called_once()

        # Verify the message was converted to dict
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["run_id"] == "test_run"
        assert call_args["owner_key"] == "test_public_key_123"
        assert call_args["role"] == Role.HUMAN
        assert call_args["content"] == "Test message"

    def test_insert_message_operation_failure(self, mocker):
        """Test message insertion when MongoDB operation fails."""
        # Mock MongoDB collection to raise OperationFailure
        mock_collection = Mock()
        mock_collection.insert_one.side_effect = OperationFailure("Insert failed")

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.messages_collection = mock_collection

        # Create test message
        message = Message(
            run_id="test_run",
            owner_key="test_public_key_123",
            role=Role.HUMAN,
            content="Test message",
        )

        result = provider.insert_message(message)

        assert result is False
        mock_collection.insert_one.assert_called_once()

    def test_insert_message_not_connected(self):
        """Test message insertion when not connected to database."""
        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        # provider.messages_collection is None

        message = Message(
            run_id="test_run",
            owner_key="test_public_key_123",
            role=Role.HUMAN,
            content="Test message",
        )

        result = provider.insert_message(message)

        assert result is False

    def test_get_messages_success(self, mocker):
        """Test successful message retrieval."""
        # Mock MongoDB collection and cursor
        mock_collection = Mock()
        mock_cursor = Mock()

        # Mock MongoDB documents with ObjectId
        mock_document1 = {
            "_id": Mock(),
            "run_id": "test_run",
            "owner_key": "test_public_key_123",
            "role": Role.HUMAN,
            "content": "First message",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        mock_document2 = {
            "_id": Mock(),
            "run_id": "test_run",
            "owner_key": "test_public_key_123",
            "role": Role.AI,
            "content": "Second message",
            "timestamp": "2024-01-01T00:01:00Z",
        }

        mock_cursor.__iter__ = Mock(return_value=iter([mock_document1, mock_document2]))
        mock_collection.find.return_value = mock_cursor
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.messages_collection = mock_collection

        messages = provider.get_messages_by_owner_key("test_public_key_123", limit=10)

        assert len(messages) == 2
        assert messages[0]["role"] == Role.HUMAN
        assert messages[0]["content"] == "First message"
        assert messages[1]["role"] == Role.AI
        assert messages[1]["content"] == "Second message"

        # Verify ObjectId was converted to string
        assert isinstance(messages[0]["_id"], str)
        assert isinstance(messages[1]["_id"], str)

        # Verify query parameters
        mock_collection.find.assert_called_once_with(
            {"owner_key": "test_public_key_123"}
        )
        mock_cursor.sort.assert_called_once_with("timestamp", -1)  # DESCENDING constant
        mock_cursor.limit.assert_called_once_with(10)

    def test_get_messages_operation_failure(self, mocker):
        """Test message retrieval when MongoDB operation fails."""
        # Mock MongoDB collection to raise OperationFailure
        mock_collection = Mock()
        mock_collection.find.side_effect = OperationFailure("Query failed")

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.messages_collection = mock_collection

        messages = provider.get_messages_by_owner_key("test_public_key_123")

        assert messages == []
        mock_collection.find.assert_called_once_with(
            {"owner_key": "test_public_key_123"}
        )

    def test_get_messages_not_connected(self):
        """Test message retrieval when not connected to database."""
        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        # provider.messages_collection is None

        messages = provider.get_messages_by_owner_key("test_public_key_123")

        assert messages == []

    def test_health_check_success(self, mocker):
        """Test successful health check."""
        # Mock MongoDB client
        mock_client = Mock()
        mock_client.admin.command.return_value = None

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.client = mock_client

        result = provider.health_check()

        assert result is True
        mock_client.admin.command.assert_called_once_with("ping")

    def test_health_check_connection_failure(self, mocker):
        """Test health check when connection fails."""
        # Mock MongoDB client to raise ConnectionFailure
        mock_client = Mock()
        mock_client.admin.command.side_effect = ConnectionFailure("Ping failed")

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.client = mock_client

        result = provider.health_check()

        assert result is False
        mock_client.admin.command.assert_called_once_with("ping")

    def test_health_check_not_initialized(self):
        """Test health check when client is not initialized."""
        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        # provider.client is None

        result = provider.health_check()

        assert result is False

    def test_disconnect(self, mocker):
        """Test successful disconnection."""
        # Mock MongoDB client
        mock_client = Mock()

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.client = mock_client
        provider.database = Mock()
        provider.messages_collection = Mock()
        provider.config_collection = Mock()

        provider.disconnect()

        mock_client.close.assert_called_once()
        assert provider.client is None
        assert provider.database is None
        assert provider.messages_collection is None
        assert provider.config_collection is None

    def test_get_configuration_success(self, mocker):
        """Test successful configuration retrieval with direct structure."""
        # Mock MongoDB collection
        mock_collection = Mock()
        mock_config_doc = {
            "_id": Mock(),
            "environment": "production",
            "key": "value",  # Direct structure (no config_data wrapper)
        }
        mock_collection.find_one.return_value = mock_config_doc

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.config_collection = mock_collection

        config = provider.get_configuration("production")

        assert config == {"key": "value"}  # _id and environment are popped
        mock_collection.find_one.assert_called_once_with({"environment": "production"})

    def test_get_configuration_not_found(self, mocker):
        """Test configuration retrieval when configuration not found."""
        # Mock MongoDB collection
        mock_collection = Mock()
        mock_collection.find_one.return_value = None

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.config_collection = mock_collection

        config = provider.get_configuration("nonexistent")

        assert config is None
        mock_collection.find_one.assert_called_once_with({"environment": "nonexistent"})

    def test_upsert_configuration_success(self, mocker):
        """Test successful configuration upsert with direct structure."""
        # Mock MongoDB collection
        mock_collection = Mock()
        mock_result = Mock()
        mock_result.upserted_id = "test_config_id"
        mock_result.modified_count = 0
        mock_collection.replace_one.return_value = mock_result

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.config_collection = mock_collection

        config_data = {"key": "value"}
        result = provider.upsert_configuration("production", config_data)

        assert result is True
        # Verify replace_one is called with direct structure (no config_data wrapper)
        mock_collection.replace_one.assert_called_once_with(
            {"environment": "production"},
            {"environment": "production", "key": "value"},
            upsert=True,
        )

    def test_upsert_configuration_operation_failure(self, mocker):
        """Test configuration upsert when MongoDB operation fails."""
        # Mock MongoDB collection to raise OperationFailure
        mock_collection = Mock()
        mock_collection.replace_one.side_effect = OperationFailure("Replace failed")

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.config_collection = mock_collection

        config_data = {"key": "value"}
        result = provider.upsert_configuration("production", config_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_increment_turn_count_and_check_threshold_success(self, mocker):
        """Test successful turn count increment and threshold check."""
        # Mock MongoDB collection and find_one_and_update result
        mock_collection = Mock()
        mock_result = {"_id": "test_id", "public_key": "0x123", "turn_count": 5}
        mock_collection.find_one_and_update.return_value = mock_result
        mock_collection.update_one = Mock()

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.identities_collection = mock_collection

        should_learn, new_count = await provider.increment_turn_count_and_check_threshold(
            "0x123", threshold=20
        )

        assert should_learn is False  # 5 % 20 != 0
        assert new_count == 5
        mock_collection.find_one_and_update.assert_called_once_with(
            {"public_key": "0x123"},
            {"$inc": {"turn_count": 1}},
            return_document=mocker.ANY,
            projection={"turn_count": 1}
        )
        mock_collection.update_one.assert_not_called()  # No reset

    @pytest.mark.asyncio
    async def test_increment_turn_count_and_check_threshold_reached(self, mocker):
        """Test turn count increment when threshold is reached."""
        mock_collection = Mock()
        # Simulate count = 19 before increment, after increment = 20
        mock_result = {"_id": "test_id", "public_key": "0x123", "turn_count": 20}
        mock_collection.find_one_and_update.return_value = mock_result
        mock_collection.update_one = Mock()

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.identities_collection = mock_collection

        should_learn, new_count = await provider.increment_turn_count_and_check_threshold(
            "0x123", threshold=20
        )

        assert should_learn is True  # 20 % 20 == 0
        assert new_count == 20
        mock_collection.update_one.assert_called_once_with(
            {"public_key": "0x123"},
            {"$set": {"turn_count": 0}}
        )

    @pytest.mark.asyncio
    async def test_increment_turn_count_and_check_threshold_no_identity(self, mocker):
        """Test turn count increment when identity doesn't exist."""
        mock_collection = Mock()
        mock_collection.find_one_and_update.return_value = None

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.identities_collection = mock_collection

        should_learn, new_count = await provider.increment_turn_count_and_check_threshold(
            "0x123", threshold=20
        )

        assert should_learn is False
        assert new_count == 0
        mock_collection.update_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_increment_turn_count_and_check_threshold_not_connected(self):
        """Test turn count increment when not connected to database."""
        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        # provider.identities_collection is None

        should_learn, new_count = await provider.increment_turn_count_and_check_threshold(
            "0x123", threshold=20
        )

        assert should_learn is False
        assert new_count == 0

    @pytest.mark.asyncio
    async def test_increment_turn_count_and_check_threshold_operation_failure(self, mocker):
        """Test turn count increment when MongoDB operation fails."""
        mock_collection = Mock()
        mock_collection.find_one_and_update.side_effect = OperationFailure("Update failed")

        provider = MongoProvider("mongodb://localhost:27017", "test_db")
        provider.identities_collection = mock_collection

        should_learn, new_count = await provider.increment_turn_count_and_check_threshold(
            "0x123", threshold=20
        )

        assert should_learn is False
        assert new_count == 0
