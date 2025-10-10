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
            owner_key="test_session",
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
            owner_key="test_session",
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


class TestNexusBusRunForever:
    """Test NexusBus run_forever functionality."""
    
    @pytest.mark.asyncio
    async def test_run_forever_with_no_topics_idles(self):
        """Test that run_forever idles indefinitely when no topics are registered."""
        bus = NexusBus()
        
        # Create a task that will be cancelled after a short time
        task = asyncio.create_task(bus.run_forever())
        
        # Let it run for a brief moment
        await asyncio.sleep(0.01)
        
        # Cancel the task
        task.cancel()
        
        # Verify it was cancelled (not completed naturally)
        with pytest.raises(asyncio.CancelledError):
            await task
            
    @pytest.mark.asyncio
    async def test_run_forever_starts_listeners_for_topics(self):
        """Test that run_forever starts listeners for all registered topics."""
        bus = NexusBus()
        topic1 = "test.topic1"
        topic2 = "test.topic2"
        
        # Subscribe handlers to create topics
        async def handler1(message: Message) -> None:
            pass
            
        async def handler2(message: Message) -> None:
            pass
        
        bus.subscribe(topic1, handler1)
        bus.subscribe(topic2, handler2)
        
        # Mock the _listener method to track calls
        with patch.object(bus, '_listener', new_callable=AsyncMock) as mock_listener:
            # Create a task and cancel it quickly
            task = asyncio.create_task(bus.run_forever())
            await asyncio.sleep(0.01)  # Let it start
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Verify listeners were started for both topics
            assert mock_listener.call_count == 2
            call_args = [call[0] for call in mock_listener.call_args_list]
            topics_called = [args[0] for args in call_args]
            
            assert topic1 in topics_called
            assert topic2 in topics_called


class TestNexusBusListener:
    """Test NexusBus _listener functionality."""
    
    @pytest.mark.asyncio
    async def test_listener_processes_messages_and_calls_handlers(self):
        """Test that _listener processes messages and calls all handlers."""
        bus = NexusBus()
        topic = "test.topic"
        
        # Track handler calls
        handler1_called = False
        handler2_called = False
        received_messages = []
        
        async def handler1(message: Message) -> None:
            nonlocal handler1_called
            handler1_called = True
            received_messages.append(("handler1", message))
            
        async def handler2(message: Message) -> None:
            nonlocal handler2_called
            handler2_called = True
            received_messages.append(("handler2", message))
        
        # Subscribe handlers
        bus.subscribe(topic, handler1)
        bus.subscribe(topic, handler2)
        
        # Create test message
        message = Message(
            run_id="test_run",
            owner_key="test_session",
            role=Role.HUMAN,
            content="Test message"
        )
        
        # Start listener in background
        queue = bus._queues[topic]
        listener_task = asyncio.create_task(bus._listener(topic, queue))
        
        # Send message to queue
        await queue.put(message)
        
        # Give listener time to process
        await asyncio.sleep(0.01)
        
        # Cancel listener
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass
        
        # Verify both handlers were called
        assert handler1_called
        assert handler2_called
        assert len(received_messages) == 2
        
        # Verify the message was passed to both handlers
        handler_names = [msg[0] for msg in received_messages]
        assert "handler1" in handler_names
        assert "handler2" in handler_names
        
        # Verify the same message was passed to both
        for _, received_msg in received_messages:
            assert received_msg.id == message.id
            assert received_msg.content == message.content
            
    @pytest.mark.asyncio
    async def test_listener_handles_handler_exceptions_gracefully(self):
        """Test that _listener continues processing even when handlers raise exceptions."""
        bus = NexusBus()
        topic = "test.topic"
        
        # Track calls
        good_handler_called = False
        
        async def failing_handler(message: Message) -> None:
            raise ValueError("Handler failed")
            
        async def good_handler(message: Message) -> None:
            nonlocal good_handler_called
            good_handler_called = True
        
        # Subscribe both handlers
        bus.subscribe(topic, failing_handler)
        bus.subscribe(topic, good_handler)
        
        # Create test message
        message = Message(
            run_id="test_run",
            owner_key="test_session",
            role=Role.HUMAN,
            content="Test message"
        )
        
        # Start listener in background
        queue = bus._queues[topic]
        listener_task = asyncio.create_task(bus._listener(topic, queue))
        
        # Send message to queue
        await queue.put(message)
        
        # Give listener time to process and handle exceptions
        await asyncio.sleep(0.01)
        
        # Cancel listener
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass
        
        # Verify the good handler was still called despite the failing one
        assert good_handler_called
        
    @pytest.mark.asyncio
    async def test_listener_marks_queue_tasks_done(self):
        """Test that _listener properly calls task_done on the queue."""
        bus = NexusBus()
        topic = "test.topic"
        
        async def handler(message: Message) -> None:
            pass
        
        bus.subscribe(topic, handler)
        
        # Create test message
        message = Message(
            run_id="test_run",
            owner_key="test_session",
            role=Role.HUMAN,
            content="Test message"
        )
        
        # Mock the queue's task_done method
        queue = bus._queues[topic]
        with patch.object(queue, 'task_done') as mock_task_done:
            # Start listener in background
            listener_task = asyncio.create_task(bus._listener(topic, queue))
            
            # Send message to queue
            await queue.put(message)
            
            # Give listener time to process
            await asyncio.sleep(0.01)
            
            # Cancel listener
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
            
            # Verify task_done was called
            mock_task_done.assert_called_once()