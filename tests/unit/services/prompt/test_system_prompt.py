"""Unit tests for system prompt construction in ContextService."""

import os
import pytest
from unittest.mock import MagicMock

import nexus.services.context as ctxmod
from nexus.services.context import (
    ContextService,
    CONTENT_SEPARATOR,
    FALLBACK_SYSTEM_PROMPT,
    PROMPTS_SUBDIR,
    PERSONA_FILENAME,
    TOOLS_FILENAME,
    SYSTEM_FILENAME,
)


@pytest.fixture
def context_service(mocker):
    """Provide a ContextService with minimal mocked dependencies."""
    mock_bus = mocker.MagicMock()
    mock_tool_registry = mocker.MagicMock()
    service = ContextService(
        bus=mock_bus,
        tool_registry=mock_tool_registry,
        config_service=None,
        persistence_service=None,
    )
    return service


def test_load_system_prompt_concat_order_persona_system_tools(context_service, mocker):
    """It should concatenate persona, system, then tools with separators in order."""
    fake_persona = "PERSONA"
    fake_system = "SYSTEM"
    fake_tools = "TOOLS"

    def fake_loader(prompts_dir, filename, fallback):
        if filename == "persona.md":
            return fake_persona
        if filename == "system.md":
            return fake_system
        if filename == "tools.md":
            return fake_tools
        return fallback

    mocker.patch(
        "nexus.services.context.ContextService._load_prompt_file",
        side_effect=fake_loader,
    )

    result = context_service._load_system_prompt()
    expected = CONTENT_SEPARATOR.join([fake_persona, fake_system, fake_tools])
    assert result == expected


def test_load_system_prompt_missing_some_files(context_service, mocker):
    """It should skip missing files but preserve defined order of remaining parts."""
    fake_persona = "PERSONA"
    fake_system = ""  # simulate missing system.md
    fake_tools = "TOOLS"

    def fake_loader(prompts_dir, filename, fallback):
        if filename == "persona.md":
            return fake_persona
        if filename == "system.md":
            return fake_system
        if filename == "tools.md":
            return fake_tools
        return fallback

    mocker.patch(
        "nexus.services.context.ContextService._load_prompt_file",
        side_effect=fake_loader,
    )

    result = context_service._load_system_prompt()
    expected = CONTENT_SEPARATOR.join([fake_persona, fake_tools])
    assert result == expected


def test_load_system_prompt_all_missing_uses_fallback(context_service, mocker):
    """If all prompt parts are missing, it should return the fallback prompt."""

    def fake_loader(prompts_dir, filename, fallback):
        return ""  # simulate all missing/empty

    mocker.patch(
        "nexus.services.context.ContextService._load_prompt_file",
        side_effect=fake_loader,
    )

    result = context_service._load_system_prompt()
    assert result == FALLBACK_SYSTEM_PROMPT


def test_load_system_prompt_reads_actual_files_concat_order(context_service):
    """It should read real files and concatenate persona -> system -> tools in order."""
    # Compute prompts directory same way as service
    current_dir = os.path.dirname(os.path.abspath(ctxmod.__file__))
    nexus_dir = os.path.dirname(current_dir)
    prompts_dir = os.path.join(nexus_dir, PROMPTS_SUBDIR)

    # Read actual files
    with open(os.path.join(prompts_dir, PERSONA_FILENAME), "r", encoding="utf-8") as f:
        persona_content = f.read()
    with open(os.path.join(prompts_dir, SYSTEM_FILENAME), "r", encoding="utf-8") as f:
        system_content = f.read()
    with open(os.path.join(prompts_dir, TOOLS_FILENAME), "r", encoding="utf-8") as f:
        tools_content = f.read()

    # Sanity: ensure files are non-empty for a meaningful assertion
    assert persona_content.strip() != ""
    assert system_content.strip() != ""
    assert tools_content.strip() != ""

    expected = CONTENT_SEPARATOR.join([persona_content, system_content, tools_content])
    result = context_service._load_system_prompt()
    assert result == expected


