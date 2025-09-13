"""
Unit tests for core models (Message and Run).

These tests verify that Pydantic models have the correct default behaviors
and field types as specified in the core models module.
"""

import pytest
import uuid
from datetime import datetime, timezone
from nexus.core.models import Message, Run, Role, RunStatus


class TestMessageDefaults:
    """Test that Message model has correct default values."""
    
    def test_message_defaults(self):
        """Test that Message instance with minimal fields has correct defaults."""
        # Create a Message with only required fields
        run_id = f"run_{uuid.uuid4().hex}"
        session_id = f"session_{uuid.uuid4().hex}"
        
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.HUMAN,
            content="Hello, world!"
        )
        
        # Verify default values
        assert message.id.startswith("msg_")
        assert len(message.id) == 36  # "msg_" + 32 hex chars
        assert message.run_id == run_id
        assert message.session_id == session_id
        assert message.role == Role.HUMAN
        assert message.content == "Hello, world!"
        assert isinstance(message.timestamp, datetime)
        assert message.timestamp.tzinfo == timezone.utc
        assert message.metadata == {}
        
        # Verify that the id is a valid UUID (without the prefix)
        uuid_part = message.id[4:]
        uuid.UUID(uuid_part)  # Will raise ValueError if invalid


class TestRunDefaults:
    """Test that Run model has correct default values."""
    
    def test_run_defaults(self):
        """Test that Run instance with minimal fields has correct defaults."""
        # Create a Run with only required fields
        session_id = f"session_{uuid.uuid4().hex}"
        
        run = Run(session_id=session_id)
        
        # Verify default values
        assert run.id.startswith("run_")
        assert len(run.id) == 36  # "run_" + 32 hex chars
        assert run.session_id == session_id
        assert run.status == RunStatus.PENDING
        assert run.history == []
        assert run.iteration_count == 0
        assert run.tools == []
        assert run.metadata == {}
        
        # Verify that the id is a valid UUID (without the prefix)
        uuid_part = run.id[4:]
        uuid.UUID(uuid_part)  # Will raise ValueError if invalid
        
    def test_run_with_custom_status(self):
        """Test that Run can be created with custom status."""
        session_id = f"session_{uuid.uuid4().hex}"
        
        run = Run(
            session_id=session_id,
            status=RunStatus.COMPLETED
        )
        
        assert run.status == RunStatus.COMPLETED
        
    def test_run_with_history(self):
        """Test that Run can be created with initial history."""
        session_id = f"session_{uuid.uuid4().hex}"
        run_id = f"run_{uuid.uuid4().hex}"
        
        message = Message(
            run_id=run_id,
            session_id=session_id,
            role=Role.HUMAN,
            content="Initial message"
        )
        
        run = Run(
            session_id=session_id,
            history=[message]
        )
        
        assert len(run.history) == 1
        assert run.history[0] == message
        
    def test_run_with_tools_and_metadata(self):
        """Test that Run can be created with custom tools and metadata."""
        session_id = f"session_{uuid.uuid4().hex}"
        
        run = Run(
            session_id=session_id,
            tools=[{"name": "test_tool", "args": {}}],
            metadata={"custom_field": "custom_value"}
        )
        
        assert run.tools == [{"name": "test_tool", "args": {}}]
        assert run.metadata == {"custom_field": "custom_value"}