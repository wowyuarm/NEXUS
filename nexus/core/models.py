"""
Core data models for the NEXUS event-driven system.

This module defines:
- Role: enum of message actors in the system
- RunStatus: enum of lifecycle states for a Run
- Message: the atomic unit of information passed on the bus
- Run: container tracking the lifecycle and history of a single interaction

All models are Pydantic-based with strict typing and sensible defaults.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List  # noqa: F401 (Optional intentionally imported per spec)
from enum import Enum
import uuid
from datetime import datetime, timezone


class Role(str, Enum):
    """Actor producing a Message inside the system."""

    HUMAN = "HUMAN"
    AI = "AI"
    SYSTEM = "SYSTEM"
    TOOL = "TOOL"
    COMMAND = "COMMAND"


class RunStatus(str, Enum):
    """Lifecycle states of a Run."""

    PENDING = "PENDING"
    BUILDING_CONTEXT = "BUILDING_CONTEXT"
    AWAITING_LLM_DECISION = "AWAITING_LLM_DECISION"
    AWAITING_TOOL_RESULT = "AWAITING_TOOL_RESULT"
    GENERATING_RESPONSE = "GENERATING_RESPONSE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


def _now_utc() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _gen_msg_id() -> str:
    """Generate a unique message identifier with 'msg_' prefix."""
    return f"msg_{uuid.uuid4().hex}"


def _gen_run_id() -> str:
    """Generate a unique run identifier with 'run_' prefix."""
    return f"run_{uuid.uuid4().hex}"


class Message(BaseModel):
    """Atomic message entity passed through the NexusBus.

    Fields
    ------
    id: unique message ID with 'msg_' prefix
    run_id: ID of the Run this message belongs to
    session_id: ID of the conversational session continuum
    role: actor that produced the message
    content: payload content (string, dict, etc.)
    timestamp: UTC timestamp when the message was created
    metadata: arbitrary structured metadata
    """

    id: str = Field(default_factory=_gen_msg_id)
    run_id: str
    session_id: str
    role: Role
    content: Any
    timestamp: datetime = Field(default_factory=_now_utc)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Run(BaseModel):
    """Container tracking the lifecycle of a single interaction (Run)."""

    id: str = Field(default_factory=_gen_run_id)
    session_id: str
    status: RunStatus = Field(default=RunStatus.PENDING)
    history: List[Message] = Field(default_factory=list)
    iteration_count: int = Field(default=0)
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
