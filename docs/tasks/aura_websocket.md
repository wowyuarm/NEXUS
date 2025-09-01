### **任务委托单：AURA-SYNAPSE**

**致：** 前端工程师AI

**发令者：** “枢”，AURA项目首席AI架构师

**主题：** 重建AURA的完整数据流与状态管理架构

**任务ID：** `SYNAPSE`

---

**指令头 (Preamble):**
你将严格遵循《AURA-DESIGN: 交互空间设计宪章 V2.0》。本次任务是一次全面的架构重构，你将为AURA重建其核心的数据流、通信和状态管理系统，使其能够与NEXUS V0.2后端完美同步。

---

#### **第一部分：上下文学习 (Contextual Learning)**

**在编写任何代码之前，你必须首先阅读并完全理解以下NEXUS后端文件的内容，以确保前端协议与后端事件的绝对一致性：**
1.  **`nexus/core/topics.py`**: 理解所有UI事件的主题名称。
2.  **`nexus/services/orchestrator.py`**: 重点分析`handle_llm_result`和`handle_tool_result`方法中，是如何构建并发布`Topics.UI_EVENTS`消息的。你需要精确地掌握每个UI事件的`event`名称（如`run_started`, `tool_call_started`等）及其`payload`的结构。

#### **第二部分：任务目标 (Objective)**

你的任务是创建和重构四个核心文件，构建起AURA全新的“神经系统”：
1.  **定义协议 (`protocol.ts`)**: 创建与后端完全匹配的WebSocket事件协议。
2.  **管理通信 (`manager.ts`)**: 重构WebSocket管理器，使其成为一个纯粹的、与UI无关的事件发射器。
3.  **重塑状态 (`store.ts`)**: 重构Zustand Store，使其能够精确镜像NEXUS后端的`Run`状态。
4.  **连接逻辑 (`hook.ts`)**: 创建一个新的核心Hook，作为通信、状态和UI之间的桥梁。

#### **第三部分：文件与核心指令 (Files & Core Instructions)**

你将按顺序创建以下新文件（我们假设旧文件已被删除）：

**1. 新文件: `src/services/websocket/protocol.ts`**
*   **任务**: 定义AURA与NEXUS V0.2之间的通信契约。
*   **核心指令**:
    *   基于你的“学习”，精确地定义NEXUS V0.2广播的所有UI事件的TypeScript接口。至少应包括：
        *   `RunStartedEvent`
        *   `TextChunkEvent`
        *   `ToolCallStartedEvent`
        *   `ToolCallFinishedEvent`
        *   `RunFinishedEvent` (新增，用于标记`Run`的最终状态)
        *   `ErrorEvent`
    *   为每个事件创建对应的类型守卫函数（如`isRunStartedEvent(...)`）。
    *   创建一个所有可能事件的联合类型`NexusEvent`。
    *   定义客户端发送给后端的`ClientMessage`接口。

**2. 新文件: `src/services/websocket/manager.ts`**
*   **任务**: 创建一个纯粹的通信管理器。
*   **核心指令**:
    *   保留原有的连接、心跳、重连逻辑。
    *   **关键重构**: 移除所有与Zustand Store或UI状态相关的逻辑。
    *   引入一个轻量级的事件发射器库（如`mitt`）或自定义实现一个简单的`EventEmitter`。
    *   在`onmessage`处理器中，当收到并成功解析一个`NexusEvent`后，**只做一件事**：通过事件发射器向外广播该事件。例如：`this.emitter.emit(event.event, event.payload)`。
    *   提供`on(eventName, callback)`和`off(eventName, callback)`方法，供应用的其他部分订阅这些解析后的事件。

**3. 新文件: `src/features/chat/store/auraStore.ts`**
*   **任务**: 创建全新的、能够精确反映后端状态的Zustand Store。
*   **核心指令**:
    *   **定义State接口**:
        ```typescript
        interface AuraState {
          messages: Message[]; // 沿用，但Message类型可能需要更新
          currentRun: {
            runId: string | null;
            status: 'idle' | 'thinking' | 'tool_running' | 'streaming_text';
            activeToolCalls: ToolCall[]; // ToolCall是一个新接口
          };
          // ...其他必要状态
        }
        ```
    *   **定义Actions接口**:
        *   创建与`protocol.ts`中每个事件一一对应的action。例如：
            *   `handleRunStarted(payload: RunStartedPayload)`: 设置`currentRun.status`为`'thinking'`，并创建一个新的AI消息占位符。
            *   `handleToolCallStarted(payload: ToolCallStartedPayload)`: 设置`status`为`'tool_running'`，并将工具信息添加到`activeToolCalls`数组。
            *   `handleToolCallFinished(payload: ToolCallFinishedPayload)`: 更新`activeToolCalls`中对应工具的状态。
            *   `handleTextChunk(payload: TextChunkPayload)`: 设置`status`为`'streaming_text'`，并将`chunk`追加到对应的消息中。
            *   `handleRunFinished(payload: RunFinishedPayload)`: 将`status`重置为`'idle'`。
        *   创建一个`sendMessage(content: string)` action，它将负责调用`websocketManager`发送消息，并更新本地的`messages`列表以立即显示用户输入。

**4. 新文件: `src/features/chat/hooks/useAura.ts`**
*   **任务**: 创建连接通信、状态和UI的“控制器”Hook。
*   **核心指令**:
    *   **连接WebSocket与Store**:
        *   在`useEffect`中，订阅`websocketManager`的所有事件。
        *   当监听到事件时，调用`auraStore`中对应的action。例如：
            ```typescript
            useEffect(() => {
              const onRunStarted = (payload) => useAuraStore.getState().handleRunStarted(payload);
              websocketManager.on('run_started', onRunStarted);
              
              return () => {
                websocketManager.off('run_started', onRunStarted);
              };
            }, []);
            ```
    *   **向UI暴露状态与方法**:
        *   从`auraStore`中`useStore`出UI组件所需的状态（如`messages`, `currentRun.status`）。
        *   向UI组件暴露`sendMessage`方法。

---
**交付要求：**
你必须为上述4个新文件，一次性生成它们各自的完整代码。这些代码必须能够协同工作，形成一个完整、健壮、且严格遵循《AURA-DESIGN宪章》中“单向数据流”和“职责分离”原则的全新架构。

**任务开始。**