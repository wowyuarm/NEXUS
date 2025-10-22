"""Theme command definition for NEXUS."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

COMMAND_DEFINITION = {
    "name": "theme",
    "description": "Toggle between light and dark themes (client-side only).",
    "usage": "/theme [light|dark|system]",
    "handler": "client",
    "examples": [
        "/theme",
        "/theme light",
        "/theme dark",
        "/theme system",
    ],
}


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Prevent accidental server execution of the client-only command."""
    logger.warning("Theme command executed on server; this should be client-only")
    raise RuntimeError(
        "Theme command should be executed on the client side. "
        "Check command handler routing if this message appears."
    )
