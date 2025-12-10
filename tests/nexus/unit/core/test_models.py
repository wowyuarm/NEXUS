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
        owner_key = f"public_key_{uuid.uuid4().hex}"

        message = Message(
            run_id=run_id, owner_key=owner_key, role=Role.HUMAN, content="Hello, world!"
        )

        # Verify default values
        assert message.id.startswith("msg_")
        assert len(message.id) == 36  # "msg_" + 32 hex chars
        assert message.run_id == run_id
        assert message.owner_key == owner_key
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
        owner_key = f"public_key_{uuid.uuid4().hex}"

        run = Run(owner_key=owner_key)

        # Verify default values
        assert run.id.startswith("run_")
        assert len(run.id) == 36  # "run_" + 32 hex chars
        assert run.owner_key == owner_key
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
        owner_key = f"public_key_{uuid.uuid4().hex}"

        run = Run(owner_key=owner_key, status=RunStatus.COMPLETED)

        assert run.status == RunStatus.COMPLETED

    def test_run_with_history(self):
        """Test that Run can be created with initial history."""
        owner_key = f"public_key_{uuid.uuid4().hex}"
        run_id = f"run_{uuid.uuid4().hex}"

        message = Message(
            run_id=run_id,
            owner_key=owner_key,
            role=Role.HUMAN,
            content="Initial message",
        )

        run = Run(owner_key=owner_key, history=[message])

        assert len(run.history) == 1
        assert run.history[0] == message

    def test_run_with_tools_and_metadata(self):
        """Test that Run can be created with custom tools and metadata."""
        owner_key = f"public_key_{uuid.uuid4().hex}"

        run = Run(
            owner_key=owner_key,
            tools=[{"name": "test_tool", "args": {}}],
            metadata={"custom_field": "custom_value"},
        )

        assert run.tools == [{"name": "test_tool", "args": {}}]
        assert run.metadata == {"custom_field": "custom_value"}


class TestRoleEnum:
    """Test that Role enum has all expected values."""

    def test_role_enum_values(self):
        """Test that Role enum contains all expected role values."""
        expected_roles = ["HUMAN", "AI", "SYSTEM", "TOOL", "COMMAND"]

        # Get all Role enum values
        actual_roles = [role.value for role in Role]

        # Verify all expected roles are present
        for expected_role in expected_roles:
            assert (
                expected_role in actual_roles
            ), f"Role.{expected_role} not found in Role enum"

        # Verify no unexpected roles exist
        assert len(actual_roles) == len(expected_roles), (
            f"Role enum has {len(actual_roles)} values, expected {len(expected_roles)}. "
            f"Actual: {actual_roles}, Expected: {expected_roles}"
        )

    def test_role_enum_string_inheritance(self):
        """Test that Role enum inherits from str."""
        # Verify that Role values can be used as strings
        assert Role.HUMAN == "HUMAN"
        assert Role.AI == "AI"
        assert Role.SYSTEM == "SYSTEM"
        assert Role.TOOL == "TOOL"
        assert Role.COMMAND == "COMMAND"

        # Verify string operations work
        assert (
            str(Role.HUMAN) == "Role.HUMAN"
        )  # Enum __str__ returns the full representation
        assert Role.HUMAN.value == "HUMAN"  # .value returns the actual string value
        assert Role.HUMAN.lower() == "human"


class TestRunStatusEnum:
    """Test that RunStatus enum has all expected values."""

    def test_run_status_enum_values(self):
        """Test that RunStatus enum contains all expected status values."""
        expected_statuses = [
            "PENDING",
            "BUILDING_CONTEXT",
            "AWAITING_LLM_DECISION",
            "AWAITING_TOOL_RESULT",
            "GENERATING_RESPONSE",
            "COMPLETED",
            "FAILED",
            "TIMED_OUT",
        ]

        # Get all RunStatus enum values
        actual_statuses = [status.value for status in RunStatus]

        # Verify all expected statuses are present
        for expected_status in expected_statuses:
            assert (
                expected_status in actual_statuses
            ), f"RunStatus.{expected_status} not found in RunStatus enum"

        # Verify no unexpected statuses exist
        assert len(actual_statuses) == len(expected_statuses), (
            f"RunStatus enum has {len(actual_statuses)} values, expected {len(expected_statuses)}. "
            f"Actual: {actual_statuses}, Expected: {expected_statuses}"
        )

    def test_run_status_enum_string_inheritance(self):
        """Test that RunStatus enum inherits from str."""
        # Verify that RunStatus values can be used as strings
        assert RunStatus.PENDING == "PENDING"
        assert RunStatus.BUILDING_CONTEXT == "BUILDING_CONTEXT"
        assert RunStatus.AWAITING_LLM_DECISION == "AWAITING_LLM_DECISION"
        assert RunStatus.AWAITING_TOOL_RESULT == "AWAITING_TOOL_RESULT"
        assert RunStatus.GENERATING_RESPONSE == "GENERATING_RESPONSE"
        assert RunStatus.COMPLETED == "COMPLETED"
        assert RunStatus.FAILED == "FAILED"
        assert RunStatus.TIMED_OUT == "TIMED_OUT"

        # Verify string operations work
        assert (
            str(RunStatus.PENDING) == "RunStatus.PENDING"
        )  # Enum __str__ returns the full representation
        assert (
            RunStatus.PENDING.value == "PENDING"
        )  # .value returns the actual string value
        assert RunStatus.PENDING.lower() == "pending"


class TestMessageFieldValidation:
    """Test Message model field validation and edge cases."""

    def test_message_with_different_content_types(self):
        """Test that Message accepts different content types."""
        run_id = f"run_{uuid.uuid4().hex}"
        owner_key = f"public_key_{uuid.uuid4().hex}"

        # Test with string content
        msg_str = Message(
            run_id=run_id,
            owner_key=owner_key,
            role=Role.HUMAN,
            content="String content",
        )
        assert msg_str.content == "String content"

        # Test with dict content
        dict_content = {"key": "value", "nested": {"inner": "data"}}
        msg_dict = Message(
            run_id=run_id, owner_key=owner_key, role=Role.AI, content=dict_content
        )
        assert msg_dict.content == dict_content

        # Test with list content
        list_content = ["item1", "item2", {"nested": "item"}]
        msg_list = Message(
            run_id=run_id, owner_key=owner_key, role=Role.TOOL, content=list_content
        )
        assert msg_list.content == list_content

        # Test with None content
        msg_none = Message(
            run_id=run_id, owner_key=owner_key, role=Role.SYSTEM, content=None
        )
        assert msg_none.content is None

    def test_message_with_custom_metadata(self):
        """Test that Message properly handles custom metadata."""
        run_id = f"run_{uuid.uuid4().hex}"
        owner_key = f"public_key_{uuid.uuid4().hex}"

        custom_metadata = {
            "source": "test_suite",
            "priority": "high",
            "tags": ["test", "validation"],
            "nested": {"level": 2, "data": {"inner": "value"}},
        }

        message = Message(
            run_id=run_id,
            owner_key=owner_key,
            role=Role.COMMAND,
            content="Test with metadata",
            metadata=custom_metadata,
        )

        assert message.metadata == custom_metadata
        assert message.metadata["source"] == "test_suite"
        assert message.metadata["nested"]["level"] == 2


class TestRunFieldValidation:
    """Test Run model field validation and edge cases."""

    def test_run_with_different_status_values(self):
        """Test that Run can be created with all status values."""
        owner_key = f"public_key_{uuid.uuid4().hex}"

        # Test each status value
        for status in RunStatus:
            run = Run(owner_key=owner_key, status=status)
            assert run.status == status

    def test_run_iteration_count_increments(self):
        """Test that Run iteration_count can be set and modified."""
        owner_key = f"public_key_{uuid.uuid4().hex}"

        # Test with custom iteration count
        run = Run(owner_key=owner_key, iteration_count=5)
        assert run.iteration_count == 5

        # Test that we can modify it
        run.iteration_count += 1
        assert run.iteration_count == 6

    def test_run_with_complex_tools(self):
        """Test that Run can handle complex tool structures."""
        owner_key = f"public_key_{uuid.uuid4().hex}"

        complex_tools = [
            {
                "name": "web_search",
                "args": {"query": "test", "limit": 10},
                "metadata": {"timeout": 30},
            },
            {
                "name": "file_read",
                "args": {"path": "/tmp/test.txt"},
                "result": {"content": "file content", "size": 1024},
            },
        ]

        run = Run(owner_key=owner_key, tools=complex_tools)

        assert len(run.tools) == 2
        assert run.tools[0]["name"] == "web_search"
        assert run.tools[1]["args"]["path"] == "/tmp/test.txt"
