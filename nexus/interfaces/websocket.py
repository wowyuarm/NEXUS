"""
WebSocket interface for NEXUS.

Provides real-time communication between the frontend and the NEXUS backend
via WebSocket connections. Handles incoming user messages and outgoing responses.
"""

import logging
import json
import uuid
from typing import Dict, Union
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from nexus.core.bus import NexusBus
from nexus.core.models import Message, Role, Run, RunStatus
from nexus.core.topics import Topics
from nexus.services.database.service import DatabaseService

logger = logging.getLogger(__name__)

# Constants for standardized response formats
RESPONSE_TYPE_ERROR = "error"
ERROR_MSG_INVALID_JSON = "Invalid JSON format"
ERROR_MSG_PROCESSING = "Error processing message"

# Constants for message types
MESSAGE_TYPE_PING = "ping"
MESSAGE_TYPE_USER_MESSAGE = "user_message"
MESSAGE_TYPE_SYSTEM_COMMAND = "system_command"


def _parse_client_message(data: str) -> Dict[str, Union[str, Dict]]:
    """
    Parse incoming client message data and extract relevant information.

    Args:
        data: Raw JSON string data from WebSocket client

    Returns:
        Dictionary containing parsed message data with standardized structure

    Raises:
        json.JSONDecodeError: If data is not valid JSON
    """
    message_data = json.loads(data)
    message_type = message_data.get("type", "")
    payload = message_data.get("payload", {})

    if message_type == MESSAGE_TYPE_PING:
        return {"type": message_type, "payload": payload}
    elif message_type == MESSAGE_TYPE_USER_MESSAGE:
        user_input = payload.get("content", "")
        client_timestamp_utc = payload.get("client_timestamp_utc", "")
        client_timezone_offset = payload.get("client_timezone_offset", 0)
        return {
            "type": message_type,
            "payload": {
                "content": user_input,
                "client_timestamp_utc": client_timestamp_utc,
                "client_timezone_offset": client_timezone_offset
            },
            "user_input": user_input,
            "client_timestamp_utc": client_timestamp_utc,
            "client_timezone_offset": client_timezone_offset
        }
    elif message_type == MESSAGE_TYPE_SYSTEM_COMMAND:
        command = payload.get("command", "")
        session_id = payload.get("session_id", "")
        return {
            "type": message_type,
            "payload": payload,
            "command": command,
            "session_id": session_id
        }
    elif message_type == "":
        return {"type": "", "payload": payload}
    else:
        return {"type": "unknown", "original_type": message_type}


class WebsocketInterface:
    def __init__(self, bus: NexusBus, database_service: DatabaseService):
        self.bus = bus
        self.database_service = database_service
        # Store active WebSocket connections by session_id
        self.connections: Dict[str, WebSocket] = {}
        logger.info("WebsocketInterface initialized")

    def _generate_run_id(self) -> str:
        """Generate a unique run identifier."""
        return f"run_{uuid.uuid4().hex}"

    def _create_error_response(self, error_message: str) -> str:
        """Create standardized error response JSON."""
        return json.dumps({
            "type": RESPONSE_TYPE_ERROR,
            "message": error_message
        })



    def subscribe_to_bus(self) -> None:
        """Subscribe to UI events for sending messages to frontend."""
        self.bus.subscribe(Topics.UI_EVENTS, self.handle_ui_event)
        self.bus.subscribe(Topics.COMMAND_RESULT, self.handle_command_result)
        logger.info("WebsocketInterface subscribed to NexusBus")

    async def handle_ui_event(self, message: Message) -> None:
        """
        Handle UI events and send them to the appropriate WebSocket connection.

        Directly forwards the standardized UI event from Orchestrator to frontend
        without any modification or re-packaging.

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

            # Forward the standardized UI event directly to frontend
            # message.content is the complete {"event": "...", "run_id": "...", "payload": {...}} dict
            standardized_event_json = json.dumps(content)
            await websocket.send_text(standardized_event_json)

            logger.info(f"Forwarded UI event to session_id={session_id}")

        except Exception as e:
            logger.error(f"Error handling UI event: {e}")

    async def handle_command_result(self, message: Message) -> None:
        """
        Handle command result messages and send them to the appropriate WebSocket connection.

        Args:
            message: Message containing command result data
        """
        try:
            run_id = message.run_id
            session_id = message.session_id
            content = message.content

            logger.info(f"Handling command result for session_id={session_id}, run_id={run_id}")

            # Find the WebSocket connection for this session
            websocket = self.connections.get(session_id)
            if not websocket:
                logger.warning(f"No WebSocket connection found for session_id={session_id}")
                return

            # Create standardized UI event for command result
            ui_event = {
                "event": "command_result",
                "run_id": run_id,
                "payload": content
            }

            # Send the UI event to frontend
            standardized_event_json = json.dumps(ui_event)
            await websocket.send_text(standardized_event_json)

            logger.info(f"Forwarded command result to session_id={session_id}")

        except Exception as e:
            logger.error(f"Error handling command result: {e}")

    def add_websocket_routes(self, app: FastAPI) -> None:
        """
        Add WebSocket routes to an existing FastAPI application.

        This method registers the WebSocket endpoint handler with the provided
        FastAPI app instance. It should be called during application initialization
        in main.py after the app is created.

        Args:
            app: FastAPI application instance to add routes to
        """
        @app.websocket("/api/v1/ws/{session_id}")
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
                        # Parse the incoming message using the helper function
                        parsed_message = _parse_client_message(data)
                        message_type = parsed_message.get("type", "")

                        # Handle different message types
                        if message_type == MESSAGE_TYPE_PING:
                            logger.debug(f"Received ping from client session_id={session_id}")
                            continue
                        elif message_type == MESSAGE_TYPE_USER_MESSAGE:
                            user_input = parsed_message.get("user_input", "")
                            client_timestamp_utc = parsed_message.get("client_timestamp_utc", "")
                            client_timezone_offset = parsed_message.get("client_timezone_offset", 0)

                            if not user_input.strip():
                                logger.warning(f"Empty user message received from session_id={session_id}")
                                continue
                        elif message_type == MESSAGE_TYPE_SYSTEM_COMMAND:
                            command = parsed_message.get("command", "")
                            logger.info(f"Received system command from session_id={session_id}: {command}")

                            if not command.strip():
                                logger.warning(f"Empty command received from session_id={session_id}")
                                continue

                            # Check if command has authentication data
                            payload = parsed_message.get("payload", {})
                            auth_data = payload.get("auth") if isinstance(payload, dict) else None

                            # Create command message content
                            # If auth is present, use structured format; otherwise use simple string
                            if auth_data:
                                command_content = {
                                    "command": command,
                                    "auth": auth_data
                                }
                                logger.info(f"Command has signature authentication")
                            else:
                                command_content = command

                            # Create command message
                            command_message = Message(
                                run_id=self._generate_run_id(),
                                session_id=session_id,
                                role=Role.COMMAND,
                                content=command_content
                            )

                            # Publish to system command topic
                            await self.bus.publish(Topics.SYSTEM_COMMAND, command_message)
                            logger.info(f"Published system command for session_id={session_id}: {command}")
                            continue
                        else:
                            logger.warning(f"Received unknown message type '{message_type}' from session_id={session_id}")
                            continue

                        # Create a new run for this user input
                        run_id = self._generate_run_id()

                        # Create the initial user message with client timestamp in metadata
                        user_message_metadata = {}
                        if client_timestamp_utc:
                            user_message_metadata["client_timestamp_utc"] = client_timestamp_utc
                        if client_timezone_offset != 0:
                            user_message_metadata["client_timezone_offset"] = client_timezone_offset

                        user_message = Message(
                            run_id=run_id,
                            session_id=session_id,
                            role=Role.HUMAN,
                            content=user_input,
                            metadata=user_message_metadata
                        )

                        # Create Run object with client timestamp in metadata and add the initial message to its history
                        run_metadata = {}
                        if client_timestamp_utc:
                            run_metadata["client_timestamp_utc"] = client_timestamp_utc
                        if client_timezone_offset != 0:
                            run_metadata["client_timezone_offset"] = client_timezone_offset

                        run = Run(
                            id=run_id,
                            session_id=session_id,
                            status=RunStatus.PENDING,
                            metadata=run_metadata
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
                        await websocket.send_text(self._create_error_response(ERROR_MSG_INVALID_JSON))
                    except Exception as e:
                        logger.error(f"Error processing message from session_id={session_id}: {e}")
                        await websocket.send_text(self._create_error_response(ERROR_MSG_PROCESSING))

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session_id={session_id}")
            except Exception as e:
                logger.error(f"WebSocket error for session_id={session_id}: {e}")
            finally:
                # Clean up the connection
                if session_id in self.connections:
                    del self.connections[session_id]
                    logger.info(f"Cleaned up connection for session_id={session_id}")

        logger.info("WebSocket routes added to FastAPI application")
