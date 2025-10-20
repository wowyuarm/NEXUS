"""
History command definition for NEXUS.

Provides access to conversation history through REST API.
This command enables users to view their message history for context review
and conversation continuity.
"""

import logging

logger = logging.getLogger(__name__)

# Command definition for auto-discovery
COMMAND_DEFINITION = {
    "name": "history",
    "description": "View conversation history",
    "usage": "/history [limit]",
    "handler": "rest",
    "requiresGUI": True,
    "examples": ["/history", "/history 50"],
    "restOptions": {
        "getEndpoint": "/api/v1/messages",
        "method": "GET"
    }
}

# Note: REST commands do not require an execute() function
# The execution logic is implemented in the REST API endpoints
# located in nexus/interfaces/rest.py

