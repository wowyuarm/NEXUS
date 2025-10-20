"""
Prompt command definition for NEXUS.

Provides access to user prompt customization through REST API.
This command enables users to view and modify their AI persona and system prompts,
allowing for personalized AI interaction styles.
"""

import logging

logger = logging.getLogger(__name__)

# Command definition for auto-discovery
COMMAND_DEFINITION = {
    "name": "prompt",
    "description": "View or modify AI persona and system prompts",
    "usage": "/prompt",
    "handler": "rest",
    "requiresGUI": True,
    "examples": ["/prompt"],
    "restOptions": {
        "getEndpoint": "/api/v1/prompts",
        "postEndpoint": "/api/v1/prompts",
        "method": "GET"
    }
}

# Note: REST commands do not require an execute() function
# The execution logic is implemented in the REST API endpoints
# located in nexus/interfaces/rest.py

