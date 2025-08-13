"""
WebSocket interface for NEXUS.

Provides real-time communication between the frontend and the NEXUS backend
via WebSocket connections. Handles incoming user messages and outgoing responses.
"""

import logging
import json
import uuid
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Role, Run, RunStatus
from nexus.core.topics import Topics

logger = logging.getLogger(__name__)


class WebsocketInterface:
    def __init__(self, bus: NexusBus):
        self.bus = bus
        # Store active WebSocket connections by session_id
        self.connections: Dict[str, WebSocket] = {}
        logger.info("WebsocketInterface initialized")

    def subscribe_to_bus(self) -> None:
        """Subscribe to UI events for sending messages to frontend."""
        self.bus.subscribe(Topics.UI_EVENTS, self.handle_ui_event)
        logger.info("WebsocketInterface subscribed to NexusBus")

    async def handle_ui_event(self, message: Message) -> None:
        """
        Handle UI events and send them to the appropriate WebSocket connection.

        Args:
            message: Message containing UI event data
        """
        try:
            run_id = message.run_id
            session_id = message.session_id
            content = message.content

            logger.info(f"Handling UI event for session_id={session_id}, run_id={run_id}")

            # Find the WebSocket connection for this session
            websocket = self.connections.get(session_id)
            if not websocket:
                logger.warning(f"No WebSocket connection found for session_id={session_id}")
                return

            # Extract payload from standardized UI event format
            # Expected format: {"event": "...", "run_id": "...", "payload": {...}}
            payload = content.get("payload", {})

            # Send the event to the frontend
            await websocket.send_text(json.dumps({
                "type": "response",
                "run_id": run_id,
                "content": payload.get("chunk", ""),
                "timestamp": message.timestamp.isoformat()
            }))

            logger.info(f"Sent UI event to session_id={session_id}")

        except Exception as e:
            logger.error(f"Error handling UI event: {e}")

    async def run_forever(self, host: str, port: int) -> FastAPI:
        """
        Create and configure the FastAPI application with WebSocket endpoint.

        Args:
            host: Host to bind to (for logging purposes)
            port: Port to bind to (for logging purposes)

        Returns:
            FastAPI application instance
        """
        app = FastAPI(title="NEXUS WebSocket API")

        @app.get("/")
        async def health_check():
            return {"status": "ok", "service": "NEXUS WebSocket API"}

        @app.get("/health")
        async def health():
            return {"status": "healthy", "connections": len(self.connections)}

        @app.websocket("/ws/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, session_id: str):
            await websocket.accept()
            logger.info(f"WebSocket connection established for session_id={session_id}")

            # Store the connection
            self.connections[session_id] = websocket

            try:
                while True:
                    # Receive message from client
                    data = await websocket.receive_text()
                    logger.info(f"Received message from session_id={session_id}: {data[:100]}...")

                    try:
                        # Parse the incoming message
                        message_data = json.loads(data)
                        user_input = message_data.get("content", "")

                        if not user_input.strip():
                            logger.warning(f"Empty message received from session_id={session_id}")
                            continue

                        # Create a new run for this user input
                        run_id = f"run_{uuid.uuid4().hex}"

                        # Create the initial user message
                        user_message = Message(
                            run_id=run_id,
                            session_id=session_id,
                            role=Role.HUMAN,
                            content=user_input
                        )

                        # Create Run object and add the initial message to its history
                        run = Run(
                            id=run_id,
                            session_id=session_id,
                            status=RunStatus.PENDING
                        )
                        run.history.append(user_message)

                        # Create envelope message containing the Run object
                        envelope_message = Message(
                            run_id=run_id,
                            session_id=session_id,
                            role=Role.SYSTEM,
                            content=run
                        )

                        # Publish the envelope message to start the conversation flow
                        await self.bus.publish(Topics.RUNS_NEW, envelope_message)
                        logger.info(f"Published new run for session_id={session_id}, run_id={run_id}")

                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON received from session_id={session_id}: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Invalid JSON format"
                        }))
                    except Exception as e:
                        logger.error(f"Error processing message from session_id={session_id}: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Error processing message"
                        }))

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session_id={session_id}")
            except Exception as e:
                logger.error(f"WebSocket error for session_id={session_id}: {e}")
            finally:
                # Clean up the connection
                if session_id in self.connections:
                    del self.connections[session_id]
                    logger.info(f"Cleaned up connection for session_id={session_id}")

        logger.info(f"WebSocket interface configured for {host}:{port}")
        return app
