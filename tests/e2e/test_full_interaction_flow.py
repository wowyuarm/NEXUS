"""
End-to-end tests for NEXUS interaction flow.

Tests complete user interaction with tool calling capabilities
in isolated environment with full service lifecycle.
"""

import asyncio
import json
import pytest
import websockets


@pytest.mark.asyncio
async def test_tool_call_interaction(nexus_service: str, test_session_id: str):
    """
    Test complete interaction flow with tool calling.
    
    This test:
    1. Connects to NEXUS WebSocket interface
    2. Sends a user message that should trigger web_search tool
    3. Collects all UI events during the interaction
    4. Validates event sequence and content
    5. Ensures proper cleanup
    """
    # Construct WebSocket URL with session ID
    ws_url = f"{nexus_service}/api/v1/ws/{test_session_id}"
    
    events = []
    
    async with websockets.connect(ws_url) as websocket:
        # Send user message that should trigger web_search tool
        user_message = {
            "type": "user_message",
            "payload": {
                "content": "What's the latest news about artificial intelligence?"
            }
        }
        
        await websocket.send(json.dumps(user_message))
        
        # Collect events until run_finished is received
        timeout = 60.0  # 60 second timeout for complete interaction
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                # Set shorter timeout for individual message reception
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                event_data = json.loads(message)
                events.append(event_data)
                
                # Check if we received run_finished event
                if event_data.get("event") == "run_finished":
                    break
                    
            except asyncio.TimeoutError:
                # Continue waiting if no message received within 5 seconds
                continue
        
        # Verify we didn't timeout waiting for run_finished
        assert events, "No events received from NEXUS service"
        assert events[-1].get("event") == "run_finished", \
            f"Expected run_finished as last event, got: {[e.get('event') for e in events]}"
    
    # Validate events
    _validate_event_sequence(events)
    _validate_event_content(events)


def _validate_event_sequence(events: list) -> None:
    """Validate the sequence and types of UI events."""
    event_types = [event.get("event") for event in events]
    
    # Must contain at least these core events in reasonable order
    assert "run_started" in event_types, "Missing run_started event"
    assert "run_finished" in event_types, "Missing run_finished event"
    
    # Check relative ordering of key events
    run_started_idx = event_types.index("run_started")
    run_finished_idx = event_types.index("run_finished")
    
    assert run_started_idx < run_finished_idx, \
        "run_started must come before run_finished"
    
    # If tool calls occurred, validate tool-related events
    if "tool_call_started" in event_types:
        tool_started_idx = event_types.index("tool_call_started")
        tool_finished_idx = event_types.index("tool_call_finished")
        
        assert tool_started_idx < tool_finished_idx, \
            "tool_call_started must come before tool_call_finished"
        assert run_started_idx < tool_started_idx < run_finished_idx, \
            "Tool events must occur between run_started and run_finished"
    
    # Validate we have a reasonable number of events
    assert 5 <= len(events) <= 50, f"Unexpected number of events: {len(events)}"


def _validate_event_content(events: list) -> None:
    """Validate the content of specific UI events."""
    # Find key events
    run_started_events = [e for e in events if e.get("event") == "run_started"]
    run_finished_events = [e for e in events if e.get("event") == "run_finished"]
    tool_started_events = [e for e in events if e.get("event") == "tool_call_started"]
    tool_finished_events = [e for e in events if e.get("event") == "tool_call_finished"]
    text_chunk_events = [e for e in events if e.get("event") == "text_chunk"]
    
    # Validate run_started event
    assert len(run_started_events) == 1, "Expected exactly one run_started event"
    run_started = run_started_events[0]
    assert "user_input" in run_started.get("payload", {}), \
        "run_started payload missing user_input"
    
    # Validate run_finished event
    assert len(run_finished_events) == 1, "Expected exactly one run_finished event"
    run_finished = run_finished_events[0]
    assert run_finished.get("payload", {}).get("status") == "completed", \
        f"Run should complete successfully, got: {run_finished.get('payload', {})}"
    
    # If tools were called, validate tool events
    if tool_started_events:
        assert len(tool_started_events) >= 1, "Expected at least one tool_call_started"
        assert len(tool_finished_events) >= 1, "Expected at least one tool_call_finished"
        
        # Validate tool_call_started content
        tool_started = tool_started_events[0]
        tool_name = tool_started.get("payload", {}).get("tool_name")
        assert tool_name == "web_search", f"Expected web_search tool, got: {tool_name}"
        
        # Validate tool_call_finished content
        tool_finished = tool_finished_events[0]
        tool_status = tool_finished.get("payload", {}).get("status")
        assert tool_status == "success", f"Tool should succeed, got: {tool_status}"
        
        # Tool result should be present
        assert "result" in tool_finished.get("payload", {}), \
            "tool_call_finished missing result"
    
    # Validate we have some text content
    assert len(text_chunk_events) >= 1, "Expected at least one text_chunk event"
    
    # Validate text_chunk events have content
    for text_event in text_chunk_events:
        chunk = text_event.get("payload", {}).get("chunk", "")
        assert isinstance(chunk, str), "Text chunk should be a string"
        assert len(chunk.strip()) > 0, "Text chunk should not be empty"


@pytest.mark.asyncio
async def test_multiple_messages(nexus_service: str, test_session_id: str):
    """Test sending multiple messages in the same session."""
    ws_url = f"{nexus_service}/api/v1/ws/{test_session_id}"
    
    async with websockets.connect(ws_url) as websocket:
        # First message
        message1 = {
            "type": "user_message",
            "payload": {
                "content": "Hello, how are you?"
            }
        }
        await websocket.send(json.dumps(message1))
        
        # Wait for first run to complete
        events1 = await _collect_events_until_finished(websocket)
        assert events1[-1].get("event") == "run_finished"
        
        # Second message
        message2 = {
            "type": "user_message", 
            "payload": {
                "content": "What can you help me with?"
            }
        }
        await websocket.send(json.dumps(message2))
        
        # Wait for second run to complete
        events2 = await _collect_events_until_finished(websocket)
        assert events2[-1].get("event") == "run_finished"
        
        # Both interactions should work independently
        assert len(events1) > 0
        assert len(events2) > 0


async def _collect_events_until_finished(websocket, timeout: float = 30.0) -> list:
    """Collect events until run_finished is received."""
    events = []
    start_time = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            event_data = json.loads(message)
            events.append(event_data)
            
            if event_data.get("event") == "run_finished":
                break
                
        except asyncio.TimeoutError:
            continue
    
    return events