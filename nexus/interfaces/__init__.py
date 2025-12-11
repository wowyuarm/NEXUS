"""
NEXUS interfaces package.

This package contains interface implementations for different
communication protocols:
- rest: HTTP REST API for stateless queries and SSE streaming
- sse: SSE interface for real-time event routing
"""

from nexus.interfaces import rest, sse

__all__ = ["rest", "sse"]
