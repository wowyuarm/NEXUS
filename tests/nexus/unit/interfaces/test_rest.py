"""
Unit tests for REST interface.

Tests the REST API endpoints for NEXUS, verifying proper separation
from WebSocket interface and correct handling of command queries.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock
from nexus.interfaces import rest


class TestRestInterface:
    """Test suite for REST API endpoints."""
    
    def test_commands_endpoint_exists(self):
        """
        GREEN Test: Verify that /commands endpoint exists and returns 200.
        
        This test verifies the REST interface skeleton is properly set up
        with dependency injection and returns a valid response.
        """
        # Create a mock CommandService
        mock_command_service = Mock()
        mock_command_service._command_definitions = {}
        
        # Create a FastAPI app and include the REST router
        app = FastAPI()
        app.include_router(rest.router, prefix="/api/v1")
        
        # Override the dependency injection
        app.dependency_overrides[rest.get_command_service] = lambda: mock_command_service
        
        # Create test client
        client = TestClient(app)
        
        # Make request to commands endpoint
        response = client.get("/api/v1/commands")
        
        # Assert successful response
        assert response.status_code == 200
        assert isinstance(response.json(), list)

