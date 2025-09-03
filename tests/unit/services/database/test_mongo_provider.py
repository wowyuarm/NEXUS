"""Unit tests for MongoProvider class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pymongo.errors import ConnectionFailure, OperationFailure
from pymongo.results import InsertOneResult

from nexus.services.database.providers.mongo import MongoProvider
from nexus.core.models import Message, Role
from datetime import datetime


class TestMongoProvider:
    """Test suite for MongoProvider functionality."""

    @pytest.fixture
    def mongo_provider(self):
        """Fixture providing a MongoProvider instance for testing."""
        return MongoProvider("mongodb://localhost:27017/test", "test_db")

    @pytest.fixture
    def sample_message(self):
        """Fixture providing a sample Message for testing."""
        return Message(
            id="msg_test_123",
            run_id="run_test_456",
            session_id="session_test_789",
            role=Role.HUMAN,
            content="Test message content",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            metadata={"test": "value"}
        )

    def test_connection_failure(self, mongo_provider, mocker):
        """Test that ConnectionFailure during connect() is caught and re-raised."""
        # Mock MongoClient to raise ConnectionFailure during ping
        mock_client = mocker.patch('pymongo.MongoClient')
        mock_admin = Mock()
        mock_admin.command.side_effect = ConnectionFailure("Connection failed")
        mock_client.return_value.admin = mock_admin

        # Assert that ConnectionFailure is re-raised
        with pytest.raises(ConnectionFailure):
            mongo_provider.connect()

    def test_insert_message_operation_failure(self, mongo_provider, sample_message, mocker):
        """Test that OperationFailure during insert_message() returns False and logs error."""
        # Mock the messages_collection.insert_one to raise OperationFailure
        mock_collection = Mock()
        mock_collection.insert_one.side_effect = OperationFailure("Insert operation failed", 123)
        
        # Set up the provider with mocked collection
        mongo_provider.messages_collection = mock_collection

        # Mock logger to capture error logs
        mock_logger = mocker.patch('nexus.services.database.providers.mongo.logger')

        # Call insert_message and assert it returns False
        result = mongo_provider.insert_message(sample_message)
        
        assert result is False
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0][0]
        assert "MongoDB operation failed during message insertion" in error_call_args
        assert "Insert operation failed" in error_call_args

    def test_get_messages_operation_failure(self, mongo_provider, mocker):
        """Test that OperationFailure during get_messages_by_session_id() returns empty list."""
        # Mock the messages_collection.find to raise OperationFailure
        mock_collection = Mock()
        mock_collection.find.side_effect = OperationFailure("Find operation failed", 456)
        
        # Set up the provider with mocked collection
        mongo_provider.messages_collection = mock_collection

        # Mock logger to capture error logs
        mock_logger = mocker.patch('nexus.services.database.providers.mongo.logger')

        # Call get_messages_by_session_id and assert it returns empty list
        result = mongo_provider.get_messages_by_session_id("test_session")
        
        assert result == []
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0][0]
        assert "MongoDB operation failed during message retrieval" in error_call_args
        assert "Find operation failed" in error_call_args

    def test_insert_message_success(self, mongo_provider, sample_message, mocker):
        """Test successful message insertion."""
        # Mock the insert_one operation to return successful result
        mock_result = Mock(spec=InsertOneResult)
        mock_result.inserted_id = "test_object_id"
        
        mock_collection = Mock()
        mock_collection.insert_one.return_value = mock_result
        
        mongo_provider.messages_collection = mock_collection

        # Mock logger to capture info logs
        mock_logger = mocker.patch('nexus.services.database.providers.mongo.logger')

        # Call insert_message and assert it returns True
        result = mongo_provider.insert_message(sample_message)
        
        assert result is True
        
        # Verify insert_one was called with correct arguments
        mock_collection.insert_one.assert_called_once()
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["id"] == "msg_test_123"
        assert call_args["run_id"] == "run_test_456"
        assert call_args["session_id"] == "session_test_789"
        assert call_args["content"] == "Test message content"
        
        # Verify success was logged
        mock_logger.info.assert_called_once()
        info_call_args = mock_logger.info.call_args[0][0]
        assert "Message inserted successfully" in info_call_args
        assert "msg_id=msg_test_123" in info_call_args
        assert "run_id=run_test_456" in info_call_args

    def test_get_messages_success(self, mongo_provider, mocker):
        """Test successful message retrieval."""
        # Mock the find operation to return sample messages
        mock_message_data = [
            {
                "_id": "object_id_1",
                "id": "msg_1",
                "session_id": "test_session",
                "content": "Message 1",
                "timestamp": datetime(2024, 1, 1, 12, 0, 0)
            },
            {
                "_id": "object_id_2", 
                "id": "msg_2",
                "session_id": "test_session",
                "content": "Message 2",
                "timestamp": datetime(2024, 1, 1, 12, 1, 0)
            }
        ]
        
        mock_cursor = Mock()
        mock_cursor.__iter__ = Mock(return_value=iter(mock_message_data))
        
        mock_collection = Mock()
        mock_collection.find.return_value.sort.return_value.limit.return_value = mock_cursor
        
        mongo_provider.messages_collection = mock_collection

        # Mock logger to capture info logs
        mock_logger = mocker.patch('nexus.services.database.providers.mongo.logger')

        # Call get_messages_by_session_id
        result = mongo_provider.get_messages_by_session_id("test_session", limit=10)
        
        # Verify result contains messages with _id converted to string
        assert len(result) == 2
        assert result[0]["_id"] == "object_id_1"
        assert result[0]["id"] == "msg_1"
        assert result[1]["_id"] == "object_id_2"
        assert result[1]["id"] == "msg_2"
        
        # Verify find was called with correct arguments
        mock_collection.find.assert_called_once_with({"session_id": "test_session"})
        mock_collection.find.return_value.sort.assert_called_once_with("timestamp", -1)
        mock_collection.find.return_value.sort.return_value.limit.assert_called_once_with(10)
        
        # Verify success was logged
        mock_logger.info.assert_called_once()
        info_call_args = mock_logger.info.call_args[0][0]
        assert "Retrieved 2 messages for session_id=test_session" in info_call_args

    def test_insert_message_not_connected(self, mongo_provider, sample_message, mocker):
        """Test insert_message returns False when not connected to MongoDB."""
        # Ensure messages_collection is None (not connected)
        mongo_provider.messages_collection = None

        # Mock logger to capture error logs
        mock_logger = mocker.patch('nexus.services.database.providers.mongo.logger')

        # Call insert_message and assert it returns False
        result = mongo_provider.insert_message(sample_message)
        
        assert result is False
        
        # Verify error was logged
        mock_logger.error.assert_called_once_with("MongoDB not connected. Cannot insert message.")

    def test_get_messages_not_connected(self, mongo_provider, mocker):
        """Test get_messages_by_session_id returns empty list when not connected to MongoDB."""
        # Ensure messages_collection is None (not connected)
        mongo_provider.messages_collection = None

        # Mock logger to capture error logs
        mock_logger = mocker.patch('nexus.services.database.providers.mongo.logger')

        # Call get_messages_by_session_id and assert it returns empty list
        result = mongo_provider.get_messages_by_session_id("test_session")
        
        assert result == []
        
        # Verify error was logged
        mock_logger.error.assert_called_once_with("MongoDB not connected. Cannot retrieve messages.")

    def test_disconnect(self, mongo_provider, mocker):
        """Test disconnect method closes the client connection."""
        # Mock the client
        mock_client = Mock()
        mongo_provider.client = mock_client
        mongo_provider.database = Mock()
        mongo_provider.messages_collection = Mock()

        # Mock logger to capture info logs
        mock_logger = mocker.patch('nexus.services.database.providers.mongo.logger')

        # Call disconnect
        mongo_provider.disconnect()
        
        # Verify client.close() was called
        mock_client.close.assert_called_once()
        
        # Verify all attributes are set to None
        assert mongo_provider.client is None
        assert mongo_provider.database is None
        assert mongo_provider.messages_collection is None
        
        # Verify disconnect was logged
        mock_logger.info.assert_called_once_with("MongoDB connection closed")

    def test_disconnect_no_client(self, mongo_provider, mocker):
        """Test disconnect method when no client exists."""
        # Ensure client is None
        mongo_provider.client = None

        # Mock logger
        mock_logger = mocker.patch('nexus.services.database.providers.mongo.logger')

        # Call disconnect - should not raise any errors
        mongo_provider.disconnect()
        
        # Verify no close calls were made and no errors logged
        mock_logger.info.assert_not_called()
        mock_logger.error.assert_not_called()