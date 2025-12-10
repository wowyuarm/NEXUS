"""
NEXUS interfaces package.

This package contains interface implementations for different
communication protocols:
- rest: HTTP REST API for stateless queries
- websocket: WebSocket interface for real-time communication
"""

from nexus.interfaces import rest, websocket

__all__ = ["rest", "websocket"]
