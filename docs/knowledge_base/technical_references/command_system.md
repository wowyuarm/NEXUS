# Command System

## Overview

The NEXUS Command System is a **deterministic, extensible, and type-safe framework** for executing user-invoked operations across the NEXUS backend and AURA frontend. Commands provide a structured way to perform system-level actions (e.g., `/ping`, `/help`, `/identity`) that are distinct from natural language AI interactions.

This document provides **exhaustive implementation details** for understanding, extending, and troubleshooting the command system across both backend (NEXUS) and frontend (AURA).

**Key Characteristics:**
- **Auto-discovery**: Backend automatically discovers commands from `nexus/commands/definition/`
- **Tri-modal execution**: Commands can be client-side, WebSocket-based, or REST-based
- **Typed contracts**: Strong TypeScript/Python type definitions ensure frontend-backend alignment
- **Signature support**: Optional cryptographic signing for authenticated commands
- **Graceful degradation**: Fallback commands ensure basic functionality when backend is unavailable

---

## Architecture Context

### System Position

```
┌─────────────────────────────────────────────────────────────┐
│                        AURA Frontend                        │
├─────────────────────────────────────────────────────────────┤
│  User Input ("/command")                                    │
│       ↓                                                      │
│  CommandPalette (UI) → commandExecutor (routing logic)      │
│       ↓                          ↓                  ↓        │
│   client handler         websocket handler    rest handler  │
│   (local exec)           (WS to backend)      (HTTP API)    │
└──────────────┬──────────────────┬──────────────────┬────────┘
               │                  │                  │
               │         ┌────────▼──────────────────▼────────┐
               │         │       NEXUS Backend               │
               │         ├───────────────────────────────────┤
               │         │  WebSocket Interface              │
               │         │       ↓                            │
               │         │  NexusBus (Topics.SYSTEM_COMMAND) │
               │         │       ↓                            │
               │         │  CommandService (execution)       │
               │         │       ↓                            │
               │         │  NexusBus (Topics.COMMAND_RESULT) │
               │         │       ↓                            │
               │         │  WebSocket Interface              │
               │         └────────┬──────────────────────────┘
               │                  │
               └──────────────────▼
                    chatStore updates SYSTEM message
```

### Design Philosophy

1. **Separation of Concerns**: Commands are **deterministic actions**, AI interactions are **generative responses**
2. **Channel Purity**: 
   - REST API (`/api/v1/commands`) - metadata discovery (one-time, on app start)
   - WebSocket - real-time command execution and results
   - Client-side - local operations without network round-trip
3. **Fail-Safe**: Fallback commands ensure critical operations (like `/help`) work offline

---

## Detailed Breakdown

### 1. Backend: Command Discovery and Registration

**File**: `nexus/services/command.py`

#### Auto-Discovery Mechanism

On service initialization, `CommandService` scans `nexus/commands/definition/` for Python modules:

```python
# Discovery flow
package = importlib.import_module('nexus.commands.definition')
for _, modname, ispkg in pkgutil.iter_modules(package.__path__):
    if not ispkg:
        full_module_name = f"nexus.commands.definition.{modname}"
        # Look for COMMAND_DEFINITION and execute() function
        self._process_module_for_commands(full_module_name)
```

**Requirements for a valid command module:**
1. Must contain `COMMAND_DEFINITION` dict with keys:
   - `name` (str): Unique command identifier (without `/` prefix)
   - `description` (str): Human-readable purpose
   - `usage` (str): Display string (e.g., `/ping`)
   - `handler` (str): One of `"client"`, `"websocket"`, `"rest"`
   - `examples` (list[str]): Usage examples
   - `requiresSignature` (bool, optional): Triggers signature verification

2. Must contain async `execute(context: Dict[str, Any]) -> Dict[str, Any]` function

**Example** (`ping.py`):
```python
COMMAND_DEFINITION = {
    "name": "ping",
    "description": "Test system connectivity",
    "usage": "/ping",
    "handler": "websocket",
    "examples": ["/ping"]
}

async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": "success",
        "message": "pong",
        "data": {"latency_ms": 0.5, "nexus_version": "0.2.0"}
    }
```

#### Command Execution Flow

1. **Receive**: WebSocket message with `type: "system_command"`, `payload.command: "/ping"`
2. **Parse**: Extract command name (`ping`), optional `auth` data
3. **Verify Signature** (if `requiresSignature: true`):
   - Hash command with keccak256
   - Recover public key from signature
   - Validate against provided `publicKey`
4. **Build Context**:
   ```python
   context = {
       'command_name': 'ping',
       'command_definitions': self._command_definitions,
       'public_key': verified_public_key,  # if signed
       **self.services  # database_service, config_service, etc.
   }
   ```
5. **Execute**: `result = await executor(context)`
6. **Publish**: Send to `Topics.COMMAND_RESULT` → WebSocket → frontend

---

### 2. Backend: REST API for Metadata

**File**: `nexus/interfaces/rest.py`

**Endpoint**: `GET /api/v1/commands`

**Purpose**: Provide frontend with list of all available commands and their metadata (handler type, description, etc.)

**Response Example**:
```json
[
  {
    "name": "ping",
    "description": "Test system connectivity",
    "usage": "/ping",
    "handler": "websocket",
    "examples": ["/ping"]
  },
  {
    "name": "help",
    "description": "Display available commands",
    "usage": "/help",
    "handler": "client",
    "examples": ["/help"]
  }
]
```

**Called**: Once at AURA app startup by `useCommandLoader` hook

---

### 3. Frontend: Command Discovery (useCommandLoader)

**File**: `aura/src/features/command/hooks/useCommandLoader.ts`

**Lifecycle**:
```typescript
// On app mount
useEffect(() => {
  loadCommands();  // Fetch from /api/v1/commands
}, []);

// Success: populate commandStore.availableCommands
// Failure: use FALLBACK_COMMANDS
```

**Fallback Commands** (used when backend is unreachable):
```typescript
const FALLBACK_COMMANDS = [
  { name: 'ping', handler: 'websocket', ... },
  { name: 'help', handler: 'client', ... },
  { name: 'clear', handler: 'client', ... }
];
// Note: 'identity' is intentionally excluded (requires backend + signature)
```

**Design Rationale**: Fallback commands are an **emergency toolkit**—only include commands that:
- Are critical for diagnosing issues (`/ping`)
- Work purely client-side (`/help`, `/clear`)

---

### 4. Frontend: Command Execution (commandExecutor)

**File**: `aura/src/features/command/commandExecutor.ts`

#### Tri-Modal Handler Routing

```typescript
export async function executeCommand(command: Command): Promise<CommandResult> {
  if (isClientCommand(command)) {
    return await executeClientCommand(command);
  } else if (isWebSocketCommand(command)) {
    return await executeWebSocketCommand(command);
  } else if (isRestCommand(command)) {
    return await executeRestCommand(command);
  }
}
```

#### Handler Type 1: Client

**When**: Command can execute entirely in the browser (e.g., `/clear`, `/help`)

**Process**:
1. Execute synchronously without network calls
2. Update chatStore directly if UI changes needed
3. Return `{ status: 'success' }`

**Example** (`/help`):
```typescript
case 'help': {
  const commands = useCommandStore.getState().availableCommands;
  const helpText = commands.map(c => `**/${c.name}** - ${c.description}`).join('\n\n');
  
  // Create SYSTEM message
  const systemMsg: Message = {
    id: uuidv4(),
    role: 'SYSTEM',
    content: { command: '/help', result: helpText },
    timestamp: new Date(),
    metadata: { status: 'completed' }
  };
  
  useChatStore.setState(state => ({ messages: [...state.messages, systemMsg] }));
  return { status: 'success', message: 'Help displayed' };
}
```

**No Network Traffic**: Client commands do not trigger WebSocket or HTTP requests

---

#### Handler Type 2: WebSocket

**When**: Command requires backend execution (e.g., `/ping`, `/identity`)

**Process**:
1. **Create Pending Message** (crucial for race-condition prevention):
   ```typescript
   const pendingMsg: Message = {
     id: uuidv4(),
     role: 'SYSTEM',
     content: { command: commandText },  // "/ping"
     timestamp: new Date(),
     metadata: { status: 'pending' }
   };
   useChatStore.setState(state => ({ messages: [...state.messages, pendingMsg] }));
   ```

2. **Sign Command** (if `requiresSignature`):
   ```typescript
   const auth = await IdentityService.signCommand(commandText);
   // auth = { publicKey: '0x...', signature: '0x...' }
   ```

3. **Send via WebSocket**:
   ```typescript
   websocketManager.sendCommand(commandText, auth);
   ```

4. **Backend Processing**: CommandService executes, publishes result

5. **Receive Result**: `chatStore.handleCommandResult` updates the pending message:
   ```typescript
   // Find pending message by command text
   // Update content.result and metadata.status = 'completed'
   ```

**Result Payload Contract** (as of latest refactor):
```typescript
{
  event: "command_result",
  run_id: "...",
  payload: {
    command: "/ping",      // Command echo (prevents race mis-assignment)
    result: {              // Actual result
      status: "success",
      message: "pong",
      data: { latency_ms: 0.5 }
    }
  }
}
```

---

#### Handler Type 3: REST

**When**: Future stateless operations (not currently used)

**Process**:
1. Construct HTTP request from `command.restOptions`
2. Execute fetch with appropriate method/headers
3. Return parsed response

**Configuration**:
```typescript
interface RestOptions {
  endpoint: string;      // '/api/v1/execute'
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  headers?: Record<string, string>;
}
```

---

### 5. Frontend: UI Components

#### CommandPalette

**File**: `aura/src/features/command/components/CommandPalette.tsx`

**Trigger**: User types `/` in chat input

**Display**: Filtered list of commands matching input (e.g., `/p` shows `/ping`)

**Features**:
- Keyboard navigation (↑/↓ to select, Enter to execute)
- Mouse hover selection
- Real-time filtering on `command.name`

**Data Source**: `commandStore.availableCommands` (populated by `useCommandLoader`)

---

#### SYSTEM Message Rendering

**File**: `aura/src/features/chat/components/ChatMessage.tsx`

**Structure**:
```
■ /ping                    ← command (always shown)
━━━━━━━━━━━━━━━━━━        ← divider (only when result exists)
latency_ms: 0.5            ← result (formatted based on type)
nexus_version: 0.2.0
timestamp: 1234567890.123
```

**Result Formatting Logic**:
- **String**: Render as markdown
- **Object**: Key-value pairs with smart type formatting:
  - `boolean` → `✓` or `✗`
  - `number` → direct display
  - `string` → direct display
  - `array` (primitives) → bullet list
  - `array` (objects) → preview first 2 items + "...and N more"
  - Complex objects → JSON code block

**Pending State**: Shows command only, no divider/result until `status: 'completed'`

---

### 6. Type Contracts and Validation

#### Frontend Types (`command.types.ts`)

```typescript
type CommandHandler = 'client' | 'websocket' | 'rest';

interface Command {
  name: string;
  description: string;
  usage: string;
  handler: CommandHandler;
  requiresSignature?: boolean;
  examples: string[];
  restOptions?: RestOptions;
}

interface CommandResult {
  status: 'success' | 'error' | 'pending';
  message: string;
  data?: Record<string, unknown>;
}
```

#### Backend Definition (Python dict)

```python
COMMAND_DEFINITION = {
    "name": str,
    "description": str,
    "usage": str,
    "handler": "client" | "websocket" | "rest",
    "examples": list[str],
    "requiresSignature": bool  # optional
}
```

**Contract Enforcement**: Frontend TypeScript types are authoritative. Backend definitions must match for proper serialization via `/api/v1/commands`.

---

## Integration Points

### 1. WebSocket Protocol

**Message Flow**:

**Client → Backend** (system_command):
```json
{
  "type": "system_command",
  "payload": {
    "command": "/ping",
    "session_id": "0x...",
    "auth": {                    // optional (if requiresSignature)
      "publicKey": "0x...",
      "signature": "0x..."
    }
  }
}
```

**Backend → Client** (command_result):
```json
{
  "event": "command_result",
  "run_id": "run_abc123",
  "payload": {
    "command": "/ping",          // echoed back (prevents race conditions)
    "result": {
      "status": "success",
      "message": "pong",
      "data": { "latency_ms": 0.5 }
    }
  }
}
```

**Integration Files**:
- Backend: `nexus/interfaces/websocket.py` (lines 140-174: `handle_command_result`)
- Frontend: `aura/src/services/websocket/protocol.ts` (CommandResultPayload type)

---

### 2. NexusBus Event Topics

**Topic**: `Topics.SYSTEM_COMMAND`
- **Publisher**: `WebsocketInterface` (on receiving client command)
- **Subscriber**: `CommandService.handle_command`

**Topic**: `Topics.COMMAND_RESULT`
- **Publisher**: `CommandService._publish_result`
- **Subscriber**: `WebsocketInterface.handle_command_result`

**Data Flow**:
```
User → WS → WebsocketInterface → SYSTEM_COMMAND topic → CommandService
CommandService → COMMAND_RESULT topic → WebsocketInterface → WS → chatStore
```

---

### 3. Identity and Cryptography

**For commands with `requiresSignature: true`:**

**Frontend** (`IdentityService.signCommand`):
1. Retrieve user's private key from localStorage
2. Hash command with keccak256: `hash = keccak(command.encode('utf-8'))`
3. Sign hash with secp256k1: `signature = privateKey.sign(hash)`
4. Return `{ publicKey: address, signature: hex }`

**Backend** (`CommandService._verify_signature`):
1. Hash command identically: `message_hash = keccak(command_str.encode('utf-8'))`
2. Recover public key from signature
3. Validate recovered address matches provided `publicKey`
4. Inject `verified_public_key` into execution context

**Integration Files**:
- Frontend: `aura/src/services/identity/identity.ts`
- Backend: `nexus/services/command.py` (lines 280-370)

---

### 4. State Management (chatStore)

**Command Result Handling** (`chatStore.handleCommandResult`):

**Payload Types**:
1. **Wrapped** (preferred, as of latest refactor):
   ```typescript
   { command: "/ping", result: { status: "success", ... } }
   ```
2. **Raw** (legacy fallback):
   ```typescript
   { status: "success", message: "...", data: {...} }
   ```

**Matching Strategy** (to update correct pending message):
1. **Primary**: Find by `command` text match in pending SYSTEM messages
2. **Fallback**: Find most recent pending SYSTEM message (last-in-first-out)

**Race Condition Prevention**: The wrapped payload with explicit `command` field ensures concurrent commands (`/ping` + `/identity`) update their respective messages accurately.

---

## Environment-Specific Behavior

### Local Development

**Backend**:
- Commands auto-discovered from `nexus/commands/definition/`
- Logs command execution at INFO level
- No CORS restrictions on REST API if `ALLOWED_ORIGINS` includes `localhost:5173`

**Frontend**:
- Fetches commands from `http://localhost:8000/api/v1/commands`
- WebSocket connects to `ws://localhost:8000/api/v1/ws/{publicKey}`
- Fallback commands kick in if backend not running

**Environment Variables**:
```bash
# Backend (.env)
NEXUS_ENV=development
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Frontend (aura/.env or vite config)
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/api/v1/ws
```

---

### Production (Render)

**Backend**:
- Same auto-discovery mechanism
- CORS configured via `ALLOWED_ORIGINS` environment variable:
  ```bash
  ALLOWED_ORIGINS=https://your-aura-app.onrender.com
  ```
- WebSocket uses WSS (secure) if behind HTTPS proxy

**Frontend**:
- Fetches commands from production API URL
- WebSocket uses `wss://` protocol
- Fallback commands still available if connection lost

**Critical**: Ensure `ALLOWED_ORIGINS` matches exact frontend URL in production, or CORS preflight will fail (HTTP 400/405).

---

## Common Issues and Troubleshooting

### Issue 1: "Unknown command" or Missing Commands in Palette

**Symptoms**:
- CommandPalette shows only 3 fallback commands
- `/identity` or custom commands not listed

**Diagnosis**:
```typescript
// Check browser console:
"⚠️ Failed to load commands from backend, using fallback"
```

**Root Causes**:
1. **CORS Failure**: Backend `ALLOWED_ORIGINS` doesn't include frontend URL
   - **Check**: Browser Network tab → `/api/v1/commands` → Status 400/405
   - **Fix**: Add frontend origin to `.env`:
     ```bash
     ALLOWED_ORIGINS=http://localhost:5173  # or your Vite port
     ```
   - **Restart backend** to apply

2. **Backend Not Running**: NEXUS service down or not reachable
   - **Check**: `curl http://localhost:8000/api/v1/commands`
   - **Fix**: Start backend with `python -m nexus.main`

3. **Network Error**: Firewall or incorrect API URL
   - **Check**: `aura/src/features/command/api.ts` → `API_BASE_URL`
   - **Fix**: Ensure `VITE_API_BASE_URL` environment variable is correct

---

### Issue 2: Command Result Shows "unknown" Title

**Symptoms**:
```
■ unknown           ← Should be "■ /ping"
━━━━━━━━━━━━━━━━━━
pong
```

**Root Cause**: Pending SYSTEM message wasn't created before sending WebSocket command

**Fixed In**: Latest refactor (commit `bac76a9`) - `commandExecutor.ts` now creates pending message before `websocketManager.sendCommand()`

**Verification**:
```typescript
// In commandExecutor.ts (executeWebSocketCommand)
const pendingMsg: Message = {
  content: { command: commandText },  // "/ping" stored here
  metadata: { status: 'pending' }
};
useChatStore.setState(...);  // Add pending message
websocketManager.sendCommand(...);   // Then send
```

---

### Issue 3: Concurrent Commands Overwrite Each Other

**Symptoms**: Execute `/ping` and `/identity` quickly → both show same result

**Root Cause**: Old implementation used "most recent pending" matching, causing race condition

**Solution**: Backend now wraps payload with `command` field:
```typescript
payload: { command: "/ping", result: {...} }
```

Frontend matches by exact command text, not just recency.

**Files**:
- Backend: `nexus/interfaces/websocket.py` (lines 160-180)
- Frontend: `aura/src/features/chat/store/chatStore.ts` (lines 345-365)

---

### Issue 4: `/help` Triggers Network Request

**Symptoms**: Network tab shows WebSocket message when executing `/help`

**Root Cause**: `/help` handler set to `"websocket"` instead of `"client"`

**Fix**:
```python
# nexus/commands/definition/help.py
COMMAND_DEFINITION = {
    "handler": "client"  # Not "websocket"
}
```

**Verification**: Execute `/help` → check Network tab → no new WS frames

---

### Issue 5: Command Result Array Shows Ugly JSON

**Symptoms**:
```
**data:** [{"id":1,"name":"test"},{"id":2,"name":"test2"}]
```

**Enhancement** (as of latest refactor):
```typescript
// ChatMessage.tsx formatObjectResult
if (Array.isArray(value)) {
  const isPrimitiveArray = value.every(v => ['string','number','boolean'].includes(typeof v));
  if (isPrimitiveArray) {
    formattedValue = value.map(v => `- ${v}`).join('\n');
  } else {
    const preview = JSON.stringify(value.slice(0,2), null, 2);
    formattedValue = '```json\n' + preview + '\n```\n... and N more';
  }
}
```

**Result**:
```
**items:**
- item1
- item2
- item3
```

---

## Adding a New Command

### Step 1: Create Command Module

**Location**: `nexus/commands/definition/my_command.py`

```python
"""
My custom command definition.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

COMMAND_DEFINITION = {
    "name": "mycommand",
    "description": "Does something useful",
    "usage": "/mycommand",
    "handler": "websocket",  # or "client"
    "examples": ["/mycommand"],
    "requiresSignature": False  # optional
}

async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the command.
    
    Args:
        context: Contains command_name, command_definitions, injected services
        
    Returns:
        Dict with status, message, and optional data
    """
    try:
        # Your logic here
        result = {
            "status": "success",
            "message": "Command executed",
            "data": {"key": "value"}
        }
        return result
    except Exception as e:
        logger.error(f"Command failed: {e}")
        raise RuntimeError(str(e))
```

### Step 2: Auto-Discovery (Automatic)

No manual registration needed. `CommandService` will discover on next backend restart.

### Step 3: Restart Backend

```bash
cd /home/wowyuarm/projects/NEXUS
source .venv/bin/activate
python -m nexus.main
```

**Verify in logs**:
```
CommandService initialized with 5 commands  # count increased
Registered command: mycommand from nexus.commands.definition.my_command
```

### Step 4: Frontend Auto-Sync

AURA will fetch updated command list on next page load via `/api/v1/commands`.

**Verify**: Type `/` in chat → see new command in palette

---

## Testing Commands

### Backend Unit Test

**Location**: `tests/nexus/unit/services/test_command_service.py`

```python
@pytest.mark.asyncio
async def test_mycommand_execution(command_service):
    """Test mycommand executes successfully."""
    input_message = Message(
        run_id="test-run",
        session_id="test-session",
        role=Role.COMMAND,
        content="/mycommand"
    )
    
    await command_service.handle_command(input_message)
    
    # Assert: check mock_bus.publish was called with expected result
    mock_bus.publish.assert_called_once()
    result_message = mock_bus.publish.call_args[0][1]
    assert result_message.content["status"] == "success"
```

### Frontend Integration Test

**Location**: `aura/src/features/command/hooks/__tests__/useCommandLoader.test.ts`

Ensure new command appears in fetched list:
```typescript
expect(commands.map(c => c.name)).toContain('mycommand');
```

---

## Performance Considerations

### Command Execution Latency

**Client Commands**: < 10ms (synchronous, no network)

**WebSocket Commands**:
- Network RTT: ~50-200ms (local dev)
- Backend execution: varies by command (e.g., `/ping` < 1ms, database queries may be 10-100ms)
- Total: typically 100-300ms for simple commands

**Optimization Tips**:
- Use `client` handler for operations that don't require backend data
- Cache command metadata in frontend (`commandStore`)
- Avoid blocking operations in `execute()` functions

### Command Discovery Overhead

**On Backend Startup**: ~50-200ms to scan and register all commands

**On Frontend Startup**: Single REST API call (~100ms)

**Not a Bottleneck**: Discovery happens once, cached for session lifetime

---

## Security Considerations

### Signature Verification

**Purpose**: Prevent command spoofing (ensure command originates from holder of private key)

**When to Use**: Commands that:
- Modify user state
- Access sensitive data
- Perform privileged operations

**Implementation**:
```python
COMMAND_DEFINITION = {"requiresSignature": True}
```

**Attack Vectors**:
- **Replay**: Not prevented (same signature can be reused). Consider adding nonce if needed.
- **MitM**: Signatures are sent over WebSocket. Use WSS in production.

### Command Injection

**Not Applicable**: Commands are pre-defined, not dynamically constructed from user input. Command name is validated against registry.

---

## Future Enhancements

### Planned Features

1. **REST Handler Implementation**: Full support for stateless HTTP-based commands
2. **Command Arguments**: Structured parameters (e.g., `/search query:text limit:10`)
3. **Command Aliases**: Short forms (e.g., `/p` → `/ping`)
4. **Command History**: Navigate previous commands with ↑/↓ in input
5. **Batch Commands**: Execute multiple commands in sequence

### Extension Points

1. **Custom Result Renderers**: Register type-specific formatters for SYSTEM messages
2. **Command Middleware**: Pre/post-execution hooks (logging, analytics, validation)
3. **Dynamic Command Registration**: Runtime command addition without restart

---

## References

### Related Documentation

- **Architecture Overview**: `../02_NEXUS_ARCHITECTURE.md`
- **Environment Setup**: `environment_configuration.md`
- **WebSocket Protocol**: `aura/src/services/websocket/protocol.ts` (inline docs)
- **Identity System**: `aura/src/services/identity/identity.ts`

### Key Code Files

**Backend**:
- `nexus/services/command.py` - CommandService implementation
- `nexus/commands/definition/` - All command definitions
- `nexus/interfaces/rest.py` - `/api/v1/commands` endpoint
- `nexus/interfaces/websocket.py` - Command result publishing

**Frontend**:
- `aura/src/features/command/commandExecutor.ts` - Execution router
- `aura/src/features/command/hooks/useCommandLoader.ts` - Discovery hook
- `aura/src/features/command/components/CommandPalette.tsx` - UI component
- `aura/src/features/chat/components/ChatMessage.tsx` - Result rendering
- `aura/src/features/chat/store/chatStore.ts` - Result handling

### External Resources

- **Ethereum Signature Standard**: EIP-191 (message signing)
- **WebSocket Protocol**: RFC 6455

---

**Last Updated**: 2025-10-07  
**Version**: NEXUS v0.2.0  
**Maintainer**: AI Collaboration Team

