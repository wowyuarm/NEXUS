"""
Database service skeleton for NEXUS.

This service will be responsible for persistence concerns (e.g., saving runs,
messages, and other state) in future iterations. For now, it wires into the
NexusBus and exposes a run_forever hook for any background work if needed.
"""

import logging
from nexus.core.bus import NexusBus

logger = logging.getLogger(__name__)


class DatabaseService:
    """Database service placeholder.

    Responsibilities:
    - Subscribe to bus topics requiring persistence (future work)
    - Perform async background tasks if needed via run_forever
    """

    def __init__(self, bus: NexusBus):
        self.bus = bus
        logger.info("DatabaseService Initialized")

    def subscribe_to_bus(self) -> None:
        """Declare bus subscriptions (no-op for now)."""
        # Future: self.bus.subscribe("topics.persistence.write", self.handle_write)
        logger.info("DatabaseService subscribed to NexusBus")

    async def run_forever(self) -> None:
        """Run background tasks if any (idle for now)."""
        # No background loop yet. Intentionally left as a placeholder.
        return
