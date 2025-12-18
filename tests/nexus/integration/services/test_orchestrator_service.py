"""
Integration tests for OrchestratorService.

These tests verify that OrchestratorService correctly handles event-driven interactions
via NexusBus, including proper state machine management, tool call orchestration,
and multi-tool synchronization. All external dependencies are mocked to ensure isolation
while testing the service's integration with the event bus system.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from nexus.core.models import Message, Role, Run, RunStatus
from nexus.core.topics import Topics
from nexus.services.orchestrator import OrchestratorService


class TestOrchestratorFlows:
    """Integration test suite for OrchestratorService event-driven behavior."""

    @pytest.fixture
    def mock_bus(self):
        """Create a mock NexusBus for testing."""
        mock_bus = Mock()
        mock_bus.publish = AsyncMock()
        mock_bus.subscribe = Mock()
        return mock_bus

    @pytest.fixture
    def mock_config_service(self):
        """Create a mock ConfigService for testing."""
        mock_service = Mock()
        mock_service.get_int.return_value = 5  # Default max_tool_iterations
        return mock_service

    @pytest.fixture
    def mock_identity_service(self):
        """Create a mock IdentityService for testing."""
        mock_service = AsyncMock()
        # By default, assume user is registered (returns identity dict with overrides)
        mock_service.get_identity.return_value = {
            "public_key": "test-public-key",
            "created_at": "2025-01-01T00:00:00Z",
            "config_overrides": {},
            "prompt_overrides": {},
        }
        return mock_service

    @pytest.fixture
    def orchestrator_service(
        self, mock_bus, mock_config_service, mock_identity_service
    ):
        """Create OrchestratorService instance with mocked dependencies."""
        return OrchestratorService(
            bus=mock_bus,
            config_service=mock_config_service,
            identity_service=mock_identity_service,
        )

    @pytest.fixture
    def sample_run(self):
        """Create a sample Run object for testing."""
        # Create initial human message
        human_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.HUMAN,
            content="What is artificial intelligence?",
        )

        # Create run with history
        run = Run(
            id="test-run-123",
            owner_key="test-session-456",
            status=RunStatus.PENDING,
            history=[human_message],
        )
        return run

    @pytest.mark.asyncio
    async def test_simple_dialogue_flow(
        self, orchestrator_service, mock_bus, sample_run
    ):
        """
        Test complete simple dialogue flow: new_run -> context_ready -> llm_result (no tools).
        Verifies correct event publishing sequence and state transitions.
        """
        # Step 1: Handle new run
        new_run_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.SYSTEM,
            content=sample_run,
        )

        await orchestrator_service.handle_new_run(new_run_message)

        # Assert: run_started UI event and context build request published
        assert mock_bus.publish.call_count == 2

        # Verify run_started UI event
        ui_call = mock_bus.publish.call_args_list[0]
        assert ui_call[0][0] == Topics.UI_EVENTS
        ui_message = ui_call[0][1]
        assert ui_message.content["event"] == "run_started"
        assert (
            ui_message.content["payload"]["user_input"]
            == "What is artificial intelligence?"
        )

        # Verify context build request - now expects Run object as content
        context_call = mock_bus.publish.call_args_list[1]
        assert context_call[0][0] == Topics.CONTEXT_BUILD_REQUEST
        context_message = context_call[0][1]
        # Content should be the Run object itself
        assert isinstance(context_message.content, Run)
        assert context_message.content.id == sample_run.id
        # Verify user_profile is in Run.metadata
        assert "user_profile" in context_message.content.metadata
        user_profile = context_message.content.metadata["user_profile"]
        assert user_profile["public_key"] == "test-public-key"
        assert "config_overrides" in user_profile
        assert "prompt_overrides" in user_profile

        # Verify run is stored and status updated
        assert sample_run.id in orchestrator_service.active_runs
        assert (
            orchestrator_service.active_runs[sample_run.id].status
            == RunStatus.BUILDING_CONTEXT
        )

        mock_bus.publish.reset_mock()

        # Step 2: Handle context ready
        context_ready_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.SYSTEM,
            content={
                "status": "success",
                "messages": [
                    {"role": "system", "content": "You are Xi, an AI assistant."},
                    {"role": "user", "content": "What is artificial intelligence?"},
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "description": "Search the web",
                        },
                    }
                ],
            },
        )

        await orchestrator_service.handle_context_ready(context_ready_message)

        # Assert: LLM request published
        mock_bus.publish.assert_called_once()
        llm_call = mock_bus.publish.call_args
        assert llm_call[0][0] == Topics.LLM_REQUESTS
        llm_message = llm_call[0][1]
        assert "messages" in llm_message.content
        assert "tools" in llm_message.content

        # Verify run status updated
        run = orchestrator_service.active_runs[sample_run.id]
        assert run.status == RunStatus.AWAITING_LLM_DECISION
        assert len(run.tools) == 1

        mock_bus.publish.reset_mock()

        # Step 3: Handle LLM result (no tool calls)
        llm_result_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.AI,
            content={
                "content": "Artificial intelligence is a field of computer science...",
                "tool_calls": None,
            },
        )

        await orchestrator_service.handle_llm_result(llm_result_message)

        # Assert: run_finished UI event published
        mock_bus.publish.assert_called_once()
        finish_call = mock_bus.publish.call_args
        assert finish_call[0][0] == Topics.UI_EVENTS
        finish_message = finish_call[0][1]
        assert finish_message.content["event"] == "run_finished"
        assert finish_message.content["payload"]["status"] == "completed"

        # Verify run is completed and removed
        assert sample_run.id not in orchestrator_service.active_runs

    @pytest.mark.asyncio
    async def test_user_profile_propagation(
        self, orchestrator_service, mock_bus, mock_identity_service
    ):
        """
        Test that user_profile is correctly injected into Run.metadata and propagated.
        Verifies that identity information with overrides is properly attached to the Run.
        """
        # Arrange: Setup identity with custom overrides
        mock_identity_service.get_identity.return_value = {
            "public_key": "user-with-overrides",
            "created_at": "2025-01-01T00:00:00Z",
            "config_overrides": {"model": "deepseek-chat", "temperature": 0.9},
            "prompt_overrides": {"persona": "I am Xi..."},
        }

        # Create run with the identity's public_key
        human_message = Message(
            run_id="test-run-456",
            owner_key="user-with-overrides",
            role=Role.HUMAN,
            content="Hello!",
        )

        run = Run(
            id="test-run-456",
            owner_key="user-with-overrides",
            status=RunStatus.PENDING,
            history=[human_message],
        )

        new_run_message = Message(
            run_id="test-run-456",
            owner_key="user-with-overrides",
            role=Role.SYSTEM,
            content=run,
        )

        # Act: Handle new run
        await orchestrator_service.handle_new_run(new_run_message)

        # Assert: Verify identity service was called
        mock_identity_service.get_identity.assert_called_once_with(
            "user-with-overrides"
        )

        # Verify user_profile was injected into Run.metadata
        stored_run = orchestrator_service.active_runs["test-run-456"]
        assert "user_profile" in stored_run.metadata

        user_profile = stored_run.metadata["user_profile"]
        assert user_profile["public_key"] == "user-with-overrides"
        assert user_profile["config_overrides"] == {
            "model": "deepseek-chat",
            "temperature": 0.9,
        }
        assert user_profile["prompt_overrides"] == {"persona": "I am Xi..."}
        assert "created_at" in user_profile

        # Verify context build request includes the Run object with user_profile
        context_call = mock_bus.publish.call_args_list[
            1
        ]  # Second call is CONTEXT_BUILD_REQUEST
        assert context_call[0][0] == Topics.CONTEXT_BUILD_REQUEST
        context_message = context_call[0][1]

        # Content should be the Run object
        assert isinstance(context_message.content, Run)
        assert context_message.content.id == "test-run-456"

        # Verify user_profile is accessible in the transmitted Run object
        transmitted_user_profile = context_message.content.metadata.get("user_profile")
        assert transmitted_user_profile is not None
        assert transmitted_user_profile["config_overrides"] == {
            "model": "deepseek-chat",
            "temperature": 0.9,
        }
        assert transmitted_user_profile["prompt_overrides"] == {"persona": "I am Xi..."}

    @pytest.mark.asyncio
    async def test_single_tool_call_flow(
        self, orchestrator_service, mock_bus, sample_run
    ):
        """
        Test single tool call flow: llm_result (with tool) -> tool_result -> llm_result (final).
        Verifies tool call orchestration and agentic loop completion.
        """
        # Setup: Add run to active runs
        orchestrator_service.active_runs[sample_run.id] = sample_run
        sample_run.status = RunStatus.AWAITING_LLM_DECISION
        sample_run.tools = [{"type": "function", "function": {"name": "web_search"}}]

        # Step 1: Handle LLM result with tool calls
        llm_result_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.AI,
            content={
                "content": "I'll search for information about AI.",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "arguments": '{"query": "artificial intelligence definition"}',
                        },
                    }
                ],
            },
        )

        await orchestrator_service.handle_llm_result(llm_result_message)

        # Assert: Tool request published
        mock_bus.publish.assert_called_once()
        tool_call = mock_bus.publish.call_args
        assert tool_call[0][0] == Topics.TOOLS_REQUESTS
        tool_message = tool_call[0][1]
        assert tool_message.content["name"] == "web_search"
        assert (
            tool_message.content["args"]["query"]
            == "artificial intelligence definition"
        )
        assert tool_message.content["call_id"] == "call_123"

        # Verify run state
        run = orchestrator_service.active_runs[sample_run.id]
        assert run.status == RunStatus.AWAITING_TOOL_RESULT
        assert run.iteration_count == 1
        assert run.metadata["pending_tool_calls"] == 1
        assert len(run.history) == 2  # Original human + AI with tool calls

        mock_bus.publish.reset_mock()

        # Step 2: Handle tool result
        tool_result_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.TOOL,
            content={
                "tool_name": "web_search",
                "result": "AI is the simulation of human intelligence...",
                "status": "success",
                "call_id": "call_123",
            },
        )

        await orchestrator_service.handle_tool_result(tool_result_message)

        # Assert: tool_call_finished UI event and follow-up LLM request published
        assert mock_bus.publish.call_count == 2

        # Verify tool_call_finished UI event
        ui_call = mock_bus.publish.call_args_list[0]
        assert ui_call[0][0] == Topics.UI_EVENTS
        ui_message = ui_call[0][1]
        assert ui_message.content["event"] == "tool_call_finished"
        assert ui_message.content["payload"]["tool_name"] == "web_search"
        assert ui_message.content["payload"]["status"] == "success"

        # Verify follow-up LLM request
        llm_call = mock_bus.publish.call_args_list[1]
        assert llm_call[0][0] == Topics.LLM_REQUESTS
        llm_message = llm_call[0][1]
        assert "messages" in llm_message.content
        assert (
            len(llm_message.content["messages"]) == 3
        )  # system, user, assistant, tool

        # Verify run state
        run = orchestrator_service.active_runs[sample_run.id]
        assert run.status == RunStatus.AWAITING_LLM_DECISION
        assert run.metadata["pending_tool_calls"] == 0
        assert (
            len(run.history) == 3
        )  # Original human + AI with tool calls + tool result

    @pytest.mark.asyncio
    async def test_multi_tool_sync_flow(
        self, orchestrator_service, mock_bus, sample_run
    ):
        """
        Test multi-tool synchronization: LLM calls 2 tools, waits for both results.
        Verifies that LLM is only called after all tools complete.
        """
        # Setup: Add run to active runs
        orchestrator_service.active_runs[sample_run.id] = sample_run
        sample_run.status = RunStatus.AWAITING_LLM_DECISION
        sample_run.tools = [{"type": "function", "function": {"name": "web_search"}}]

        # Step 1: Handle LLM result with multiple tool calls
        llm_result_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.AI,
            content={
                "content": "I'll search for information from multiple sources.",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "arguments": '{"query": "AI definition"}',
                        },
                    },
                    {
                        "id": "call_456",
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "arguments": '{"query": "AI applications"}',
                        },
                    },
                ],
            },
        )

        await orchestrator_service.handle_llm_result(llm_result_message)

        # Assert: Two tool requests published
        assert mock_bus.publish.call_count == 2

        # Verify run state
        run = orchestrator_service.active_runs[sample_run.id]
        assert run.metadata["pending_tool_calls"] == 2

        mock_bus.publish.reset_mock()

        # Step 2: Handle first tool result
        tool_result_1 = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.TOOL,
            content={
                "tool_name": "web_search",
                "result": "AI definition result...",
                "status": "success",
                "call_id": "call_123",
            },
        )

        await orchestrator_service.handle_tool_result(tool_result_1)

        # Assert: Only UI event published, no LLM request yet
        mock_bus.publish.assert_called_once()
        ui_call = mock_bus.publish.call_args
        assert ui_call[0][0] == Topics.UI_EVENTS

        # Verify pending count decremented but still waiting
        run = orchestrator_service.active_runs[sample_run.id]
        assert run.metadata["pending_tool_calls"] == 1

        mock_bus.publish.reset_mock()

        # Step 3: Handle second tool result
        tool_result_2 = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.TOOL,
            content={
                "tool_name": "web_search",
                "result": "AI applications result...",
                "status": "success",
                "call_id": "call_456",
            },
        )

        await orchestrator_service.handle_tool_result(tool_result_2)

        # Assert: UI event AND LLM request published (all tools completed)
        assert mock_bus.publish.call_count == 2

        # Verify LLM request is the second call
        llm_call = mock_bus.publish.call_args_list[1]
        assert llm_call[0][0] == Topics.LLM_REQUESTS

        # Verify run state
        run = orchestrator_service.active_runs[sample_run.id]
        assert run.metadata["pending_tool_calls"] == 0
        assert run.status == RunStatus.AWAITING_LLM_DECISION

    @pytest.mark.asyncio
    async def test_max_iterations_safety_valve(
        self, orchestrator_service, mock_bus, sample_run
    ):
        """
        Test safety valve: when max_tool_iterations is exceeded, run times out.
        Verifies that the system prevents infinite tool calling loops.
        """
        # Setup: Add run to active runs and set iteration count near limit
        orchestrator_service.active_runs[sample_run.id] = sample_run
        sample_run.status = RunStatus.AWAITING_LLM_DECISION
        sample_run.iteration_count = 5  # At max limit (config returns 5)
        sample_run.tools = [{"type": "function", "function": {"name": "web_search"}}]

        # Handle LLM result with tool calls (should trigger safety valve)
        llm_result_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.AI,
            content={
                "content": "I need to search more...",
                "tool_calls": [
                    {
                        "id": "call_999",
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "arguments": '{"query": "more info"}',
                        },
                    }
                ],
            },
        )

        await orchestrator_service.handle_llm_result(llm_result_message)

        # Assert: Error event and run_finished event published, no tool requests
        assert mock_bus.publish.call_count == 2

        # Verify error event
        error_call = mock_bus.publish.call_args_list[0]
        assert error_call[0][0] == Topics.UI_EVENTS
        error_message = error_call[0][1]
        assert error_message.content["event"] == "error"
        assert "Maximum tool iterations" in error_message.content["payload"]["message"]

        # Verify run_finished event with timed_out status
        finish_call = mock_bus.publish.call_args_list[1]
        assert finish_call[0][0] == Topics.UI_EVENTS
        finish_message = finish_call[0][1]
        assert finish_message.content["event"] == "run_finished"
        assert finish_message.content["payload"]["status"] == "timed_out"

        # Verify run is removed and status updated
        assert sample_run.id not in orchestrator_service.active_runs
        assert sample_run.status == RunStatus.TIMED_OUT

    @pytest.mark.asyncio
    async def test_handle_streaming_events_forwarding(
        self, orchestrator_service, mock_bus, sample_run
    ):
        """
        Test that streaming events (text_chunk, tool_call_started) are forwarded to UI.
        """
        # Setup: Add run to active runs
        orchestrator_service.active_runs[sample_run.id] = sample_run

        # Test text_chunk forwarding
        text_chunk_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.SYSTEM,
            content={
                "event": "text_chunk",
                "run_id": "test-run-123",
                "payload": {"chunk": "Hello"},
            },
        )

        await orchestrator_service.handle_llm_result(text_chunk_message)

        # Assert: Message forwarded to UI_EVENTS
        mock_bus.publish.assert_called_once()
        ui_call = mock_bus.publish.call_args
        assert ui_call[0][0] == Topics.UI_EVENTS
        ui_message = ui_call[0][1]
        assert ui_message.content["event"] == "text_chunk"
        assert ui_message.content["payload"]["chunk"] == "Hello"

        mock_bus.publish.reset_mock()

        # Test tool_call_started forwarding
        tool_started_message = Message(
            run_id="test-run-123",
            owner_key="test-session-456",
            role=Role.SYSTEM,
            content={
                "event": "tool_call_started",
                "run_id": "test-run-123",
                "payload": {"tool_name": "web_search"},
            },
        )

        await orchestrator_service.handle_llm_result(tool_started_message)

        # Assert: Message forwarded to UI_EVENTS
        mock_bus.publish.assert_called_once()
        ui_call = mock_bus.publish.call_args
        assert ui_call[0][0] == Topics.UI_EVENTS
        ui_message = ui_call[0][1]
        assert ui_message.content["event"] == "tool_call_started"
        assert ui_message.content["payload"]["tool_name"] == "web_search"

    def test_subscribe_to_bus(self, orchestrator_service, mock_bus):
        """
        Test that OrchestratorService correctly subscribes to all required topics.
        """
        # Act: Subscribe to bus
        orchestrator_service.subscribe_to_bus()

        # Assert: Verify subscriptions to all required topics
        expected_subscriptions = [
            (Topics.RUNS_NEW, orchestrator_service.handle_new_run),
            (Topics.CONTEXT_BUILD_RESPONSE, orchestrator_service.handle_context_ready),
            (Topics.LLM_RESULTS, orchestrator_service.handle_llm_result),
            (Topics.TOOLS_RESULTS, orchestrator_service.handle_tool_result),
        ]

        assert mock_bus.subscribe.call_count == len(expected_subscriptions)

        for i, (expected_topic, expected_handler) in enumerate(expected_subscriptions):
            call_args = mock_bus.subscribe.call_args_list[i]
            assert call_args[0][0] == expected_topic
            assert call_args[0][1] == expected_handler
