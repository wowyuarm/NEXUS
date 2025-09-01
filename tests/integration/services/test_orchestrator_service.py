"""Integration tests for OrchestratorService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from nexus.core.models import Message, Role, Run, RunStatus
from nexus.core.topics import Topics
from nexus.services.orchestrator import OrchestratorService


class TestOrchestratorService:
    """Test suite for OrchestratorService integration behavior."""

    @pytest.fixture
    def mock_bus(self, mocker):
        """Fixture providing a mock NexusBus with publish method."""
        mock_bus = mocker.MagicMock()
        mock_bus.publish = AsyncMock()
        return mock_bus

    @pytest.fixture
    def mock_config_service(self, mocker):
        """Fixture providing a mock ConfigService."""
        mock_config = mocker.MagicMock()
        mock_config.get_int = MagicMock(return_value=5)  # max_tool_iterations
        return mock_config

    @pytest.fixture
    def orchestrator_service(self, mock_bus, mock_config_service):
        """Fixture providing an OrchestratorService instance with mocked dependencies."""
        return OrchestratorService(mock_bus, mock_config_service)

    @pytest.fixture
    def sample_run(self):
        """Fixture providing a sample Run object for testing."""
        return Run(
            id="run_123",
            session_id="session_456",
            history=[
                Message(
                    run_id="run_123",
                    session_id="session_456",
                    role=Role.HUMAN,
                    content="Hello, how are you?"
                )
            ]
        )

    @pytest.mark.asyncio
    async def test_simple_dialogue_flow(self, orchestrator_service, mock_bus, sample_run):
        """Test the complete simple dialogue flow without tool calls."""
        # Arrange - RUNS_NEW event
        run_new_message = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.SYSTEM,
            content=sample_run
        )

        # Act 1: Handle new run
        await orchestrator_service.handle_new_run(run_new_message)

        # Assert 1: Should publish both UI event and context build request
        assert mock_bus.publish.call_count == 2
        
        # Check UI event (run_started)
        ui_event_call = mock_bus.publish.call_args_list[0]
        assert ui_event_call[0][0] == Topics.UI_EVENTS
        ui_event = ui_event_call[0][1]
        assert ui_event.content["event"] == "run_started"
        assert ui_event.content["payload"]["session_id"] == "session_456"
        
        # Check context build request
        context_request_call = mock_bus.publish.call_args_list[1]
        assert context_request_call[0][0] == Topics.CONTEXT_BUILD_REQUEST
        context_request = context_request_call[0][1]
        assert context_request.run_id == "run_123"
        assert context_request.session_id == "session_456"
        assert "current_input" in context_request.content

        # Reset mock for next assertion
        mock_bus.publish.reset_mock()

        # Arrange - CONTEXT_BUILD_RESPONSE event
        context_response = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.SYSTEM,
            content={
                "status": "success",
                "messages": [
                    {"role": "user", "content": "Hello, how are you?"}
                ],
                "tools": []
            }
        )

        # Act 2: Handle context ready
        await orchestrator_service.handle_context_ready(context_response)

        # Assert 2: Should publish LLM request
        mock_bus.publish.assert_called_once_with(Topics.LLM_REQUESTS, mock_bus.publish.call_args[0][1])
        llm_request = mock_bus.publish.call_args[0][1]
        assert llm_request.run_id == "run_123"
        assert "messages" in llm_request.content
        assert "tools" in llm_request.content

        # Reset mock for next assertion
        mock_bus.publish.reset_mock()

        # Arrange - LLM_RESULTS event (no tool calls)
        llm_result = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.AI,
            content={
                "content": "I'm doing well, thank you!",
                "tool_calls": None
            }
        )

        # Act 3: Handle LLM result
        await orchestrator_service.handle_llm_result(llm_result)

        # Assert 3: Should publish run_finished UI event
        # Should be called twice: once for text_chunk (if any) and once for run_finished
        assert mock_bus.publish.call_count >= 1
        
        # Find the run_finished event
        run_finished_call = None
        for call in mock_bus.publish.call_args_list:
            if call[0][0] == Topics.UI_EVENTS and call[0][1].content.get("event") == "run_finished":
                run_finished_call = call
                break
        
        assert run_finished_call is not None, "run_finished UI event not published"
        ui_event = run_finished_call[0][1]
        assert ui_event.content["payload"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_single_tool_call_flow(self, orchestrator_service, mock_bus, sample_run):
        """Test the flow with a single tool call."""
        # Setup: Get through initial context building
        run_new_message = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.SYSTEM,
            content=sample_run
        )
        await orchestrator_service.handle_new_run(run_new_message)
        
        context_response = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.SYSTEM,
            content={
                "status": "success",
                "messages": [
                    {"role": "user", "content": "Hello, how are you?"}
                ],
                "tools": [{"name": "calculator"}]
            }
        )
        await orchestrator_service.handle_context_ready(context_response)
        
        # Reset mock for tool call testing
        mock_bus.publish.reset_mock()

        # Arrange - LLM_RESULTS event with tool call
        llm_result = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.AI,
            content={
                "content": "I'll calculate that for you",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "calculator",
                            "arguments": "{\"expression\": \"2+2\"}"
                        }
                    }
                ]
            }
        )

        # Act: Handle LLM result with tool call
        await orchestrator_service.handle_llm_result(llm_result)

        # Assert: Should publish tool request
        mock_bus.publish.assert_called_with(Topics.TOOLS_REQUESTS, mock_bus.publish.call_args[0][1])
        tool_request = None
        for call in mock_bus.publish.call_args_list:
            if call[0][0] == Topics.TOOLS_REQUESTS:
                tool_request = call[0][1]
                break
        
        assert tool_request is not None, "Tool request not published"
        assert tool_request.content["name"] == "calculator"
        assert "args" in tool_request.content

        # Reset mock for tool result testing
        mock_bus.publish.reset_mock()

        # Arrange - TOOLS_RESULTS event
        tool_result = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.SYSTEM,
            content={
                "tool_name": "calculator",
                "result": "4",
                "status": "success",
                "call_id": "call_1"
            }
        )

        # Act: Handle tool result
        await orchestrator_service.handle_tool_result(tool_result)

        # Assert: Should publish follow-up LLM request
        mock_bus.publish.assert_called_with(Topics.LLM_REQUESTS, mock_bus.publish.call_args[0][1])
        followup_llm_request = None
        for call in mock_bus.publish.call_args_list:
            if call[0][0] == Topics.LLM_REQUESTS:
                followup_llm_request = call[0][1]
                break
        
        assert followup_llm_request is not None, "Follow-up LLM request not published"
        assert "messages" in followup_llm_request.content

    @pytest.mark.asyncio
    async def test_multi_tool_synchronization_flow(self, orchestrator_service, mock_bus, sample_run):
        """Test multi-tool synchronization logic."""
        # Setup: Get through initial context building
        run_new_message = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.SYSTEM,
            content=sample_run
        )
        await orchestrator_service.handle_new_run(run_new_message)
        
        context_response = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.SYSTEM,
            content={
                "status": "success",
                "messages": [
                    {"role": "user", "content": "Calculate 2+2 and 3+3"}
                ],
                "tools": [{"name": "calculator"}]
            }
        )
        await orchestrator_service.handle_context_ready(context_response)
        
        # Reset mock for multi-tool testing
        mock_bus.publish.reset_mock()

        # Arrange - LLM_RESULTS event with two tool calls
        llm_result = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.AI,
            content={
                "content": "I'll calculate both expressions",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "calculator",
                            "arguments": "{\"expression\": \"2+2\"}"
                        }
                    },
                    {
                        "id": "call_2",
                        "function": {
                            "name": "calculator",
                            "arguments": "{\"expression\": \"3+3\"}"
                        }
                    }
                ]
            }
        )

        # Act 1: Handle LLM result with multiple tool calls
        await orchestrator_service.handle_llm_result(llm_result)

        # Assert 1: Should set pending_tool_calls to 2
        run = orchestrator_service.active_runs["run_123"]
        assert run.metadata.get('pending_tool_calls') == 2
        
        # Should publish 2 tool requests
        tool_request_calls = [call for call in mock_bus.publish.call_args_list if call[0][0] == Topics.TOOLS_REQUESTS]
        assert len(tool_request_calls) == 2

        # Reset mock for first tool result
        mock_bus.publish.reset_mock()

        # Arrange - First TOOLS_RESULTS event
        first_tool_result = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.SYSTEM,
            content={
                "tool_name": "calculator",
                "result": "4",
                "status": "success",
                "call_id": "call_1"
            }
        )

        # Act 2: Handle first tool result
        await orchestrator_service.handle_tool_result(first_tool_result)

        # Assert 2: Should decrement pending_tool_calls to 1, but NOT call LLM yet
        run = orchestrator_service.active_runs["run_123"]
        assert run.metadata.get('pending_tool_calls') == 1
        
        # Should NOT publish LLM request yet
        llm_request_calls = [call for call in mock_bus.publish.call_args_list if call[0][0] == Topics.LLM_REQUESTS]
        assert len(llm_request_calls) == 0, "LLM request published prematurely"

        # Reset mock for second tool result
        mock_bus.publish.reset_mock()

        # Arrange - Second TOOLS_RESULTS event
        second_tool_result = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.SYSTEM,
            content={
                "tool_name": "calculator",
                "result": "6",
                "status": "success",
                "call_id": "call_2"
            }
        )

        # Act 3: Handle second tool result
        await orchestrator_service.handle_tool_result(second_tool_result)

        # Assert 3: Should decrement pending_tool_calls to 0 and call LLM
        run = orchestrator_service.active_runs["run_123"]
        assert run.metadata.get('pending_tool_calls') == 0
        
        # Should publish LLM request now
        mock_bus.publish.assert_called_with(Topics.LLM_REQUESTS, mock_bus.publish.call_args[0][1])
        llm_request = None
        for call in mock_bus.publish.call_args_list:
            if call[0][0] == Topics.LLM_REQUESTS:
                llm_request = call[0][1]
                break
        
        assert llm_request is not None, "LLM request not published after all tools completed"
        assert "messages" in llm_request.content

    @pytest.mark.asyncio
    async def test_max_tool_iterations_safety_valve(self, orchestrator_service, mock_bus, mock_config_service, sample_run):
        """Test that max tool iterations safety valve works correctly."""
        # Setup mock to return low max iterations
        mock_config_service.get_int.return_value = 1  # Only 1 iteration allowed
        
        # Recreate orchestrator with the new config
        orchestrator_service = OrchestratorService(mock_bus, mock_config_service)
        
        # Setup: Get through initial context building
        run_new_message = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.SYSTEM,
            content=sample_run
        )
        await orchestrator_service.handle_new_run(run_new_message)
        
        context_response = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.SYSTEM,
            content={
                "status": "success",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "tools": [{"name": "calculator"}]
            }
        )
        await orchestrator_service.handle_context_ready(context_response)
        
        # Reset mock for iteration testing
        mock_bus.publish.reset_mock()

        # Arrange - LLM_RESULTS event with tool call (first iteration)
        llm_result = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.AI,
            content={
                "content": "I'll calculate",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "calculator",
                            "arguments": "{\"expression\": \"2+2\"}"
                        }
                    }
                ]
            }
        )

        # Act 1: Handle LLM result (first iteration)
        await orchestrator_service.handle_llm_result(llm_result)

        # Should publish tool request (first iteration is allowed)
        tool_request_calls = [call for call in mock_bus.publish.call_args_list if call[0][0] == Topics.TOOLS_REQUESTS]
        assert len(tool_request_calls) == 1

        # Reset mock for second iteration attempt
        mock_bus.publish.reset_mock()

        # Arrange - Second LLM_RESULTS event with tool call (would be second iteration)
        second_llm_result = Message(
            run_id="run_123",
            session_id="session_456",
            role=Role.AI,
            content={
                "content": "I'll calculate again",
                "tool_calls": [
                    {
                        "id": "call_2",
                        "function": {
                            "name": "calculator",
                            "arguments": "{\"expression\": \"3+3\"}"
                        }
                    }
                ]
            }
        )

        # Act 2: Handle second LLM result (would exceed max iterations)
        await orchestrator_service.handle_llm_result(second_llm_result)

        # Assert: Should publish error and run_finished events due to max iterations exceeded
        ui_event_calls = [call for call in mock_bus.publish.call_args_list if call[0][0] == Topics.UI_EVENTS]
        assert len(ui_event_calls) >= 2  # error event + run_finished event
        
        # Should contain error message about max iterations
        error_event = None
        for call in ui_event_calls:
            if call[0][1].content.get("event") == "error":
                error_event = call[0][1]
                break
        
        assert error_event is not None, "Error event not published for max iterations"
        assert "Maximum tool iterations" in error_event.content["payload"]["message"]