"""
Unit tests for WebSocket interface message parsing logic.

These tests verify that the extracted message parsing helper function
correctly handles different message types and edge cases.
"""

import pytest
import json
from nexus.interfaces.websocket import _parse_client_message, MESSAGE_TYPE_PING, MESSAGE_TYPE_USER_MESSAGE


class TestParseClientMessage:
    """Test the _parse_client_message helper function."""
    
    def test_parse_client_message_valid_user_message(self):
        """Test parsing a valid user message."""
        valid_user_message = json.dumps({
            "type": "user_message",
            "payload": {
                "content": "Hello, world!"
            }
        })

        result = _parse_client_message(valid_user_message)

        assert result["type"] == "user_message"
        assert result["payload"] == {"content": "Hello, world!", "client_timestamp": "", "client_timestamp_utc": "", "client_timezone_offset": 0}
        assert result["user_input"] == "Hello, world!"
        assert result["client_timestamp"] == ""
        
    def test_parse_client_message_valid_user_message_empty_content(self):
        """Test parsing a user message with empty content."""
        message_with_empty_content = json.dumps({
            "type": "user_message",
            "payload": {
                "content": ""
            }
        })

        result = _parse_client_message(message_with_empty_content)

        assert result["type"] == "user_message"
        assert result["payload"] == {"content": "", "client_timestamp": "", "client_timestamp_utc": "", "client_timezone_offset": 0}
        assert result["user_input"] == ""
        assert result["client_timestamp"] == ""
        
    def test_parse_client_message_valid_user_message_no_payload(self):
        """Test parsing a user message with no payload."""
        message_no_payload = json.dumps({
            "type": "user_message"
        })

        result = _parse_client_message(message_no_payload)

        assert result["type"] == "user_message"
        assert result["payload"] == {"content": "", "client_timestamp": "", "client_timestamp_utc": "", "client_timezone_offset": 0}
        assert result["user_input"] == ""
        assert result["client_timestamp"] == ""
        
    def test_parse_client_message_valid_ping(self):
        """Test parsing a valid ping message."""
        valid_ping_message = json.dumps({
            "type": "ping"
        })
        
        result = _parse_client_message(valid_ping_message)
        
        assert result["type"] == "ping"
        assert result["payload"] == {}
        
    def test_parse_client_message_ping_with_payload(self):
        """Test parsing a ping message with payload (should still work)."""
        ping_with_payload = json.dumps({
            "type": "ping",
            "payload": {
                "timestamp": "2023-01-01T00:00:00Z"
            }
        })
        
        result = _parse_client_message(ping_with_payload)
        
        assert result["type"] == "ping"
        assert result["payload"] == {"timestamp": "2023-01-01T00:00:00Z"}
        
    def test_parse_client_message_invalid_json(self):
        """Test parsing invalid JSON raises JSONDecodeError."""
        invalid_json = '{"type": "user_message", "payload": {"content": "Hello"'
        
        with pytest.raises(json.JSONDecodeError):
            _parse_client_message(invalid_json)
            
    def test_parse_client_message_invalid_json_syntax(self):
        """Test parsing JSON with syntax errors."""
        invalid_json_syntax = '{"type": "user_message",,}'
        
        with pytest.raises(json.JSONDecodeError):
            _parse_client_message(invalid_json_syntax)
            
    def test_parse_client_message_unknown_type(self):
        """Test parsing a message with unknown type."""
        unknown_type_message = json.dumps({
            "type": "unknown_type",
            "payload": {
                "data": "some data"
            }
        })
        
        result = _parse_client_message(unknown_type_message)
        
        assert result["type"] == "unknown"
        assert result["original_type"] == "unknown_type"
        assert "payload" not in result
        
    def test_parse_client_message_no_type_field(self):
        """Test parsing a message with no type field."""
        no_type_message = json.dumps({
            "payload": {
                "content": "Hello, world!"
            }
        })
        
        result = _parse_client_message(no_type_message)
        
        assert result["type"] == ""
        assert result["payload"] == {"content": "Hello, world!"}
        
    def test_parse_client_message_empty_type(self):
        """Test parsing a message with empty type field."""
        empty_type_message = json.dumps({
            "type": "",
            "payload": {
                "content": "Hello, world!"
            }
        })
        
        result = _parse_client_message(empty_type_message)
        
        assert result["type"] == ""
        assert result["payload"] == {"content": "Hello, world!"}
        
    def test_parse_client_message_null_type(self):
        """Test parsing a message with null type field."""
        null_type_message = json.dumps({
            "type": None,
            "payload": {
                "content": "Hello, world!"
            }
        })
        
        result = _parse_client_message(null_type_message)
        
        assert result["type"] == "unknown"
        assert result["original_type"] is None
        assert "payload" not in result
        
    def test_parse_client_message_complex_user_content(self):
        """Test parsing a user message with complex content."""
        complex_message = json.dumps({
            "type": "user_message",
            "payload": {
                "content": "Hello, world! 👋\nThis is a multi-line message with special characters: é, ñ, 中文"
            }
        })
        
        result = _parse_client_message(complex_message)
        
        assert result["type"] == "user_message"
        assert result["payload"]["content"] == "Hello, world! 👋\nThis is a multi-line message with special characters: é, ñ, 中文"
        assert result["user_input"] == "Hello, world! 👋\nThis is a multi-line message with special characters: é, ñ, 中文"
        
    def test_parse_client_message_extra_fields_ignored(self):
        """Test that extra fields in the message are ignored appropriately."""
        message_with_extra_fields = json.dumps({
            "type": "user_message",
            "payload": {
                "content": "Hello, world!"
            },
            "extra_field": "should be ignored",
            "another_field": 12345
        })
        
        result = _parse_client_message(message_with_extra_fields)
        
        assert result["type"] == "user_message"
        assert result["payload"] == {"content": "Hello, world!", "client_timestamp": "", "client_timestamp_utc": "", "client_timezone_offset": 0}
        assert result["user_input"] == "Hello, world!"
        assert result["client_timestamp"] == ""
        # Extra fields should not appear in the result
        assert "extra_field" not in result
        assert "another_field" not in result