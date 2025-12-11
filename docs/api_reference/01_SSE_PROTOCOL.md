# SSE Protocol Reference

This document describes the Server-Sent Events (SSE) protocol used for real-time communication between AURA frontend and NEXUS backend.

## Overview

NEXUS uses HTTP + SSE architecture for real-time communication:

- **Chat Messages**: `POST /api/v1/chat` returns SSE stream
- **Command Execution**: `POST /api/v1/commands/execute` returns JSON
- **Connection State**: `GET /api/v1/stream/{public_key}` returns persistent SSE stream

---

## Endpoints

### POST /api/v1/chat

Send a chat message and receive streaming AI response.

**Request:**
```http
POST /api/v1/chat
Authorization: Bearer <public_key>
Content-Type: application/json

{
  "content": "Hello, how are you?",
  "client_timestamp_utc": "2025-12-11T03:00:00Z",
  "client_timezone_offset": -480
}
```

**Response:** `text/event-stream`

The response is an SSE stream containing the following events:

```
event: run_started
data: {"event":"run_started","run_id":"run_abc123","payload":{"owner_key":"0x...","user_input":"Hello"}}

event: text_chunk
data: {"event":"text_chunk","run_id":"run_abc123","payload":{"chunk":"Hi there!","is_final":false}}

event: tool_call_started
data: {"event":"tool_call_started","run_id":"run_abc123","payload":{"tool_name":"web_search","args":{"query":"..."}}}

event: tool_call_finished
data: {"event":"tool_call_finished","run_id":"run_abc123","payload":{"tool_name":"web_search","status":"success","result":"..."}}

event: run_finished
data: {"event":"run_finished","run_id":"run_abc123","payload":{"status":"completed"}}
```

---

### POST /api/v1/commands/execute

Execute a system command synchronously.

**Request:**
```http
POST /api/v1/commands/execute
Authorization: Bearer <public_key>
Content-Type: application/json

{
  "command": "/ping",
  "args": [],
  "auth": {
    "publicKey": "0x...",
    "signature": "0x..."
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "pong",
  "data": {
    "latency_ms": 42
  }
}
```

The `auth` field is only required for commands that require signature verification (e.g., `/identity`).

---

### GET /api/v1/stream/{public_key}

Establish a persistent SSE connection for connection state and proactive events.

**Request:**
```http
GET /api/v1/stream/0xABC123...
```

**Response:** `text/event-stream`

The first event is always `connection_state`:

```
event: connection_state
data: {"visitor": false}
```

Subsequent events may include:
- `command_result`: Results from commands executed via the persistent stream
- Keepalive comments (`: keepalive`) every 30 seconds

---

## Event Types

### run_started

Indicates the start of a new AI conversation turn.

```json
{
  "event": "run_started",
  "run_id": "run_abc123",
  "payload": {
    "owner_key": "0x...",
    "user_input": "Hello, how are you?"
  }
}
```

### text_chunk

A chunk of AI-generated text (streamed incrementally).

```json
{
  "event": "text_chunk",
  "run_id": "run_abc123",
  "payload": {
    "chunk": "Hello! I'm doing",
    "role": "AI",
    "is_final": false
  }
}
```

### tool_call_started

Indicates the AI is invoking a tool.

```json
{
  "event": "tool_call_started",
  "run_id": "run_abc123",
  "payload": {
    "tool_name": "web_search",
    "args": {
      "query": "weather in Tokyo"
    }
  }
}
```

### tool_call_finished

Tool execution completed.

```json
{
  "event": "tool_call_finished",
  "run_id": "run_abc123",
  "payload": {
    "tool_name": "web_search",
    "status": "success",
    "result": "Current weather in Tokyo: 15°C, partly cloudy"
  }
}
```

### run_finished

The AI conversation turn has completed.

```json
{
  "event": "run_finished",
  "run_id": "run_abc123",
  "payload": {
    "status": "completed",
    "final_content": "..."
  }
}
```

### error

An error occurred during processing.

```json
{
  "event": "error",
  "run_id": "run_abc123",
  "payload": {
    "message": "Error description",
    "details": "Optional details"
  }
}
```

### connection_state

Connection state information (sent on persistent stream connection).

```json
{
  "event": "connection_state",
  "run_id": "connect_xxx",
  "payload": {
    "visitor": false
  }
}
```

### command_result

Result of a command execution (sent via persistent stream).

```json
{
  "event": "command_result",
  "run_id": "cmd_xxx",
  "payload": {
    "command": "/ping",
    "result": {
      "status": "success",
      "message": "pong",
      "data": {}
    }
  }
}
```

---

## Authentication

All endpoints require authentication via Bearer token:

```http
Authorization: Bearer <public_key>
```

The `public_key` is the user's Ethereum-style public key used for identity.

For commands requiring signature verification (e.g., `/identity`), include an `auth` object:

```json
{
  "auth": {
    "publicKey": "0x...",
    "signature": "0x..."
  }
}
```

The signature is an ECDSA signature of the command string.

---

## Error Handling

### HTTP Errors

| Status | Description |
|--------|-------------|
| 401 | Missing or invalid Authorization header |
| 403 | Signature verification failed |
| 500 | Internal server error |
| 503 | Service unavailable |

### SSE Errors

Errors during streaming are sent as `error` events:

```
event: error
data: {"event":"error","run_id":"...","payload":{"message":"Error description"}}
```

---

## Keepalive

SSE streams send keepalive comments every 30 seconds to prevent proxy timeouts:

```
: keepalive

```

Clients should ignore comment lines (lines starting with `:`).

---

## Migration from WebSocket

If migrating from the previous WebSocket implementation:

| WebSocket | SSE |
|-----------|-----|
| `ws://host/api/v1/ws/{public_key}` | `GET /api/v1/stream/{public_key}` |
| `{ type: "user_message", payload: {...} }` | `POST /api/v1/chat` |
| `{ type: "system_command", payload: {...} }` | `POST /api/v1/commands/execute` |
| Server events via WebSocket | Server events via SSE |

Event payload structures remain identical between WebSocket and SSE.
