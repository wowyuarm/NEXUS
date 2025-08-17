### **任务委托单：AURA-NEXUS-LIVESTREAM**

**致：** 工程师AI

**发令者：** “枢”，AURA项目首席AI架构师

**主题：** 实现NEXUS到AURA的完整、实时的状态广播系统

**任务ID：** `LIVESTREAM`

---

**指令头 (Preamble):**
你是一名资深的全栈架构师。你的任务是打通NEXUS后端的状态广播与AURA前端的状态渲染之间的壁垒，实现一个能够实时、可视化地展现AI思考与行动过程的“直播”系统。

---

#### **核心指令**

**1. 后端增强: `nexus/services/orchestrator.py`**

*   **目标**: 让`Orchestrator`成为一个合格的“现场解说员”。
*   **行动**:
    *   **在`handle_new_run`的开头**: 增加发布`run_started` UI事件的逻辑。
    *   **在`handle_llm_result`中**:
        *   如果检测到`tool_calls`，在发布`TOOLS_REQUESTS`**之前**，循环遍历`tool_calls`并为每一个发布`tool_call_started` UI事件。
    *   **在`handle_tool_result`的开头**: 增加发布`tool_call_finished` UI事件的逻辑。
    *   **在`Run`完成时** (无论是`COMPLETED`, `FAILED`, 还是 `TIMED_OUT`): 在清理`active_runs`**之前**，发布一个`run_finished` UI事件，其中`payload`应包含最终的状态。

**2. 前端增强: `aura/src/features/chat/store/auraStore.ts`**

*   **目标**: 让AURA的“心智”能够理解并响应所有新的状态广播。
*   **行动**:
    *   在`AuraActions`和`useAuraStore`的实现中，增加新的`handleRunStarted`和`handleRunFinished` action。
    *   **`handleRunStarted`**: 应该将`currentRun.status`设置为`'thinking'`，并**创建一个新的、空的AI消息占位符**到`messages`数组中。这个占位符是后续所有`text_chunk`和`tool_call`的“容器”。
    *   **`handleRunFinished`**: 应该将`currentRun.status`重置为`'idle'`，并将最后一条AI消息的`isStreaming`标记设为`false`。
    *   **修改`handleToolCallFinished`**: 它不应该再将`status`改回`'thinking'`，因为`Orchestrator`可能会继续等待其他工具，或者直接进入`streaming_text`状态。它只负责更新`ToolCallCard`的状态。
    *   **修改`handleTextChunk`**: 确保它能正确地找到那个由`handleRunStarted`创建的AI消息占位符，并将`chunk`追加进去。

**3. 前端增强: `aura/src/features/chat/hooks/useAura.ts`**

*   **目标**: 将新的心智活动连接到神经系统。
*   **行动**: 在`useEffect`中，增加对`websocketManager`广播的`run_started`和`run_finished`事件的订阅，并分别调用`auraStore`中对应的`handle...` action。

---
**交付要求：**
你必须：
1.  提供`nexus/services/orchestrator.py`增强后的完整代码。
2.  提供`aura/src/features/chat/store/auraStore.ts`增强后的完整代码。
3.  提供`aura/src/features/chat/hooks/useAura.ts`增强后的完整代码。

完成这次改造后，AURA将能够**实时、精确、可视化地**展现NEXUS引擎内部的每一步思考和行动，实现我们最初设想的、富有生命感的交互体验。

**任务开始。**