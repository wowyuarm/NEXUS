# WS-SSE-001: WebSocket to SSE Migration

**Date:** 2025-12-11
**Status:** 🚧 In Progress

---

## Part 1: Task Brief

### Background

NEXUS 最初选择 WebSocket 是为了支持「AI 主动发消息」的产品愿景。经过深入分析，当前实际使用模式完全是「用户请求 → 服务端流式响应」的单向流，WebSocket 的双向特性并未被利用。同时，WebSocket 带来了额外的部署复杂度（Nginx 升级配置、跨域问题、代理层调试）。迁移到 HTTP + SSE 可以简化架构、降低运维成本，并为未来 CLI/移动端接入提供更友好的接口。

### Objectives

1. 将聊天流式响应从 WebSocket 迁移到 HTTP POST + SSE
2. 将命令执行从 WebSocket 迁移到同步 HTTP REST
3. 完全移除 WebSocket 代码，简化技术栈
4. 保持所有现有功能正常工作

### Deliverables

**Backend (Nexus):**
- [ ] `nexus/interfaces/sse.py` - 新 SSE 接口实现
- [ ] `nexus/interfaces/rest.py` - 新增 `/chat` 和 `/commands/execute` 端点
- [ ] `nexus/main.py` - 移除 WebSocket 初始化，添加 SSE 路由
- [ ] 删除 `nexus/interfaces/websocket.py`
- [ ] `tests/nexus/unit/interfaces/test_sse.py` - SSE 接口单元测试

**Frontend (Aura):**
- [ ] `aura/src/services/stream/manager.ts` - 新 SSE/HTTP 通信管理器
- [ ] `aura/src/services/stream/protocol.ts` - 协议类型（复用现有事件类型）
- [ ] `aura/src/config/nexus.ts` - 配置更新（移除 wsUrl）
- [ ] `aura/src/features/chat/hooks/useAura.ts` - 切换到 StreamManager
- [ ] `aura/src/features/chat/store/chatStore.ts` - sendMessage 改用 HTTP
- [ ] 删除 `aura/src/services/websocket/` 目录
- [ ] 更新相关测试文件

**Documentation:**
- [ ] `docs/api_reference/01_SSE_PROTOCOL.md` - 新协议文档（替换 WebSocket 文档）
- [ ] 更新 `docs/knowledge_base/technical_references/command_system.md`

### Risk Assessment

- ⚠️ **SSE 认证限制**：原生 `EventSource` API 不支持自定义 Header
  - **缓解**：使用 path parameter `/{public_key}` 传递身份（与现有 WebSocket 一致）；聊天请求用 fetch + ReadableStream 可携带 Authorization header

- ⚠️ **代理层超时**：Nginx/Render 可能超时断开长 SSE 连接
  - **缓解**：配置 `proxy_read_timeout`，SSE 流发送周期性 `:keepalive` 注释行

- ⚠️ **聊天流中断恢复**：网络波动导致 SSE 流断开，部分响应丢失
  - **缓解**：前端在流断开时显示错误提示，用户可重新发送；后端记录完整响应到历史

- ⚠️ **并发请求处理**：用户快速连续发送消息
  - **缓解**：保持现有 `isInputDisabled` 机制，同一时刻只允许一个 active run

### Dependencies

**Code Dependencies:**
- `nexus/core/bus.py` - NexusBus 事件系统（无变化）
- `nexus/core/topics.py` - Topics.UI_EVENTS, Topics.COMMAND_RESULT（无变化）
- `nexus/services/orchestrator.py` - 现有 UI 事件发布逻辑（无变化）
- `nexus/interfaces/rest.py` - 现有 REST 认证逻辑（复用）

**Infrastructure:**
- FastAPI StreamingResponse 支持
- 前端 fetch API + ReadableStream 支持

**External:**
- 无

### References

- `docs/api_reference/01_WEBSOCKET_PROTOCOL.md` - 现有协议定义
- `docs/knowledge_base/technical_references/command_system.md` - 命令系统架构
- `docs/learn/2025-09-11-render-vite-ws-nginx.md` - WebSocket 部署问题复盘
- `docs/learn/2025-09-12-llm-invalid-argument-tool-calls.md` - LLM 消息格式问题
- `nexus/interfaces/websocket.py` - 现有 WebSocket 实现
- `aura/src/services/websocket/manager.ts` - 现有前端 WebSocket 管理器
- `aura/src/features/chat/hooks/useAura.ts` - 现有事件订阅逻辑

### Acceptance Criteria

- [ ] 所有后端测试通过：`pytest tests/nexus/ -v`
- [ ] 所有前端测试通过：`pnpm test:run`
- [ ] 聊天流式响应正常：用户输入 → AI 逐字流式输出
- [ ] 工具调用 UI 更新正常：tool_call_started → tool_call_finished
- [ ] 命令执行正常：`/ping`, `/identity`, `/config`, `/clear`
- [ ] visitor/member 状态判断正常
- [ ] 错误处理和 UI 提示正常
- [ ] 无 WebSocket 相关代码残留
- [ ] 本地开发环境验证通过
- [ ] 文档已更新

---

## Part 2: Implementation Plan

### Architecture Overview

```
【目标架构：HTTP + SSE】

┌─────────────────┐                         ┌─────────────────┐
│     AURA        │                         │     NEXUS       │
│    (Frontend)   │                         │    (Backend)    │
├─────────────────┤                         ├─────────────────┤
│                 │                         │                 │
│  StreamManager  │ ─── POST /chat ──────▶  │  SSE Interface  │
│                 │ ◀── SSE stream ───────  │                 │
│                 │                         │                 │
│                 │ ─── POST /commands ──▶  │  REST Interface │
│                 │ ◀── JSON response ────  │                 │
│                 │                         │                 │
│                 │ ─── GET /stream ─────▶  │  SSE Interface  │
│                 │ ◀── SSE (conn state) ── │  (persistent)   │
└─────────────────┘                         └─────────────────┘
```

**通信模型：**
1. **聊天**：`POST /api/v1/chat` → 返回 SSE 流（text/event-stream）
2. **命令**：`POST /api/v1/commands/execute` → 返回 JSON
3. **连接状态**：`GET /api/v1/stream/{public_key}` → SSE 流（首条 connection_state）

### Phase 1: 后端 SSE 基础设施

**Goal:** 实现 SSE 接口核心逻辑，与现有 WebSocket 并行运行。

**New Files:**
- `nexus/interfaces/sse.py` - SSE 接口实现

**Modified Files:**
- `nexus/main.py` (添加 SSE 路由注册)
- `nexus/interfaces/rest.py` (添加 /chat 和 /commands/execute 端点)

#### Detailed Design

**1. SSE 接口类：`SSEInterface`**

位置：`nexus/interfaces/sse.py`

```python
class SSEInterface:
    """
    Server-Sent Events interface for NEXUS.
    
    Handles:
    - Chat streaming responses via POST /chat
    - Persistent event stream via GET /stream/{public_key}
    - Command execution via POST /commands/execute
    """
    
    def __init__(
        self,
        bus: NexusBus,
        database_service: DatabaseService,
        identity_service: IdentityService
    ):
        self.bus = bus
        self.database_service = database_service
        self.identity_service = identity_service
        # 活跃的 SSE 流，用于 connection_state 等
        self.active_streams: Dict[str, asyncio.Queue] = {}
    
    def subscribe_to_bus(self) -> None:
        """Subscribe to UI_EVENTS and COMMAND_RESULT topics."""
        self.bus.subscribe(Topics.UI_EVENTS, self.handle_ui_event)
        self.bus.subscribe(Topics.COMMAND_RESULT, self.handle_command_result)
    
    async def handle_ui_event(self, message: Message) -> None:
        """Route UI events to the appropriate SSE stream."""
        owner_key = message.owner_key
        if owner_key in self.active_streams:
            await self.active_streams[owner_key].put(message.content)
    
    async def handle_command_result(self, message: Message) -> None:
        """Route command results to the appropriate SSE stream."""
        # 命令结果通过持久流推送（如果有）
        owner_key = message.owner_key
        if owner_key in self.active_streams:
            event = {
                "event": "command_result",
                "run_id": message.run_id,
                "payload": message.content
            }
            await self.active_streams[owner_key].put(event)
```

**2. 聊天端点：`POST /api/v1/chat`**

位置：`nexus/interfaces/rest.py`

```python
class ChatRequest(BaseModel):
    content: str
    client_timestamp_utc: str = ""
    client_timezone_offset: int = 0

@router.post("/chat")
async def chat(
    request: ChatRequest,
    owner_key: str = Depends(verify_bearer_token),
    # 依赖注入
):
    """
    Send a chat message and receive streaming response via SSE.
    
    Returns: StreamingResponse with content-type text/event-stream
    
    Events:
    - run_started: {"owner_key": "...", "user_input": "..."}
    - text_chunk: {"chunk": "...", "is_final": false}
    - tool_call_started: {"tool_name": "...", "args": {...}}
    - tool_call_finished: {"tool_name": "...", "status": "...", "result": "..."}
    - run_finished: {"status": "completed|error"}
    - error: {"message": "..."}
    """
    
    async def event_generator():
        # 1. 创建 Run 并发布到 bus
        run_id = str(uuid.uuid4())
        queue = asyncio.Queue()
        
        # 2. 临时订阅此 run 的事件
        # ... 实现细节
        
        # 3. 生成 SSE 事件
        while True:
            event = await queue.get()
            yield f"event: {event['event']}\n"
            yield f"data: {json.dumps(event)}\n\n"
            
            if event['event'] in ('run_finished', 'error'):
                break
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Nginx unbuffered
        }
    )
```

**3. 命令执行端点：`POST /api/v1/commands/execute`**

位置：`nexus/interfaces/rest.py`

```python
class CommandExecuteRequest(BaseModel):
    command: str  # e.g., "/ping", "/identity"
    args: List[str] = []
    auth: Optional[Dict[str, str]] = None  # For commands requiring signature

@router.post("/commands/execute")
async def execute_command(
    request: CommandExecuteRequest,
    owner_key: str = Depends(verify_bearer_token),
    command_svc=Depends(get_command_service)
) -> Dict[str, Any]:
    """
    Execute a system command synchronously.
    
    Returns:
        {
            "status": "success" | "error",
            "message": "...",
            "data": {...}  # optional
        }
    """
    # 构造命令内容
    command_content = request.command
    if request.auth:
        command_content = {
            "command": request.command,
            "auth": request.auth
        }
    
    # 同步执行命令
    result = await command_svc.execute_command_sync(
        owner_key=owner_key,
        command=command_content
    )
    
    return result
```

**4. 持久流端点：`GET /api/v1/stream/{public_key}`**

位置：`nexus/interfaces/sse.py`（通过 rest.py 暴露）

```python
@router.get("/stream/{public_key}")
async def event_stream(
    public_key: str,
    identity_svc=Depends(get_identity_service)
):
    """
    Persistent SSE stream for connection state and proactive events.
    
    First event is always connection_state with visitor status.
    """
    
    async def stream_generator():
        # 1. 查询 visitor 状态
        identity = await identity_svc.get_identity(public_key)
        is_visitor = identity is None
        
        # 2. 发送 connection_state
        yield f"event: connection_state\n"
        yield f"data: {json.dumps({'visitor': is_visitor})}\n\n"
        
        # 3. 保持连接，定期发送 keepalive
        queue = asyncio.Queue()
        sse_interface.active_streams[public_key] = queue
        
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"event: {event.get('event', 'message')}\n"
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive comment
                    yield ": keepalive\n\n"
        finally:
            del sse_interface.active_streams[public_key]
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

#### Test Cases

**Test File:** `tests/nexus/unit/interfaces/test_sse.py`

- `test_chat_endpoint_returns_sse_stream()` - 验证 /chat 返回正确的 content-type
- `test_chat_endpoint_streams_text_chunks()` - 验证 text_chunk 事件正确流式输出
- `test_chat_endpoint_streams_tool_events()` - 验证工具调用事件
- `test_chat_endpoint_streams_run_finished()` - 验证 run_finished 事件终止流
- `test_chat_endpoint_requires_auth()` - 验证缺少 Bearer token 返回 401
- `test_command_execute_ping()` - 验证 /ping 命令执行
- `test_command_execute_identity()` - 验证 /identity 命令执行
- `test_command_execute_requires_auth()` - 验证命令认证
- `test_stream_endpoint_sends_connection_state()` - 验证首条 connection_state 事件
- `test_stream_endpoint_sends_keepalive()` - 验证 keepalive 注释

---

### Phase 2: 前端 StreamManager 实现

**Goal:** 实现新的 SSE/HTTP 通信管理器，与现有 WebSocket 并行。

**New Files:**
- `aura/src/services/stream/manager.ts` - 新通信管理器
- `aura/src/services/stream/protocol.ts` - 协议类型

**Modified Files:**
- `aura/src/config/nexus.ts` (添加 sseUrl 配置)

#### Detailed Design

**1. StreamManager 类**

位置：`aura/src/services/stream/manager.ts`

```typescript
import { getNexusConfig } from '@/config/nexus';
import { IdentityService } from '../identity/identity';
import type { NexusEvent } from './protocol';

type EventCallback<T = unknown> = (payload: T) => void;

export class StreamManager {
  private eventSource: EventSource | null = null;
  private emitter = new EventEmitter();
  private publicKey: string = '';
  private baseUrl: string;
  private isConnected: boolean = false;
  private abortController: AbortController | null = null;

  constructor() {
    this.baseUrl = getNexusConfig().apiUrl;
  }

  /**
   * Establish persistent SSE connection for connection_state and proactive events.
   */
  async connect(): Promise<void> {
    const identity = await IdentityService.getIdentity();
    this.publicKey = identity.publicKey;
    
    const streamUrl = `${this.baseUrl}/stream/${this.publicKey}`;
    this.eventSource = new EventSource(streamUrl);
    
    this.eventSource.onopen = () => {
      this.isConnected = true;
      this.emitter.emit('connected', { publicKey: this.publicKey });
    };
    
    this.eventSource.onerror = () => {
      this.isConnected = false;
      this.emitter.emit('disconnected', {});
      // Auto-reconnect handled by EventSource
    };
    
    // Listen for specific event types
    this.eventSource.addEventListener('connection_state', (e) => {
      const data = JSON.parse(e.data);
      this.emitter.emit('connection_state', data);
    });
    
    this.eventSource.addEventListener('command_result', (e) => {
      const data = JSON.parse(e.data);
      this.emitter.emit('command_result', data.payload);
    });
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.isConnected = false;
  }

  /**
   * Send chat message and handle streaming response.
   */
  async sendMessage(content: string): Promise<void> {
    if (this.abortController) {
      this.abortController.abort();
    }
    this.abortController = new AbortController();
    
    const response = await fetch(`${this.baseUrl}/chat`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.publicKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        content,
        client_timestamp_utc: new Date().toISOString(),
        client_timezone_offset: new Date().getTimezoneOffset()
      }),
      signal: this.abortController.signal
    });
    
    if (!response.ok) {
      throw new Error(`Chat request failed: ${response.status}`);
    }
    
    // Parse SSE stream
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      let currentEvent = '';
      let currentData = '';
      
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7);
        } else if (line.startsWith('data: ')) {
          currentData = line.slice(6);
        } else if (line === '' && currentEvent && currentData) {
          // Complete event
          const payload = JSON.parse(currentData);
          this.emitter.emit(currentEvent, payload.payload || payload);
          currentEvent = '';
          currentData = '';
        }
      }
    }
  }

  /**
   * Execute command via HTTP POST.
   */
  async executeCommand(
    command: string,
    auth?: { publicKey: string; signature: string }
  ): Promise<{ status: string; message: string; data?: Record<string, unknown> }> {
    const response = await fetch(`${this.baseUrl}/commands/execute`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.publicKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ command, auth })
    });
    
    return response.json();
  }

  // Event subscription API
  on<T = unknown>(event: string, callback: EventCallback<T>): void {
    this.emitter.on(event, callback);
  }

  off<T = unknown>(event: string, callback: EventCallback<T>): void {
    this.emitter.off(event, callback);
  }

  get connected(): boolean {
    return this.isConnected;
  }

  get currentPublicKey(): string {
    return this.publicKey;
  }
}

export const streamManager = new StreamManager();
```

**2. 协议类型**

位置：`aura/src/services/stream/protocol.ts`

```typescript
// 复用现有事件类型定义，从 websocket/protocol.ts 迁移
export type {
  RunStartedPayload,
  ToolCallStartedPayload,
  ToolCallFinishedPayload,
  TextChunkPayload,
  RunFinishedPayload,
  ErrorPayload,
  CommandResultPayload,
  ConnectionStatePayload,
  NexusEvent
} from '../websocket/protocol';
```

#### Test Cases

**Test File:** `aura/src/services/stream/__tests__/manager.test.ts`

- `test_connect_establishes_event_source()` - 验证 EventSource 连接建立
- `test_connect_emits_connected_event()` - 验证 connected 事件
- `test_sendMessage_posts_to_chat_endpoint()` - 验证 POST /chat 请求
- `test_sendMessage_parses_sse_events()` - 验证 SSE 事件解析
- `test_sendMessage_emits_text_chunk()` - 验证 text_chunk 事件分发
- `test_executeCommand_posts_to_commands_endpoint()` - 验证命令执行请求
- `test_disconnect_closes_event_source()` - 验证连接关闭

---

### Phase 3: 前端切换到 StreamManager

**Goal:** 将 useAura 和 chatStore 从 WebSocket 切换到 StreamManager。

**Modified Files:**
- `aura/src/features/chat/hooks/useAura.ts`
- `aura/src/features/chat/store/chatStore.ts`
- `aura/src/features/command/commandExecutor.ts`

#### Detailed Design

**1. useAura.ts 改造**

```typescript
// 替换 import
import { streamManager } from '@/services/stream/manager';

// 替换所有 websocketManager 调用为 streamManager
// 事件订阅逻辑保持不变，只需改变订阅源
useEffect(() => {
  streamManager.on('run_started', onRunStarted);
  streamManager.on('text_chunk', onTextChunk);
  // ... 其他事件
  
  return () => {
    streamManager.off('run_started', onRunStarted);
    // ... cleanup
  };
}, [/* deps */]);
```

**2. chatStore.ts 改造**

```typescript
// sendMessage 改为调用 streamManager
sendMessage: async (content: string) => {
  // ... 添加用户消息到 UI
  
  try {
    await streamManager.sendMessage(content);
  } catch (error) {
    // 错误处理
  }
}
```

**3. commandExecutor.ts 改造**

```typescript
// WebSocket 命令改为 HTTP 调用
async function executeServerCommand(command: Command, options: CommandExecutionOptions) {
  const result = await streamManager.executeCommand(
    options.rawInput,
    options.auth
  );
  return result;
}
```

#### Test Cases

更新现有测试文件，mock streamManager 替代 websocketManager：

- `aura/src/features/chat/store/__tests__/chatStore.test.ts`
- `aura/src/features/chat/hooks/__tests__/useAura.test.ts` (如果存在)

---

### Phase 4: WebSocket 清理 & 文档更新

**Goal:** 完全移除 WebSocket 代码，更新所有文档。

**Deleted Files:**
- `nexus/interfaces/websocket.py`
- `aura/src/services/websocket/` (整个目录)
- `tests/nexus/unit/interfaces/test_websocket.py`

**Modified Files:**
- `nexus/main.py` (移除 WebSocket 初始化)
- `aura/src/config/nexus.ts` (移除 wsUrl)
- `.env.example` (移除 VITE_AURA_WS_URL)
- `docs/api_reference/01_WEBSOCKET_PROTOCOL.md` → 重命名为 `01_SSE_PROTOCOL.md`
- `docs/knowledge_base/technical_references/command_system.md`
- `docs/knowledge_base/technical_references/environment_configuration.md`

#### Documentation Updates

**1. 新建 `docs/api_reference/01_SSE_PROTOCOL.md`**

内容：描述 SSE 事件格式、端点、认证方式。

**2. 更新 `command_system.md`**

- 移除 WebSocket 命令通道描述
- 添加 REST 命令执行说明

---

### Key Files Summary

**New Files (5):**
- `nexus/interfaces/sse.py`
- `aura/src/services/stream/manager.ts`
- `aura/src/services/stream/protocol.ts`
- `tests/nexus/unit/interfaces/test_sse.py`
- `docs/api_reference/01_SSE_PROTOCOL.md`

**Modified Files (10):**
- `nexus/main.py`
- `nexus/interfaces/rest.py`
- `aura/src/config/nexus.ts`
- `aura/src/features/chat/hooks/useAura.ts`
- `aura/src/features/chat/store/chatStore.ts`
- `aura/src/features/command/commandExecutor.ts`
- `aura/src/features/chat/store/__tests__/chatStore.test.ts`
- `.env.example`
- `docs/knowledge_base/technical_references/command_system.md`
- `docs/knowledge_base/technical_references/environment_configuration.md`

**Deleted Files (3):**
- `nexus/interfaces/websocket.py`
- `aura/src/services/websocket/` (directory)
- `tests/nexus/unit/interfaces/test_websocket.py`

---

### Acceptance Criteria

- [ ] 所有后端测试通过：`pytest tests/nexus/ -v`
- [ ] 所有前端测试通过：`pnpm test:run`
- [ ] 聊天流式响应正常：用户输入 → AI 逐字流式输出
- [ ] 工具调用 UI 更新正常：tool_call_started → tool_call_finished
- [ ] 命令执行正常：`/ping`, `/identity`, `/config`, `/clear`
- [ ] visitor/member 状态判断正常
- [ ] 错误处理和 UI 提示正常
- [ ] 无 WebSocket 相关代码残留
- [ ] 本地开发环境验证通过
- [ ] 文档已更新

---

## Part 3: Completion Report

### Implementation Overview

成功实现了 WebSocket 到 SSE 的架构迁移（Phase 1-3），建立了并行运行的双通道架构。WebSocket 代码暂时保留作为 fallback，待 SSE 路径验证稳定后再执行最终清理。

**已交付：**
- 后端 SSE 接口（`nexus/interfaces/sse.py`）
- REST 端点扩展（`POST /chat`, `POST /commands/execute`, `GET /stream/{public_key}`）
- 前端 StreamManager（`aura/src/services/stream/`）
- 前端核心模块切换到 SSE（useAura, chatStore, commandExecutor）
- SSE 协议文档（`docs/api_reference/02_SSE_PROTOCOL.md`）
- 16 个后端 SSE 单元测试
- 307 个后端测试全部通过
- 191 个前端测试全部通过

**暂未执行（待稳定后）：**
- 删除 WebSocket 代码
- 删除前端 websocket 目录
- 移除 wsUrl 配置

---

### Technical Implementation Details

#### 1. 后端 SSE 接口 (`nexus/interfaces/sse.py`)

创建了 `SSEInterface` 类，负责：
- 管理活跃的聊天流（`active_chat_streams: Dict[str, asyncio.Queue]`）
- 管理持久连接流（`active_persistent_streams: Dict[str, asyncio.Queue]`）
- 订阅 `Topics.UI_EVENTS` 和 `Topics.COMMAND_RESULT`，将事件路由到正确的 SSE 流

```python
class SSEInterface:
    def __init__(self, bus, database_service, identity_service):
        self.active_chat_streams: Dict[str, asyncio.Queue] = {}
        self.active_persistent_streams: Dict[str, asyncio.Queue] = {}
    
    async def handle_ui_event(self, message: Message) -> None:
        # 路由到对应 run_id 的聊天流
        if run_id in self.active_chat_streams:
            await self.active_chat_streams[run_id].put(message.content)
```

**关键设计决策：Queue-based Event Routing**

使用 `asyncio.Queue` 而非直接发送，原因：
1. 解耦事件生产者（Orchestrator）和消费者（SSE 流）
2. 支持同一用户多个并发请求的隔离
3. 与现有 NexusBus 订阅模式兼容

#### 2. REST 端点扩展 (`nexus/interfaces/rest.py`)

新增三个端点：

**POST /chat** - 聊天流式响应
```python
@router.post("/chat")
async def chat(request: ChatRequest, owner_key: str = Depends(verify_bearer_token)):
    async def event_generator():
        run_id = await sse_interface.create_run_and_publish(...)
        queue = sse_interface.register_chat_stream(run_id)
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=30.0)
            yield sse_interface.format_sse_event(event_type, event)
            if event_type in ('run_finished', 'error'):
                break
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**POST /commands/execute** - 同步命令执行
- 直接调用 CommandService 执行器
- 返回 JSON 响应而非 SSE 流
- 支持签名验证

**GET /stream/{public_key}** - 持久连接
- 首条事件发送 `connection_state`（visitor 状态）
- 每 30 秒发送 keepalive 注释
- 接收命令结果推送

#### 3. 前端 StreamManager (`aura/src/services/stream/manager.ts`)

实现了与 WebSocketManager 兼容的 API：

```typescript
export class StreamManager {
  async connect(): Promise<void> {
    // 建立 EventSource 持久连接
    this.eventSource = new EventSource(`${this.baseUrl}/stream/${this.publicKey}`);
  }
  
  async sendMessage(input: string): Promise<void> {
    // POST /chat 并解析 SSE 响应
    const response = await fetch(`${this.baseUrl}/chat`, {...});
    await this.parseSSEStream(response);
  }
  
  async executeCommand(command: string, auth?): Promise<CommandExecuteResponse> {
    // POST /commands/execute
    return fetch(`${this.baseUrl}/commands/execute`, {...}).then(r => r.json());
  }
}
```

**SSE 流解析**

使用 `ReadableStream` + 手动解析替代原生 `EventSource`（因为 POST 请求需要携带 Authorization header）：

```typescript
private async parseSSEStream(response: Response): Promise<void> {
  const reader = response.body!.getReader();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: true });
    // 解析 event: 和 data: 行
    // 触发对应事件
  }
}
```

---

### Problems Encountered & Solutions

#### Problem 1: SSE 流与 Bus 订阅的时序问题

**症状：** 第一个 `text_chunk` 事件丢失

**原因分析：**
1. `POST /chat` 创建 Run 并发布到 bus
2. Orchestrator 立即开始处理并发布 `run_started`
3. 此时 SSE 流的 queue 还未注册完成

**解决方案：**
```python
# 先注册 queue，再发布 run
run_id = self._generate_run_id()
queue = sse_interface.register_chat_stream(run_id)  # 先注册
await bus.publish(Topics.RUNS_NEW, envelope_message)  # 后发布
```

#### Problem 2: 前端 sendMessage 的同步/异步语义

**症状：** 原 `websocketManager.sendMessage()` 是 fire-and-forget，新 `streamManager.sendMessage()` 需要等待流结束

**解决方案：**
```typescript
// chatStore.ts
sendMessage: (content: string) => {
  // 立即添加用户消息到 UI
  set((state) => ({ messages: [...state.messages, userMessage] }));
  
  // 异步发送，不阻塞 UI
  streamManager.sendMessage(content).catch((error) => {
    set({ lastError: String(error) });
  });
}
```

---

### Test & Verification

#### 后端测试
```bash
pytest tests/nexus/unit/interfaces/test_sse.py -v
# 16 passed

pytest tests/nexus/ -v
# 307 passed in 3.17s
```

#### 前端测试
```bash
pnpm test:run
# 191 passed in 6.00s

pnpm build
# ✓ built in 4.03s
```

#### 端到端验证（待执行）
- [ ] 本地启动完整系统，验证聊天流
- [ ] 验证工具调用 UI 更新
- [ ] 验证命令执行（/ping, /identity）
- [ ] 验证 visitor/member 状态切换

---

### Reflections & Improvements

**What Went Well:**
- 并行架构策略正确：先建新路径，再切换，最后清理
- 事件结构复用：SSE 和 WebSocket 使用相同的 payload 格式，减少了前端改动
- TDD 流程有效：先写 16 个 SSE 测试用例，确保实现正确

**What Could Be Improved:**
- 持久流 (`GET /stream/{public_key}`) 的重连逻辑需要更完善的测试
- 命令结果目前通过持久流推送，但 `POST /commands/execute` 已经返回结果，存在冗余
  - **Follow-up**: 考虑移除持久流的命令结果推送，简化架构

**Architectural Insights:**
- HTTP + SSE 架构确实比 WebSocket 更简单，尤其在代理配置方面
- `fetch` + `ReadableStream` 比原生 `EventSource` 更灵活，但需要手动处理 SSE 协议解析

---

### Next Steps

1. **E2E 验证**：启动完整系统，手动验证所有功能路径
2. **稳定运行**：观察 1-2 天，确认无问题
3. **最终清理**：删除 WebSocket 代码（`websocket.py`, `aura/src/services/websocket/`）
4. **文档更新**：更新 `command_system.md` 中的通信描述

---

### Related Links

- **Branch**: `feat/websocket-to-sse-migration`
- **New Files**:
  - `nexus/interfaces/sse.py`
  - `aura/src/services/stream/manager.ts`
  - `aura/src/services/stream/protocol.ts`
  - `aura/src/services/stream/index.ts`
  - `tests/nexus/unit/interfaces/test_sse.py`
  - `docs/api_reference/02_SSE_PROTOCOL.md`
- **Modified Files**:
  - `nexus/interfaces/rest.py`
  - `nexus/main.py`
  - `aura/src/features/chat/hooks/useAura.ts`
  - `aura/src/features/chat/store/chatStore.ts`
  - `aura/src/features/command/commandExecutor.ts`
