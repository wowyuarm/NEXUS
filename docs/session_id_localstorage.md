### **任务委托单：AURA-NEXUS-CONNECTION-FIX-V2**

**致：** 工程师AI

**发令者：** “枢”，AURA项目首席AI架构师

**主题：** 修复连接协议并实现持久化会话身份

**任务ID：** `CONNECTION-FIX-V2`

---

**指令头 (Preamble):**
你是一名资深的系统集成工程师。你的任务是修复AURA与NEXUS之间的连接问题，并实现一个基于`localStorage`的持久化`session_id`机制，以确保对话记忆的连续性。

---

#### **核心指令**

**1. 后端修复 (`nexus/interfaces/websocket.py`)**:
*   将WebSocket端点路径从`"/ws/{session_id}"`**修改为**`"/api/v1/ws/{session_id}"`。

**2. 前端修复 (`aura/.env`)**:
*   将`VITE_WS_URL`的值**修改为**`ws://localhost:8000/api/v1/ws`。

**3. 前端修复 (`aura/src/services/websocket/manager.ts`) - 这是核心**
*   **安装UUID库**: 在`aura/`目录下执行`pnpm add uuid && pnpm add -D @types/uuid`。
*   **重构`WebSocketManager`**:
    *   移除构造函数中的`url`参数。
    *   在构造函数中，从`import.meta.env.VITE_WS_URL`读取基础URL。
    *   **新增一个私有方法 `_getSessionId(): string`**:
        *   这个方法负责从`localStorage`中获取`nexus_session_id`。
        *   如果获取不到，就用`uuidv4()`生成一个新的，存入`localStorage`，然后返回。
        *   如果能获取到，就直接返回。
    *   **修改`connect`方法**:
        *   在方法的一开始，就调用`this._getSessionId()`来获取一个持久化的`session_id`。
        *   使用这个`session_id`来拼接完整的WebSocket URL。
        *   将这个`session_id`存储在类的成员变量中（如`this.sessionId`），以便后续使用。

**4. 前端修复 (`aura/src/features/chat/hooks/useAura.ts`)**
*   **修改`sendMessage` action**:
    *   在调用`websocketManager.sendMessage(...)`时，确保传递的消息体中包含`session_id`。`websocketManager`应该提供一个获取当前`sessionId`的方法。

---
**交付要求：**
你必须提供`nexus/interfaces/websocket.py`和`aura/src/services/websocket/manager.ts`重构后的完整代码，以及`aura/.env`的更新内容。代码必须实现一个健壮的、能够跨页面刷新保持不变的`session_id`管理机制。

**任务开始。**