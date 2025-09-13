"""
Unit tests for NexusBus internal state management and boundary conditions.

These tests verify that the NexusBus correctly manages its internal data structures
and handles edge cases gracefully.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Role


class TestNexusBusInternalState:
    """Test NexusBus internal state management."""
    
    def test_subscribe_creates_internal_structures(self):
        """Test that subscribing creates queues and subscriber lists."""
        bus = NexusBus()
        topic = "test.topic"
        
        # Create a mock async handler
        async def mock_handler(message: Message) -> None:
            pass
        
        # Initially, no internal structures should exist
        assert topic not in bus._queues
        assert topic not in bus._subscribers
        
        # Subscribe to the topic
        bus.subscribe(topic, mock_handler)
        
        # Verify internal structures were created
        assert topic in bus._queues
        assert topic in bus._subscribers
        assert isinstance(bus._queues[topic], asyncio.Queue)
        assert isinstance(bus._subscribers[topic], list)
        assert len(bus._subscribers[topic]) == 1
        assert bus._subscribers[topic][0] == mock_handler
        
    def test_subscribe_multiple_handlers(self):
        """Test that multiple handlers can subscribe to the same topic."""
        bus = NexusBus()
        topic = "test.topic"
        
        # Create mock async handlers
        async def handler1(message: Message) -> None:
            pass
            
        async def handler2(message: Message) -> None:
            pass
        
        # Subscribe multiple handlers to the same topic
        bus.subscribe(topic, handler1)
        bus.subscribe(topic, handler2)
        
        # Verify both handlers are registered
        assert len(bus._subscribers[topic]) == 2
        assert handler1 in bus._subscribers[topic]
        assert handler2 in bus._subscribers[topic]
        
        # Verify only one queue was created
        assert len(bus._queues) == 1
        assert topic in bus._queues
        
    def test_publish_to_unsubscribed_topic_is_silent(self):
        """Test that publishing to an unsubscribed topic doesn't raise exceptions."""
        bus = NexusBus()
        topic = "unsubscribed.topic"
        
        # Create a test message
        message = Message(
            run_id="test_run",
            session_id="test_session",
            role=Role.HUMAN,
            content="Test message"
        )
        
        # Publishing to a topic with no subscribers should not raise an exception
        # This test passes if no exception is raised
        with patch('asyncio.Queue.put', new_callable=AsyncMock) as mock_put:
            asyncio.run(bus.publish(topic, message))
            
            # Since the topic doesn't exist, put should not be called
            mock_put.assert_not_called()
            
    def test_publish_to_subscribed_topic_enqueues_message(self):
        """Test that publishing to a subscribed topic enqueues the message."""
        bus = NexusBus()
        topic = "test.topic"
        
        # Subscribe a mock handler first
        async def mock_handler(message: Message) -> None:
            pass
        
        bus.subscribe(topic, mock_handler)
        
        # Create a test message
        message = Message(
            run_id="test_run",
            session_id="test_session",
            role=Role.HUMAN,
            content="Test message"
        )
        
        # Publish to the topic
        with patch.object(bus._queues[topic], 'put', new_callable=AsyncMock) as mock_put:
            asyncio.run(bus.publish(topic, message))
            
            # Verify the message was enqueued
            mock_put.assert_called_once_with(message)
            
    def test_bus_initialization_state(self):
        """Test that NexusBus initializes with empty internal structures."""
        bus = NexusBus()
        
        # Verify initial state
        assert bus._queues == {}
        assert bus._subscribers == {}
        
    def test_multiple_topics_isolation(self):
        """Test that different topics maintain separate internal structures."""
        bus = NexusBus()
        topic1 = "topic1"
        topic2 = "topic2"
        
        async def handler1(message: Message) -> None:
            pass
            
        async def handler2(message: Message) -> None:
            pass
        
        # Subscribe to different topics
        bus.subscribe(topic1, handler1)
        bus.subscribe(topic2, handler2)
        
        # Verify topics are isolated
        assert topic1 in bus._queues
        assert topic2 in bus._queues
        assert topic1 in bus._subscribers
        assert topic2 in bus._subscribers
        
        # Verify handlers are correctly assigned to their topics
        assert len(bus._subscribers[topic1]) == 1
        assert len(bus._subscribers[topic2]) == 1
        assert bus._subscribers[topic1][0] == handler1
        assert bus._subscribers[topic2][0] == handler2
        
        # Verify queues are separate
        assert bus._queues[topic1] is not bus._queues[topic2]