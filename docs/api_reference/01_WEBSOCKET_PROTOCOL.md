# 01: WebSocket Protocol

This document specifies the WebSocket communication protocol between the AURA client and the NEXUS server.

-   **Endpoint**: `ws://<host>:<port>/api/v1/ws/{session_id}`
-   **Data Format**: All messages are JSON strings.

---

## I. Client-to-Server Messages

Messages sent from AURA to NEXUS.

### 1. `user_message`

-   **Purpose**: To send a user's conversational input to the backend and initiate a new `Run`.
-   **Structure**:
    ```json
    {
      "type": "user_message",
      "payload": {
        "content": "The user's text input.",
        "session_id": "The client's persistent session ID."
      }
    }
    ```
-   **Fields**:
    -   `type`: Must be the string `"user_message"`.
    -   `payload.content`: `string` - The raw text entered by the user.
    -   `payload.session_id`: `string` - The persistent session ID retrieved from the client's `localStorage`.

### 2. `ping`

-   **Purpose**: A heartbeat message sent periodically by the client to keep the WebSocket connection alive and verify its health.
-   **Structure**:
    ```json
    {
      "type": "ping"
    }
    ```
-   **Server Response**: The server will not send a direct `pong` response. It acknowledges the connection is alive internally.

---

## II. Server-to-Client Messages (UI Events)

Messages broadcast from NEXUS to AURA. All server-to-client messages follow a standard envelope structure.

**Standard Envelope:**
```json
{
  "event": "<event_type_string>",
  "run_id": "<unique_run_identifier>",
  "payload": { ... }
}
```

### 1. `run_started`

-   **Purpose**: Signals that the backend has successfully received a `user_message`, created a `Run`, and is beginning the thinking process. This is the trigger for AURA's initial "thinking" animation.
-   **Payload (`payload`)**:
    ```json
    {
      "session_id": "The session ID for this run.",
      "user_input": "The original user input that started this run."
    }
    ```

### 2. `text_chunk`

-   **Purpose**: Delivers a piece of the AI's response in a stream. A single AI response may be broken into multiple `text_chunk` events.
-   **Payload (`payload`)**:
    ```json
    {
      "chunk": "A segment of the AI's text response."
    }
    ```

### 3. `tool_call_started`

-   **Purpose**: Signals that the AI has decided to use a tool and the execution is beginning. This triggers the rendering of a `ToolCallCard` in AURA.
-   **Payload (`payload`)**:
    ```json
    {
      "tool_name": "The name of the tool being called (e.g., 'web_search').",
      "args": { ... } // An object containing the arguments for the tool.
    }
    ```

### 4. `tool_call_finished`

-   **Purpose**: Signals that a tool has finished executing. This triggers an update to the corresponding `ToolCallCard`'s state in AURA.
-   **Payload (`payload`)**:
    ```json
    {
      "tool_name": "The name of the tool that finished.",
      "status": "'success' | 'error'",
      "result": "A string representation of the tool's output or error message."
    }
    ```

### 5. `run_finished`

-   **Purpose**: Signals that the entire `Run` has concluded (either successfully, with an error, or timed out). This allows AURA to reset its state to `idle` and re-enable the user input.
-   **Payload (`payload`)**:
    ```json
    {
      "status": "'completed' | 'failed' | 'timed_out'"
    }
    ```

### 6. `error`

-   **Purpose**: Signals that a critical, unrecoverable error occurred during the `Run`.
-   **Payload (`payload`)**:
    ```json
    {
      "message": "A user-friendly error message.",
      "details": "Optional technical details about the error."
    }
    ```