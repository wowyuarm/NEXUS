"""
Config command definition for NEXUS.

Provides access to user configuration management through REST API.
This command enables users to view and modify their personalized configuration
(model selection, temperature, max_tokens, etc.) through a GUI interface.
"""

import logging

logger = logging.getLogger(__name__)

# Command definition for auto-discovery
COMMAND_DEFINITION = {
    "name": "config",
    "description": "View or modify some configuration (model, temperature, etc.)",
    "usage": "/config",
    "handler": "rest",
    "requiresGUI": True,
    "examples": ["/config"],
    "restOptions": {
        "getEndpoint": "/api/v1/config",
        "postEndpoint": "/api/v1/config",
        "method": "GET",
    },
}

# Note: REST commands do not require an execute() function
# The execution logic is implemented in the REST API endpoints
# located in nexus/interfaces/rest.py
