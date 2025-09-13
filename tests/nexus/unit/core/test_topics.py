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
            if not attr_name.startswith('_') and not callable(getattr(Topics, attr_name)):
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
            if not attr_name.startswith('_') and not callable(getattr(Topics, attr_name)):
                attr_value = getattr(Topics, attr_name)
                assert isinstance(attr_value, str), (
                    f"Topic '{attr_name}' is not a string: {type(attr_value)}"
                )
                
    def test_topics_follow_naming_convention(self):
        """Test that topics follow the expected naming convention (dot-separated)."""
        for attr_name in dir(Topics):
            if not attr_name.startswith('_') and not callable(getattr(Topics, attr_name)):
                attr_value = getattr(Topics, attr_name)
                # All topics should be dot-separated strings
                assert '.' in attr_value, (
                    f"Topic '{attr_name}' value '{attr_value}' does not follow dot-separated naming convention"
                )
                
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
            "ui.events"
        ]
        
        for expected_topic in expected_topics:
            # Check if the topic value exists in any of the class attributes
            found = False
            for attr_name in dir(Topics):
                if not attr_name.startswith('_') and not callable(getattr(Topics, attr_name)):
                    if getattr(Topics, attr_name) == expected_topic:
                        found = True
                        break
            
            assert found, f"Expected topic '{expected_topic}' not found in Topics class"
            
    def test_no_empty_topic_values(self):
        """Test that no topic values are empty strings."""
        for attr_name in dir(Topics):
            if not attr_name.startswith('_') and not callable(getattr(Topics, attr_name)):
                attr_value = getattr(Topics, attr_name)
                assert attr_value.strip() != "", (
                    f"Topic '{attr_name}' has an empty value"
                )
                
    def test_topic_class_can_be_instantiated(self):
        """Test that Topics class can be instantiated but doesn't need to be."""
        # The Topics class is a namespace, but Python allows instantiation
        topics_instance = Topics()
        assert topics_instance is not None