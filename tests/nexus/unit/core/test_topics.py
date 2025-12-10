"""
Unit tests for Topics class to ensure topic constant uniqueness and integrity.

These tests verify that all topic constants are unique and properly defined.
"""

import pytest
from nexus.core.topics import Topics


class TestTopicsIntegrity:
    """Test that Topics class maintains topic integrity."""

    def test_topic_values_are_unique(self):
        """Test that all topic constant values are unique."""
        # Get all topic values from the Topics class
        topic_values = []

        # Collect all topic values from the class attributes
        for attr_name in dir(Topics):
            # Skip private/dunder attributes and methods
            if not attr_name.startswith("_") and not callable(
                getattr(Topics, attr_name)
            ):
                attr_value = getattr(Topics, attr_name)
                # Only include string values (our topics)
                if isinstance(attr_value, str):
                    topic_values.append(attr_value)

        # Convert to set to check for uniqueness
        unique_topics = set(topic_values)

        # Assert that all values are unique
        assert len(topic_values) == len(unique_topics), (
            f"Found duplicate topic values. Original: {len(topic_values)}, "
            f"Unique: {len(unique_topics)}. Duplicate values: "
            f"{[x for x in topic_values if topic_values.count(x) > 1]}"
        )

    def test_all_topics_are_strings(self):
        """Test that all topic attributes are strings."""
        for attr_name in dir(Topics):
            if not attr_name.startswith("_") and not callable(
                getattr(Topics, attr_name)
            ):
                attr_value = getattr(Topics, attr_name)
                assert isinstance(
                    attr_value, str
                ), f"Topic '{attr_name}' is not a string: {type(attr_value)}"

    def test_topics_follow_naming_convention(self):
        """Test that topics follow the expected naming convention (dot-separated)."""
        for attr_name in dir(Topics):
            if not attr_name.startswith("_") and not callable(
                getattr(Topics, attr_name)
            ):
                attr_value = getattr(Topics, attr_name)
                # All topics should be dot-separated strings
                assert (
                    "." in attr_value
                ), f"Topic '{attr_name}' value '{attr_value}' does not follow dot-separated naming convention"

    def test_expected_topics_exist(self):
        """Test that expected topics are defined in the Topics class."""
        expected_topics = [
            "runs.new",
            "context.build.request",
            "context.build.response",
            "llm.requests",
            "llm.results",
            "tools.requests",
            "tools.results",
            "ui.events",
            "system.command",
            "command.result",
        ]

        for expected_topic in expected_topics:
            # Check if the topic value exists in any of the class attributes
            found = False
            for attr_name in dir(Topics):
                if not attr_name.startswith("_") and not callable(
                    getattr(Topics, attr_name)
                ):
                    if getattr(Topics, attr_name) == expected_topic:
                        found = True
                        break

            assert found, f"Expected topic '{expected_topic}' not found in Topics class"

    def test_no_empty_topic_values(self):
        """Test that no topic values are empty strings."""
        for attr_name in dir(Topics):
            if not attr_name.startswith("_") and not callable(
                getattr(Topics, attr_name)
            ):
                attr_value = getattr(Topics, attr_name)
                assert (
                    attr_value.strip() != ""
                ), f"Topic '{attr_name}' has an empty value"

    def test_topic_class_can_be_instantiated(self):
        """Test that Topics class can be instantiated but doesn't need to be."""
        # The Topics class is a namespace, but Python allows instantiation
        topics_instance = Topics()
        assert topics_instance is not None

    def test_specific_topic_constants_exist(self):
        """Test that specific topic constants are properly defined."""
        # Test run lifecycle topics
        assert hasattr(Topics, "RUNS_NEW")
        assert Topics.RUNS_NEW == "runs.new"

        # Test context building topics
        assert hasattr(Topics, "CONTEXT_BUILD_REQUEST")
        assert Topics.CONTEXT_BUILD_REQUEST == "context.build.request"
        assert hasattr(Topics, "CONTEXT_BUILD_RESPONSE")
        assert Topics.CONTEXT_BUILD_RESPONSE == "context.build.response"

        # Test LLM interaction topics
        assert hasattr(Topics, "LLM_REQUESTS")
        assert Topics.LLM_REQUESTS == "llm.requests"
        assert hasattr(Topics, "LLM_RESULTS")
        assert Topics.LLM_RESULTS == "llm.results"

        # Test tool execution topics
        assert hasattr(Topics, "TOOLS_REQUESTS")
        assert Topics.TOOLS_REQUESTS == "tools.requests"
        assert hasattr(Topics, "TOOLS_RESULTS")
        assert Topics.TOOLS_RESULTS == "tools.results"

        # Test UI topics
        assert hasattr(Topics, "UI_EVENTS")
        assert Topics.UI_EVENTS == "ui.events"

        # Test command system topics
        assert hasattr(Topics, "SYSTEM_COMMAND")
        assert Topics.SYSTEM_COMMAND == "system.command"
        assert hasattr(Topics, "COMMAND_RESULT")
        assert Topics.COMMAND_RESULT == "command.result"

    def test_topic_constants_are_class_attributes(self):
        """Test that all topic constants are class attributes, not instance attributes."""
        # All topics should be accessible without instantiation
        assert Topics.RUNS_NEW == "runs.new"
        assert Topics.CONTEXT_BUILD_REQUEST == "context.build.request"
        assert Topics.CONTEXT_BUILD_RESPONSE == "context.build.response"
        assert Topics.LLM_REQUESTS == "llm.requests"
        assert Topics.LLM_RESULTS == "llm.results"
        assert Topics.TOOLS_REQUESTS == "tools.requests"
        assert Topics.TOOLS_RESULTS == "tools.results"
        assert Topics.UI_EVENTS == "ui.events"
        assert Topics.SYSTEM_COMMAND == "system.command"
        assert Topics.COMMAND_RESULT == "command.result"

    def test_topic_grouping_by_prefix(self):
        """Test that topics are properly grouped by their prefix."""
        # Collect all topics by prefix
        topic_groups = {}

        for attr_name in dir(Topics):
            if not attr_name.startswith("_") and not callable(
                getattr(Topics, attr_name)
            ):
                attr_value = getattr(Topics, attr_name)
                if isinstance(attr_value, str) and "." in attr_value:
                    prefix = attr_value.split(".")[0]
                    if prefix not in topic_groups:
                        topic_groups[prefix] = []
                    topic_groups[prefix].append(attr_value)

        # Verify expected topic groups exist
        expected_prefixes = [
            "runs",
            "context",
            "llm",
            "tools",
            "ui",
            "system",
            "command",
        ]

        for expected_prefix in expected_prefixes:
            assert (
                expected_prefix in topic_groups
            ), f"Topic group '{expected_prefix}' not found. Available groups: {list(topic_groups.keys())}"

        # Verify specific groups have expected topics
        assert "runs.new" in topic_groups["runs"]
        assert "context.build.request" in topic_groups["context"]
        assert "context.build.response" in topic_groups["context"]
        assert "llm.requests" in topic_groups["llm"]
        assert "llm.results" in topic_groups["llm"]
        assert "tools.requests" in topic_groups["tools"]
        assert "tools.results" in topic_groups["tools"]
        assert "ui.events" in topic_groups["ui"]
        assert "system.command" in topic_groups["system"]
        assert "command.result" in topic_groups["command"]
