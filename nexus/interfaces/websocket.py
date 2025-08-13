import logging
from nexus.core.bus import NexusBus

logger = logging.getLogger(__name__)


class WebsocketInterface:
    def __init__(self, bus: NexusBus):
        self.bus = bus
        logger.info("WebsocketInterface Initialized")

    def subscribe_to_bus(self) -> None:
        # Subscribe to UI events/messages for the frontend here in the future
        logger.info("WebsocketInterface subscribed to NexusBus")

    async def run_forever(self, host: str, port: int):
        # Start the WebSocket server here in the future
        # Log to avoid unused-argument warnings for now
        logger.info("WebsocketInterface.run_forever requested at %s:%d", host, port)
        pass
