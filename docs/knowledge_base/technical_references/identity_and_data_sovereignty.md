# Identity and Data Sovereignty System

## Overview

The NEXUS Identity and Data Sovereignty system establishes a **cryptographic identity-based data isolation architecture** where every piece of user data is strictly bound to a user's cryptographic public key (`owner_key`). This system implements a "gatekeeper" mechanism that distinguishes between **visitors** (unregistered public keys) and **members** (registered users with persistent identity), ensuring that only authenticated members can access personalized AI services and persistent conversation history.

This document covers the complete implementation of the `DATA-SOVEREIGNTY-1.0` initiative, which replaced the legacy `session_id`-based architecture with a blockchain-inspired identity model.

**Key Concepts:**
- **Owner Key**: A user's Ethereum-compatible public key that serves as their unique identity and data ownership token
- **Gatekeeper Pattern**: Authorization mechanism that intercepts requests and enforces identity verification
- **Visitor vs. Member**: Two-tier user model where visitors receive guidance but no persistence, while members have full access
- **Identity Service**: Centralized service managing identity creation, verification, and retrieval

---

## Architecture Context

### Position in NEXUS Ecosystem

```
┌─────────────────────────────────────────────────────────────┐
│                        AURA (Frontend)                       │
│  ┌──────────────┐    ┌───────────────┐   ┌──────────────┐  │
│  │IdentityService│───▶│ WebSocket Mgr │───│ Chat Store   │  │
│  │(Key Gen/Sign)│    │ (public_key)  │   │(visitorMode) │  │
│  └──────────────┘    └───────────────┘   └──────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │ ws://nexus/api/v1/ws/{public_key}
┌────────────────────────────▼────────────────────────────────┐
│                       NEXUS (Backend)                        │
│  ┌──────────────────┐      ┌────────────────────────────┐  │
│  │WebSocketInterface│─────▶│   OrchestratorService      │  │
│  │(Routing)         │      │   (Gatekeeper Logic)       │  │
│  └──────────────────┘      └────────────┬───────────────┘  │
│                                          │                   │
│  ┌──────────────────┐      ┌────────────▼───────────────┐  │
│  │IdentityService   │◀─────│  PersistenceService        │  │
│  │(DB Operations)   │      │  (owner_key filtering)     │  │
│  └──────────┬───────┘      └────────────────────────────┘  │
│             │                                                │
│  ┌──────────▼───────────────────────────────────────────┐  │
│  │         MongoDB (identities + messages)              │  │
│  │  - identities: {public_key, created_at, metadata}    │  │
│  │  - messages: {owner_key, role, content, timestamp}   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Integration with Existing Systems

- **Event Bus (`NexusBus`)**: All identity checks happen asynchronously through event subscriptions
- **Command System**: `/identity` command triggers identity creation with cryptographic signature verification
- **LLM Services**: Only invoked for registered members; visitors bypass LLM entirely
- **Database Layer**: All queries now scoped by `owner_key` instead of ephemeral `session_id`

---

## Detailed Breakdown

### 1. Core Data Model

#### Message Model (`nexus/core/models.py`)

**Before (session_id-based):**
```python
class Message(BaseModel):
    run_id: str
    session_id: str  # ❌ Removed
    role: Role
    content: Union[str, Dict[str, Any]]
    timestamp: Optional[datetime] = None
```

**After (owner_key-based):**
```python
class Message(BaseModel):
    run_id: str
    owner_key: str  # ✅ User's cryptographic public key
    role: Role
    content: Union[str, Dict[str, Any]]
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
```

**Key Changes:**
- `session_id` → `owner_key`: Permanent identity instead of ephemeral session
- `owner_key` is an Ethereum-compatible address (e.g., `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb`)
- All database queries, event routing, and service calls now use `owner_key`

#### Run Model (`nexus/core/models.py`)

```python
class Run(BaseModel):
    run_id: str
    owner_key: str  # ✅ Changed from session_id
    messages: List[Message] = []
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

---

### 2. Database Layer

#### MongoDB Collections

**`identities` Collection Schema:**
```javascript
{
  "_id": ObjectId("..."),
  "public_key": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",  // Unique index
  "created_at": ISODate("2025-10-10T12:00:00Z"),
  "metadata": {
    // Future: user preferences, personalization settings
  }
}
```

**`messages` Collection Schema:**
```javascript
{
  "_id": ObjectId("..."),
  "run_id": "uuid-v4-string",
  "owner_key": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",  // Indexed for queries
  "role": "human|ai|system|tool",
  "content": "message content or structured data",
  "timestamp": ISODate("2025-10-10T12:01:30Z")
}
```

#### MongoProvider Changes (`nexus/services/database/providers/mongo.py`)

**New Initialization:**
```python
def connect(self):
    # ... existing connection logic ...
    
    # Initialize identities collection
    self.identities_collection = self.database.identities
    
    # Create unique index on public_key
    self.identities_collection.create_index(
        [("public_key", pymongo.ASCENDING)],
        unique=True
    )
```

**Key Methods:**

| Method | Purpose | Query Pattern |
|--------|---------|---------------|
| `get_messages_by_owner_key(owner_key: str, limit: int)` | Retrieve conversation history | `{"owner_key": owner_key}` |
| `find_identity_by_public_key(public_key: str)` | Check if user is registered | `{"public_key": public_key}` |
| `create_identity(identity_data: Dict)` | Register new member | `insert_one(identity_data)` |

**Example Usage:**
```python
# Check if user is registered
identity = await db_service.provider.find_identity_by_public_key(public_key)

if identity is None:
    # Visitor flow - no history access
    pass
else:
    # Member flow - load personalized history
    messages = await db_service.provider.get_messages_by_owner_key(
        owner_key=public_key, 
        limit=50
    )
```

---

### 3. Identity Service Layer

#### IdentityService (`nexus/services/identity.py`)

**Purpose:** Centralized service for all identity-related operations, abstracting database complexity.

**Dependency Injection:**
```python
class IdentityService:
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
```

**Core Methods:**

```python
async def get_identity(self, public_key: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve identity document for a given public key.
    
    Returns:
        - Identity document if registered
        - None if visitor (unregistered)
    """
    return await asyncio.to_thread(
        self.db_service.provider.find_identity_by_public_key,
        public_key
    )

async def create_identity(self, public_key: str, metadata: Optional[Dict] = None) -> bool:
    """
    Register a new member identity.
    
    Creates a permanent identity record binding public_key to user data.
    """
    identity_data = {
        'public_key': public_key,
        'created_at': datetime.now(timezone.utc),
        'metadata': metadata or {}
    }
    return await asyncio.to_thread(
        self.db_service.provider.create_identity,
        identity_data
    )

async def get_or_create_identity(self, public_key: str) -> Optional[Dict[str, Any]]:
    """
    Idempotent identity retrieval/creation.
    
    Used by /identity command to ensure member status.
    """
    identity = await self.get_identity(public_key)
    if identity:
        return identity
    
    success = await self.create_identity(public_key)
    if not success:
        return None
    
    new_identity = await self.get_identity(public_key)
    if new_identity:
        new_identity['_just_created'] = True
    return new_identity
```

**Service Wiring (`nexus/main.py`):**
```python
# Instantiate services in dependency order
database_service = DatabaseService(provider=mongo_provider)
identity_service = IdentityService(db_service=database_service)

# Inject into dependent services
orchestrator_service = OrchestratorService(
    bus=nexus_bus,
    identity_service=identity_service  # ✅ Injected
)

command_service = CommandService(
    bus=nexus_bus,
    database_service=database_service,
    identity_service=identity_service  # ✅ Injected for /identity command
)
```

---

### 4. Gatekeeper Mechanism

#### Implementation Location: `OrchestratorService.handle_new_run()`

**Flow Diagram:**
```
User sends message
      │
      ▼
WebSocketInterface wraps in Run(owner_key=public_key)
      │
      ▼
Publishes to RUNS_NEW topic
      │
      ▼
OrchestratorService.handle_new_run()
      │
      ├─ Extract owner_key from Run
      │
      ├─ Call identity_service.get_identity(owner_key)
      │
      ├─ if identity is None:  ◄── GATEKEEPER CHECK
      │   │
      │   ├─ Create guidance message (Role.SYSTEM)
      │   │   "身份未验证。请通过 /identity 指令创建..."
      │   │
      │   ├─ Publish to UI_EVENTS
      │   │
      │   └─ RETURN (stop processing) ◄── Visitor flow terminates here
      │
      └─ else:  ◄── Member flow continues
          │
          ├─ Publish CONTEXT_BUILD_REQUEST
          ├─ ContextService loads history by owner_key
          ├─ LLMService processes request
          └─ PersistenceService saves with owner_key
```

**Code Implementation (`nexus/services/orchestrator.py`):**
```python
async def handle_new_run(self, message: Message) -> None:
    run = Run(run_id=message.run_id, owner_key=message.owner_key, messages=[message])
    
    # ═══════════════════════════════════════════
    # GATEKEEPER: Identity Verification Check
    # ═══════════════════════════════════════════
    if self.identity_service:
        identity = await self.identity_service.get_identity(run.owner_key)
        
        if identity is None:
            # VISITOR FLOW: Unregistered public key
            logger.info(f"Unverified user attempted access: owner_key={run.owner_key}")
            
            # Send guidance message to frontend
            guidance_event = Message(
                run_id=run.run_id,
                owner_key=run.owner_key,
                role=Role.SYSTEM,
                content={
                    "status": "info",
                    "message": "身份未验证。请通过 /identity 指令创建或恢复您的永久身份，以保存对话。",
                    "data": {"restricted": True}
                }
            )
            await self.bus.publish(Topics.UI_EVENTS, guidance_event)
            
            # Publish run_finished to close the UI flow
            await self._publish_standardized_ui_event(
                run_id=run.run_id,
                owner_key=run.owner_key,
                event_type="run_finished",
                payload={"status": "visitor_guidance_sent"}
            )
            return  # ◄── CRITICAL: Stop processing here
    
    # MEMBER FLOW: Continue with normal conversation processing
    context_request = Message(
        run_id=run.run_id,
        owner_key=run.owner_key,
        role=Role.SYSTEM,
        content={"action": "build_context", "user_message": message.content}
    )
    await self.bus.publish(Topics.CONTEXT_BUILD_REQUEST, context_request)
```

**Key Behaviors:**

| User Type | Identity Check Result | LLM Called? | History Queried? | DB Writes? |
|-----------|----------------------|-------------|------------------|------------|
| **Visitor** | `None` | ❌ No | ❌ No | ❌ No |
| **Member** | `{public_key: ...}` | ✅ Yes | ✅ Yes | ✅ Yes |

---

### 5. Identity Command (`/identity`)

#### Purpose
The `/identity` command allows users to **claim their identity** by providing a cryptographic signature, proving ownership of their private key. This is the **only** way to transition from visitor to member status.

#### Command Definition (`nexus/commands/definition/identity.py`)

```python
COMMAND_DEFINITION = {
    "name": "identity",
    "description": "Verify your identity and display your public key through cryptographic signature",
    "usage": "/identity",
    "handler": "websocket",
    "requiresSignature": True,  # ✅ Enforces cryptographic proof
    "examples": ["/identity"]
}
```

#### Execution Flow

```
AURA Frontend                           NEXUS Backend
     │                                        │
     ├─ User types "/identity"                │
     │                                        │
     ├─ IdentityService.signCommand()        │
     │   └─ Signs command with private key   │
     │                                        │
     ├─ WebSocket.send({                     │
     │     type: "system_command",            │
     │     payload: {                         │
     │       command: "/identity",            │
     │       public_key: "0x...",             │
     │       auth: {                          │
     │         publicKey: "0x...",            │
     │         signature: "0x..."             │
     │       }                                │
     │     }                                  │
     │   })                ──────────────────▶│
     │                                        │
     │                                        ├─ CommandService.handle_command()
     │                                        │   │
     │                                        │   ├─ Verify signature (keccak256)
     │                                        │   │   ✅ Signature valid
     │                                        │   │
     │                                        │   ├─ Execute identity.execute(context)
     │                                        │   │   │
     │                                        │   │   ├─ context['public_key'] = verified_key
     │                                        │   │   │
     │                                        │   │   ├─ identity_service.get_or_create_identity()
     │                                        │   │   │   │
     │                                        │   │   │   ├─ Check DB for existing identity
     │                                        │   │   │   │
     │                                        │   │   │   ├─ If None: Create new identity
     │                                        │   │   │   │   └─ INSERT INTO identities
     │                                        │   │   │   │
     │                                        │   │   │   └─ Return identity doc
     │                                        │   │   │
     │                                        │   │   └─ Return success message
     │                                        │   │
     │                                        │   └─ Publish to COMMAND_RESULT
     │                                        │
     │◀──────────────────────────────────────┤ WebSocket.send({
     │                                        │   event: "command_result",
     │                                        │   payload: {
     │                                        │     status: "success",
     │                                        │     message: "✨ 身份已创建！...",
     │                                        │     data: {
     │                                        │       public_key: "0x...",
     │                                        │       verified: true,
     │                                        │       is_new: true
     │                                        │     }
     │                                        │   }
     │                                        │ })
     │                                        │
     ├─ ChatStore.handleCommandResult()      │
     │   └─ Display system message            │
     │                                        │
```

#### Command Execution Code (`nexus/commands/definition/identity.py`)

```python
async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    # Extract verified public key (already validated by signature check)
    public_key = context.get('public_key')
    if not public_key:
        raise RuntimeError("Public key not found in context")
    
    # Get IdentityService from dependency injection
    identity_service = context.get('identity_service')
    if not identity_service:
        raise RuntimeError("IdentityService not found in context")
    
    # Idempotent identity creation/retrieval
    identity = await identity_service.get_or_create_identity(public_key)
    
    if not identity:
        raise RuntimeError(f"Failed to create/retrieve identity for {public_key}")
    
    # Determine if this was a new registration or existing verification
    is_new = identity.get('_just_created', False)
    
    if is_new:
        message = f"✨ 身份已创建！您的主权身份已锚定到区块链公钥：{public_key[:10]}...{public_key[-8:]}"
    else:
        message = f"✅ 身份已验证！欢迎回来，您的公钥：{public_key[:10]}...{public_key[-8:]}"
    
    return {
        "status": "success",
        "message": message,
        "data": {
            "public_key": public_key,
            "verified": True,
            "is_new": is_new,
            "created_at": identity.get('created_at')
        }
    }
```

---

### 6. Frontend Integration

#### WebSocket Connection (`aura/src/services/websocket/manager.ts`)

**Old Route:** `/api/v1/ws/{session_id}`  
**New Route:** `/api/v1/ws/{public_key}`

```typescript
async connect(): Promise<void> {
  // Get persistent public key from IdentityService
  this.publicKey = await this._getPublicKey();
  
  // Construct WebSocket URL with public_key as route parameter
  const fullUrl = `${this.baseUrl}/${this.publicKey}`;
  
  this.ws = new WebSocket(fullUrl);
  
  this.ws.onopen = () => {
    this.isConnected = true;
    this.emitter.emit('connected', { publicKey: this.publicKey });
  };
  
  // Backend now sends connection_state event on connect
  this.ws.onmessage = (event) => {
    const nexusEvent = parseNexusEvent(event.data);
    this.emitter.emit(nexusEvent.event, nexusEvent.payload);
  };
}
```

#### Protocol Changes (`aura/src/services/websocket/protocol.ts`)

**New Event Type:**
```typescript
export interface ConnectionStatePayload {
  visitor: boolean;  // true if public_key is not registered
}

export type ConnectionStateEvent = {
  event: 'connection_state';
  run_id: string;
  owner_key: string;
  payload: ConnectionStatePayload;
};
```

**Message Payload Updates:**
```typescript
// All client messages now include public_key instead of session_id
export interface ClientMessage {
  type: 'user_message';
  payload: {
    content: string;
    public_key: string;  // ✅ Changed from session_id
    clientTimestamp: string;
  };
}

export interface SystemCommandMessage {
  type: 'system_command';
  payload: {
    command: string;
    public_key: string;  // ✅ Changed from session_id
    auth?: {
      publicKey: string;
      signature: string;
    };
  };
}
```

#### Chat Store Visitor Mode (`aura/src/features/chat/store/chatStore.ts`)

```typescript
interface ChatState {
  // ... existing state ...
  visitorMode: boolean;  // ✅ New field
}

const useChatStore = create<ChatState & ChatActions>((set, get) => ({
  visitorMode: false,
  
  // Handle connection_state event from backend
  handleConnectionState: (isVisitor: boolean) => {
    set({ visitorMode: isVisitor });
    
    if (isVisitor) {
      // Could show a banner or restrict UI
      console.log('🚫 Visitor mode: limited functionality until /identity');
    }
  },
  
  // Restrict commands in visitor mode
  executeCommand: async (command: string, availableCommands: Command[]) => {
    const { visitorMode } = get();
    
    if (visitorMode && !command.startsWith('/identity')) {
      // Block all commands except /identity for visitors
      return;
    }
    
    // Normal command execution...
  }
}));
```

#### UI Adaptations (`aura/src/features/chat/components/ChatInput.tsx`)

```typescript
interface ChatInputProps {
  visitorMode: boolean;  // ✅ New prop
  // ... other props
}

function ChatInput({ visitorMode, ... }: ChatInputProps) {
  const placeholder = visitorMode
    ? "输入 /identity 以完成身份验证"
    : "输入消息或 / 打开命令面板";
  
  const canSend = useMemo(() => {
    if (!input.trim()) return false;
    
    // In visitor mode, only allow commands (and only /identity)
    if (visitorMode && !input.startsWith('/')) {
      return false;
    }
    
    return true;
  }, [input, visitorMode]);
  
  return (
    <textarea placeholder={placeholder} ... />
    <button disabled={!canSend}>发送</button>
  );
}
```

#### Command Filtering (`aura/src/features/command/hooks/useCommandLoader.ts`)

```typescript
const loadCommands = async (visitorMode: boolean = false) => {
  const commands = await fetchCommandsFromBackend();
  
  // Filter available commands based on visitor status
  const availableCommands = visitorMode
    ? commands.filter(cmd => cmd.name === 'identity')  // Only /identity
    : commands;  // All commands
  
  commandStore.setState({ availableCommands });
};
```

---

## Integration Points

### Cross-Service Data Flow

**Scenario: Registered Member Sends Message**

```
1. Frontend: ChatInput → websocketManager.sendMessage("Hello")
   └─ Payload: { type: "user_message", payload: { content: "Hello", public_key: "0x..." } }

2. Backend: WebsocketInterface.websocket_endpoint()
   ├─ Extracts public_key from route parameter
   ├─ Creates Message(owner_key=public_key, role=HUMAN, content="Hello")
   └─ Publishes to RUNS_NEW

3. OrchestratorService.handle_new_run()
   ├─ identity_service.get_identity(owner_key) → Returns identity doc
   ├─ Gatekeeper check PASSES (identity exists)
   └─ Publishes CONTEXT_BUILD_REQUEST(owner_key=...)

4. ContextService.handle_build_request()
   ├─ persistence_service.get_history(owner_key)
   │  └─ db_service.get_messages_by_owner_key(owner_key)
   │     └─ MongoDB: db.messages.find({"owner_key": "0x..."})
   └─ Builds context with historical messages

5. LLMService.handle_request()
   └─ Processes with full conversation context

6. PersistenceService (subscribes to RUNS_NEW, LLM_RESULTS, TOOL_RESULTS)
   ├─ Saves human message: Message(owner_key=..., role=HUMAN, ...)
   └─ Saves AI response: Message(owner_key=..., role=AI, ...)
```

**Scenario: Visitor Sends Message**

```
1-2. [Same as above]

3. OrchestratorService.handle_new_run()
   ├─ identity_service.get_identity(owner_key) → Returns None
   ├─ Gatekeeper check FAILS (identity does not exist)
   ├─ Creates guidance Message(role=SYSTEM, content="身份未验证...")
   ├─ Publishes to UI_EVENTS
   └─ STOPS PROCESSING (no CONTEXT_BUILD_REQUEST)

4. WebsocketInterface.handle_ui_event()
   └─ Sends guidance message to frontend WebSocket

5. Frontend: ChatStore.handleTextChunk() or similar
   └─ Displays system message: "身份未验证。请通过 /identity..."
```

---

## Environment-Specific Behavior

### Development Environment

**IdentityService:**
- Uses `localStorage` for persistent key storage
- Auto-generates key pair if none exists
- Public key format: Ethereum address (40 hex chars)

**MongoDB:**
- Local instance at `mongodb://localhost:27017`
- Database name: `nexus_dev`
- Collections: `identities`, `messages`, `system_configurations`

**WebSocket:**
- Connects to `ws://localhost:8000/api/v1/ws/{public_key}`
- No TLS encryption (plain WebSocket)

### Production Environment (Render)

**IdentityService:**
- Same `localStorage` mechanism
- Key persistence across browser sessions
- No server-side key generation

**MongoDB:**
- MongoDB Atlas cluster
- Connection string from `MONGO_URI` env var
- Database name configured in `config.yml`
- Automatic index creation on first connection

**WebSocket:**
- Connects via `wss://nexus-api.onrender.com/api/v1/ws/{public_key}`
- TLS-encrypted WebSocket
- Connection validated against registered identities

---

## Common Issues and Troubleshooting

### Issue 1: "身份未验证" Message Loop

**Symptom:** User keeps seeing "身份未验证" even after running `/identity`

**Diagnosis:**
```bash
# Check MongoDB identities collection
db.identities.find({"public_key": "0x..."})  # Should return 1 document

# Check backend logs for identity service
grep "Identity found for public_key" /tmp/nexus_run.log
```

**Resolution:**
1. Verify signature was valid: Check `CommandService` logs for "Signature verified successfully"
2. Confirm identity was created: Query MongoDB `identities` collection
3. Check frontend: Ensure `localStorage` key hasn't changed

**Prevention:**
- Add `created_at` timestamp logging in `IdentityService.create_identity`
- Implement health check endpoint: `GET /api/v1/identity/{public_key}`

---

### Issue 2: Visitor Can Send Messages (Gatekeeper Bypass)

**Symptom:** Unregistered user's messages are being processed by LLM

**Diagnosis:**
```python
# Check OrchestratorService initialization
# In nexus/main.py, verify:
orchestrator_service = OrchestratorService(
    bus=nexus_bus,
    identity_service=identity_service  # ✅ Must be present
)
```

**Resolution:**
1. Ensure `identity_service` is injected into `OrchestratorService`
2. Verify `handle_new_run()` gatekeeper check is not commented out
3. Check logs: Should see "Unverified user attempted access" for visitors

---

### Issue 3: `/identity` Command Fails with "Authentication failed"

**Symptom:** Frontend sends signed command but backend rejects it

**Diagnosis:**
```typescript
// Frontend: Check signature generation
const signature = await IdentityService.signCommand('/identity');
console.log('Signature:', signature);  // Should be 132 hex chars (0x + 130)

// Backend: Check signature verification logs
grep "Signature verification" /var/log/nexus.log
```

**Common Causes:**
1. **Message mismatch**: Frontend signs `"/identity"` but backend receives `"identity"` (slash missing)
2. **Key format**: Public key is checksummed vs. lowercase
3. **Signature format**: Ethereum `v` value (27/28 vs. 0/1)

**Resolution:**
```python
# nexus/services/command.py - Signature verification
# Ensure v-value normalization:
if len(sig_bytes) == 65:
    v = sig_bytes[64]
    if v >= 27:  # Ethereum format
        sig_bytes = sig_bytes[:64] + bytes([v - 27])  # ✅ Normalize
```

---

### Issue 4: Messages Not Persisting for Member

**Symptom:** User is verified but conversation history is empty

**Diagnosis:**
```python
# Check PersistenceService
# In nexus/services/persistence.py:
async def handle_new_run(self, message: Message):
    if self.identity_service:
        identity = await self.identity_service.get_identity(message.owner_key)
        if identity is None:
            return  # ✅ Should skip persistence for visitors
    
    # For members, this should execute:
    human_message = Message(
        owner_key=message.owner_key,  # ✅ Must match identity
        ...
    )
    await self.db_service.insert_message_async(human_message)
```

**Resolution:**
1. Verify `PersistenceService` receives `identity_service` injection
2. Check `owner_key` consistency across message creation
3. Query MongoDB: `db.messages.find({"owner_key": "0x..."})`

---

### Issue 5: Frontend `visitorMode` Not Updating

**Symptom:** UI doesn't show visitor restrictions even when backend sends `connection_state`

**Diagnosis:**
```typescript
// Check WebSocket event subscription in useAura.ts
useEffect(() => {
  websocketManager.on('connection_state', onConnectionState);  // ✅ Must be present
  
  return () => {
    websocketManager.off('connection_state', onConnectionState);
  };
}, [onConnectionState]);  // ✅ Must include dependency
```

**Resolution:**
1. Verify `connection_state` is in `validEventTypes` in `protocol.ts`
2. Check `ChatStore.handleConnectionState` is called
3. Inspect Redux DevTools or Zustand state: `visitorMode` should toggle

---

## Migration Guide (session_id → owner_key)

### For Existing Data (NOT PERFORMED)

**This migration was a breaking change. No data migration was performed.** All existing `messages` with `session_id` are **orphaned** and not accessible in the new system.

**If migration were needed (for reference):**
```javascript
// MongoDB migration script (NOT EXECUTED)
db.messages.updateMany(
  {},
  [
    {
      $set: {
        owner_key: "$session_id",  // Copy session_id to owner_key
        migrated: true
      }
    },
    {
      $unset: "session_id"  // Remove old field
    }
  ]
);

// Create identities from unique owner_keys
db.messages.aggregate([
  { $group: { _id: "$owner_key" } },
  { $project: { public_key: "$_id", created_at: new Date(), metadata: {} } },
  { $merge: { into: "identities", on: "public_key", whenMatched: "keepExisting", whenNotMatched: "insert" } }
]);
```

---

## Testing Strategy

### Unit Tests

**IdentityService** (`tests/nexus/unit/services/test_identity_service.py`):
```python
async def test_get_identity_not_found():
    # Verify None return for unregistered key
    identity = await identity_service.get_identity("0xNONEXISTENT")
    assert identity is None

async def test_create_identity_success():
    # Verify identity creation
    success = await identity_service.create_identity("0xNEW")
    assert success is True
    
async def test_get_or_create_idempotent():
    # First call creates
    identity1 = await identity_service.get_or_create_identity("0xTEST")
    assert identity1['_just_created'] is True
    
    # Second call retrieves
    identity2 = await identity_service.get_or_create_identity("0xTEST")
    assert '_just_created' not in identity2
```

**MongoProvider** (`tests/nexus/unit/services/database/providers/test_mongo_provider.py`):
```python
def test_get_messages_by_owner_key():
    messages = provider.get_messages_by_owner_key("0xTEST", limit=10)
    
    # Verify query uses owner_key
    mock_collection.find.assert_called_once_with({"owner_key": "0xTEST"})
    
def test_create_identity_with_unique_constraint():
    # First insert succeeds
    provider.create_identity({"public_key": "0xUNIQUE"})
    
    # Duplicate insert fails (unique index)
    with pytest.raises(DuplicateKeyError):
        provider.create_identity({"public_key": "0xUNIQUE"})
```

### Integration Tests

**Gatekeeper Flow** (`tests/nexus/integration/services/test_orchestrator_service.py`):
```python
async def test_handle_new_run_for_unverified_user():
    # Mock identity_service to return None (visitor)
    mock_identity_service.get_identity = AsyncMock(return_value=None)
    
    # Simulate new run from visitor
    message = Message(owner_key="0xVISITOR", role=Role.HUMAN, content="Hello")
    await orchestrator.handle_new_run(message)
    
    # Verify guidance published, NOT context request
    published_events = mock_bus.publish.call_args_list
    assert any(call[0][0] == Topics.UI_EVENTS for call in published_events)
    assert not any(call[0][0] == Topics.CONTEXT_BUILD_REQUEST for call in published_events)
```

**Command Execution** (`tests/nexus/integration/services/test_command_service.py`):
```python
async def test_signed_command_verification_success():
    # Generate valid signature
    private_key = keys.PrivateKey(b'\x01' * 32)
    public_key_hex = private_key.public_key.to_address()
    signature = private_key.sign_msg_hash(keccak("/identity".encode()))
    
    # Send signed command
    input_message = Message(
        owner_key=public_key_hex,
        role=Role.COMMAND,
        content={
            "command": "/identity",
            "auth": {"publicKey": public_key_hex, "signature": signature.to_hex()}
        }
    )
    
    await command_service.handle_command(input_message)
    
    # Verify success
    result = mock_bus.publish.call_args[0][1]
    assert result.content["status"] == "success"
    assert result.content["data"]["public_key"] == public_key_hex
```

---

## Performance Considerations

### Database Indexing

**Critical Indexes:**
```python
# identities collection
db.identities.createIndex({"public_key": 1}, {unique: true})

# messages collection
db.messages.createIndex({"owner_key": 1, "timestamp": -1})
db.messages.createIndex({"run_id": 1})
```

**Query Performance:**
- `find_identity_by_public_key`: O(1) with unique index
- `get_messages_by_owner_key`: O(log n) with compound index on `(owner_key, timestamp)`

### Caching Strategy (Future Enhancement)

```python
# Example: In-memory cache for frequently accessed identities
class IdentityService:
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self._identity_cache: Dict[str, Optional[Dict]] = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def get_identity(self, public_key: str) -> Optional[Dict[str, Any]]:
        # Check cache first
        if public_key in self._identity_cache:
            cached = self._identity_cache[public_key]
            if not self._is_cache_expired(cached):
                return cached['data']
        
        # Cache miss - query database
        identity = await asyncio.to_thread(
            self.db_service.provider.find_identity_by_public_key,
            public_key
        )
        
        # Update cache
        self._identity_cache[public_key] = {
            'data': identity,
            'timestamp': datetime.now(timezone.utc)
        }
        
        return identity
```

---

## Security Considerations

### Public Key Validation

**Always validate Ethereum address format:**
```python
import re

def is_valid_ethereum_address(address: str) -> bool:
    """Validate Ethereum address format."""
    if not address.startswith('0x'):
        return False
    if len(address) != 42:  # 0x + 40 hex chars
        return False
    if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return False
    return True
```

### Signature Verification Security

**Critical checks in `CommandService._verify_signature()`:**
1. **Replay attack prevention**: Consider adding nonce/timestamp to signed message
2. **Public key binding**: Ensure `auth.publicKey` matches recovered address
3. **Message integrity**: Hash exactly what frontend signed (including whitespace)

**Future Enhancement:**
```python
# Add timestamp to prevent replay attacks
command_with_timestamp = f"{command}:{int(time.time())}"
message_hash = keccak(command_with_timestamp.encode('utf-8'))

# Verify timestamp is recent (within 5 minutes)
_, timestamp_str = command_str.split(':')
timestamp = int(timestamp_str)
if abs(time.time() - timestamp) > 300:
    return {"status": "error", "message": "Command signature expired"}
```

### Data Isolation Enforcement

**Prevent cross-user data leakage:**
```python
# ALWAYS query with owner_key filter
messages = db.messages.find({"owner_key": requesting_user_key})

# NEVER query without owner_key filter in user-facing APIs
messages = db.messages.find({})  # ❌ DANGEROUS: Exposes all user data
```

---

## Future Enhancements

### 1. Multi-Device Identity Sync

**Challenge:** User has same public key on desktop + mobile, but different private keys in localStorage

**Proposed Solution:**
- Implement "identity linking" where user can authorize additional devices
- Use QR code + signature verification for secure device pairing

### 2. Identity Metadata & Personalization

**Expand `identities.metadata` schema:**
```javascript
{
  "public_key": "0x...",
  "metadata": {
    "display_name": "Alice",
    "avatar_url": "https://...",
    "preferences": {
      "language": "zh-CN",
      "theme": "dark",
      "llm_model": "gemini-2.5-flash"
    },
    "personalization": {
      "system_prompt_override": "You are a helpful coding assistant...",
      "tone": "professional",
      "verbosity": "concise"
    }
  }
}
```

### 3. Identity Recovery Mechanism

**Problem:** User loses private key → loses access to all data

**Solutions:**
- **Social recovery**: Trusted contacts can help recover identity
- **Seed phrase backup**: Export 12-word mnemonic for key restoration
- **Email backup**: Encrypted key backup sent to verified email

### 4. Role-Based Access Control (RBAC)

```javascript
{
  "public_key": "0x...",
  "metadata": {
    "roles": ["member", "premium", "admin"],
    "permissions": ["read_history", "write_messages", "export_data", "delete_account"]
  }
}
```

---

## References

### Related Documentation
- **Architecture**: `../02_NEXUS_ARCHITECTURE.md` - Overall system design
- **Command System**: `./command_system.md` - Detailed command execution flow
- **Environment Setup**: `./environment_configuration.md` - Deployment configuration

### Code References
- **Backend**:
  - `nexus/services/identity.py` - Identity service implementation
  - `nexus/services/orchestrator.py` - Gatekeeper logic
  - `nexus/services/database/providers/mongo.py` - MongoDB operations
  - `nexus/commands/definition/identity.py` - `/identity` command
- **Frontend**:
  - `aura/src/services/identity/identity.ts` - Key generation & signing
  - `aura/src/services/websocket/manager.ts` - WebSocket with public_key
  - `aura/src/features/chat/store/chatStore.ts` - Visitor mode state

### External Resources
- [Ethereum Address Format](https://ethereum.org/en/developers/docs/accounts/)
- [ECDSA Signature Verification](https://cryptobook.nakov.com/digital-signatures/ecdsa-sign-verify-messages)
- [MongoDB Unique Indexes](https://www.mongodb.com/docs/manual/core/index-unique/)

---

**Document Version:** 1.0  
**Last Updated:** 2025-10-10  
**Status:** ✅ Complete - Reflects current `DATA-SOVEREIGNTY-1.0` implementation  
**Maintainer:** NEXUS Development Team

