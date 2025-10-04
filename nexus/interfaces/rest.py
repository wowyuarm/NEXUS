"""
REST interface for NEXUS.

Provides HTTP REST API endpoints for querying system information,
command definitions, and other stateless operations. This interface
is separate from the WebSocket interface which handles real-time
communication and stateful sessions.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

# Create the API router for REST endpoints
router = APIRouter()

# Dependency injection placeholder
# This will be overridden in main.py using app.dependency_overrides
_command_service_instance: Optional[Any] = None


def get_command_service():
    """
    Dependency injection function for CommandService.
    
    This function is a placeholder that will be overridden in main.py
    using FastAPI's dependency_overrides mechanism.
    
    Returns:
        CommandService instance
    
    Raises:
        HTTPException: If CommandService is not properly injected
    """
    if _command_service_instance is None:
        logger.error("CommandService not injected into REST interface")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable: CommandService not initialized"
        )
    return _command_service_instance


@router.get("/commands")
async def get_all_commands(
    cmd_svc=Depends(get_command_service)
) -> List[Dict[str, Any]]:
    """
    Get all available commands and their metadata.
    
    This endpoint returns a list of all registered commands with their
    definitions, including name, description, usage, examples, etc.
    
    Args:
        cmd_svc: CommandService instance (injected)
    
    Returns:
        List of command definitions
    
    Example response:
        [
            {
                "name": "help",
                "description": "Show available commands",
                "usage": "/help",
                "execution_target": "server",
                "examples": ["/help"]
            }
        ]
    """
    try:
        # Get command definitions from CommandService
        # For now, return an empty list as a skeleton implementation
        # This will be enhanced when we add the method to CommandService
        commands = []
        
        if hasattr(cmd_svc, '_command_definitions'):
            # Extract command metadata from the service's internal registry
            for cmd_name, cmd_def in cmd_svc._command_definitions.items():
                commands.append(cmd_def)
        
        logger.info(f"Retrieved {len(commands)} commands via REST API")
        return commands
        
    except Exception as e:
        logger.error(f"Error retrieving commands: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving commands: {str(e)}"
        )


