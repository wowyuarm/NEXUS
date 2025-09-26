"""
Defines the standardized event topics for the NexusBus.

This module centralizes all topic strings to prevent typos and provide a single
source of truth for inter-service communication channels.
"""

from typing import List, Dict


class Topics:
    """
    A namespace for all event topics used in the NexusBus.
    This class should not be instantiated.
    """

    # --- Run Lifecycle Topics ---
    RUNS_NEW = "runs.new"
    """
    Published by an interface when a new user request initiates a run.
    Message content: a Run object.
    """

    # --- Context Building Topics ---
    CONTEXT_BUILD_REQUEST = "context.build.request"
    """
    Published by the Orchestrator to request context for a run.
    Message content: {"session_id": str, "current_input": str}
    """

    CONTEXT_BUILD_RESPONSE = "context.build.response"
    """
    Published by the ContextService when context has been built.
    Message content: {"status": "success"|"error", "messages": List[Dict]}
    """

    # --- LLM Interaction Topics ---
    LLM_REQUESTS = "llm.requests"
    """
    Published by the Orchestrator to request an LLM completion.
    Message content: {"messages": List[Dict]}
    """

    LLM_RESULTS = "llm.results"
    """
    Published by the LLMService with the result from the LLM.
    Message content: {"content": str|None, "tool_calls": List|None}
    """

    # --- Tool Execution Topics ---
    TOOLS_REQUESTS = "tools.requests"
    """
    Published by the Orchestrator to request a tool execution.
    Message content: {"name": str, "args": Dict}
    """

    TOOLS_RESULTS = "tools.results"
    """
    Published by the ToolExecutorService with the result of a tool execution.
    Message content: {"result": Any, "status": "success"|"error", "tool_name": str}
    """

    # --- UI & Frontend Topics ---
    UI_EVENTS = "ui.events"
    """
    Published by various services (mainly Orchestrator) to send real-time
    updates to the frontend.
    Message content: {"event": str, "run_id": str, "payload": Dict}
    """

    # --- Command System Topics ---
    SYSTEM_COMMAND = "system.command"
    """
    Published by interfaces when a user issues a command.
    Message content: Command string (e.g., "/ping", "/help")
    """

    COMMAND_RESULT = "command.result"
    """
    Published by CommandService with the result of command execution.
    Message content: {"status": "success"|"error", "message": str}
    """

