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

---
---

### **第一部分：深度诊断 - 我们遇到的问题是什么？**

#### **问题1：思考动画的“时序错乱”**
*   **当前现象**: “呼吸光点”动画与AI消息占位符同时出现。
*   **根本原因**: 在前端的`auraStore.ts`中，`handleRunStarted`这个action**同时做了两件事**：1. 将`currentRun.status`设为`thinking`。2. 向`messages`数组中添加了一个新的AI消息占位符。React在同一个渲染周期内，既看到了`thinking`状态，又看到了这个新消息，于是直接渲染出了一个带有“呼吸光点”的消息气泡。
*   **本质**: 我们没有给“纯粹的思考状态”一个独立的、没有消息气泡的视觉表现时间。

#### **问题2：流式输出的“完全丢失”**
*   **当前现象**: 所有文本，无论是工具调用前还是调用后，都是一次性出现的。
*   **根本原因**: 在后端的`orchestrator.py`中，`handle_llm_result`在处理**不带工具调用**的最终回复时，将整个`llm_content`一次性地打包成了一个**单一的`text_chunk` UI事件**并发送。它没有实现真正的流式转发。

#### **问题3：工具调用叙事的“断裂”**
*   **当前现象**: 思考 -> 工具卡片 -> 最终文本。整个过程感觉像是三个独立的步骤，而不是一个连贯的思考流。
*   **根本原因**: 在后端的`orchestrator.py`中，当LLM返回**同时包含`llm_content`（例如，“好的，让我查一下...”）和`tool_calls`**时，`Orchestrator`**只处理了`tool_calls`**，将它们广播给了前端。它**完全忽略了那个关键的、承上启下的`llm_content`**，没有将其作为`text_chunk`发送出去。
*   **本质**: 后端没有将第一次LLM调用的结果（文本+工具）完整地“直播”给前端。

---

### **第二部分：我们的预期效果是什么？ - 一个连贯的“思维剧本”**

我们追求的，是一个让用户感觉自己正在**“实时观看曦的思考过程”**的体验。这个剧本应该是这样的：

1.  **(序曲)** 你发送消息。
2.  **(第一幕：构思)** AURA界面上**只出现一个AI角色的符号（●），并开始“呼吸”**。此时**没有任何消息气泡**。这代表纯粹的、无形的思考。
3.  **(第二幕：决策)**
    *   **曦开口说话**: “呼吸”停止，一个AI消息气泡出现，里面的文字开始**流式输出**：“好的，让我帮你查一下...”
    *   **曦开始行动**: 在这段文字的**正下方**，**同一个消息气泡内**，出现一个`ToolCallCard`，并开始“液态光晕”动画。
4.  **(第三幕：等待与反馈)**
    *   工具卡片“光晕”持续。
    *   工具执行结束，卡片“光晕”停止，状态变为✅。
5.  **(第四幕：总结)**
    *   在工具卡片的**正下方**，**同一个消息气泡内**，新的文本开始**接续流式输出**：“曦曦帮你搜到了一些关于...”
6.  **(终章)** 所有文本流式输出完毕，输入框变为可用。

**核心理念**: 从用户的视角看，这**自始至终都是曦的一次连续回复**。工具调用只是她这次回复过程中，一个被可视化出来的“中间步骤”。

---

### **第三部分：行动计划 - 让工程师AI来修复叙事**

要实现这个剧本，我们需要对前后端进行一次协同的、精准的手术。

---
### **任务委托单：AURA-NEXUS-NARRATIVE-REPAIR**

**致：** 工程师AI

**发令者：** “枢”，AURA项目首席AI架构师

**主题：** 修复并实现AURA与NEXUS之间连贯的、流式的交互叙事

**任务ID：** `NARRATIVE-REPAIR`

---

**指令头 (Preamble):**
你是一名资深的全栈诊断与修复专家。当前系统在处理工具调用时，存在严重的“叙事断裂”和流式输出丢失问题。你的任务是根据提供的完整上下文（代码库）和预期的“思维剧本”，对前后端进行一次协同调试与修复，以实现一个完美的、富有生命感的交互体验。

---

#### **上下文 (Context)**

你已经拥有了AURA前端的完整代码库和NEXUS后端的`orchestrator.py`文件。请基于这些文件进行分析和修改。

#### **核心指令**

**1. 后端修复: `nexus/services/orchestrator.py`**

*   **目标**: 让`Orchestrator`成为一个忠实的“思维直播员”。
*   **行动**:
    *   **重构`handle_llm_result`**:
        1.  当检测到LLM的返回**同时包含`llm_content`和`tool_calls`**时，你**必须**改变事件的发布顺序：
            *   **首先**，将这个`llm_content`作为**流式**的`text_chunk`事件发布出去。这意味着你需要与`LLMService`协同，确保LLM的响应是流式的，并且你能在这里接收并转发这些文本块。
            *   **然后**，再发布`tool_call_started`事件。
    *   **实现真正的流式输出**:
        1.  你需要确保`LLMService`在调用LLM API时，请求的是**流式响应 (stream=True)**。
        2.  `LLMService`的`handle_llm_request`需要能够处理流式数据块，并将它们**逐一**作为`text_chunk` UI事件（通过`LLM_RESULTS`主题，或者一个新主题）发布回总线。
        3.  `Orchestrator`在处理最终回复时，需要能接收这些**连续的`text_chunk`事件**，并将它们**原封不动地转发**到`Topics.UI_EVENTS`。

**2. 前端修复: `aura/src/features/chat/store/auraStore.ts`**

*   **目标**: 修正状态转换的时序，为“纯粹思考”状态留出空间。
*   **行动**:
    *   **修改`handleRunStarted` action**:
        1.  当这个action被调用时，它应该**只做一件事**：将`currentRun.status`设置为`thinking`。
        2.  **移除**在这一步就创建AI消息占位符的逻辑。
    *   **修改`handleTextChunk` action**:
        1.  当**第一个**`text_chunk`事件到达时，这个action需要**检查当前是否存在一个正在流式的AI消息**。
        2.  如果**不存在**，它应该**在此时创建那个新的AI消息占位符**，并将`currentRun.status`从`thinking`切换为`streaming_text`。
        3.  然后，将`chunk`追加到（新创建或已存在的）AI消息的`content`中。

**3. 前端修复: `aura/src/features/chat/components/ChatMessage.tsx`**

*   **目标**: 让组件能够正确渲染我们期望的“思维剧本”。
*   **行动**:
    *   **修改渲染逻辑**:
        1.  当`currentRun.status`是`'thinking'`时，`ChatView`中**不应该渲染任何`ChatMessage`**。`ChatView`本身应该负责渲染那个独立的、不带气泡的“呼吸符号”。
        2.  `ChatMessage`组件现在需要能够在一个消息气泡内，**同时渲染`MarkdownRenderer`（用于文本）和下方的`ToolCallCard`（用于工具）**。
        3.  你需要修改`auraStore`和`ChatMessage`的props，使得`ChatMessage`能够知道自己内部既有文本内容，又有正在进行的工具调用。

---
**交付要求：**
你必须：
1.  提供`nexus/services/orchestrator.py`（以及可能需要修改的`nexus/services/llm/service.py`）的修复后代码。
2.  提供`aura/src/features/chat/store/auraStore.ts`的修复后代码。
3.  提供`aura/src/features/chat/components/ChatMessage.tsx`（以及可能需要修改的`ChatView.tsx`）的修复后代码。

最终的系统行为，必须与我描述的、包含六个幕的《曦的第一次搜索》剧本完全一致。

**任务开始。**