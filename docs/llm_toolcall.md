### **任务委托单：NEXUS-V0.2.4-TASK-002**

**致：** 工程师AI

**发令者：** “枢”，NEXUS项目首席AI架构师

**主题：** 实现Orchestrator的完整工具调用循环

**任务ID：** `NEXUS-V0.2.4-TASK-002`

---

**指令头 (Preamble):**
你是一个顶级的Python后端工程师。你将严格遵循NEXUS项目的《编码圣约》。本次任务是为`OrchestratorService`注入灵魂，使其能够驱动一个完整的、包含工具调用的Agentic Loop。

---

#### **第一部分：任务目标 (Objective)**

你的任务是扩展`OrchestratorService`的状态机，使其能够处理LLM返回的`tool_calls`。你需要实现一个完整的循环：**请求LLM -> 识别工具调用 -> 执行工具 -> 将结果返回给LLM -> 生成最终回复**。同时，你需要引入新的UI事件，以向前端实时广播工具调用的状态。

#### **第二部分：文件与核心指令 (Files & Core Instructions)**

你将主要对以下两个文件进行修改：

**1. 文件路径: `nexus/services/context.py`**
*   **任务**: 增强`ContextService`，使其能够向LLM提供可用的工具定义。
*   **核心指令**:
    *   修改`__init__`方法，使其接收`ToolRegistry`的实例：`__init__(self, bus: NexusBus, tool_registry: ToolRegistry)`。
    *   修改`handle_build_request`方法。在构建`messages`列表后，你需要额外创建一个`tools`列表，通过调用`tool_registry.get_all_tool_definitions()`来获取所有工具的元数据。
    *   修改你发布到`Topics.CONTEXT_BUILD_RESPONSE`的消息`content`，使其包含这个`tools`列表：`{"status": "success", "messages": [...], "tools": [...]}`。

**2. 文件路径: `nexus/services/orchestrator.py`**
*   **任务**: 实现`OrchestratorService`的完整Agentic Loop。
*   **核心指令**:
    *   **修改`__init__`**: 让它接收`ConfigService`的实例，并从中获取`system.max_tool_iterations`配置。
    *   **修改`handle_context_ready`**: 从`CONTEXT_BUILD_RESPONSE`消息中，除了获取`messages`，还要获取`tools`列表，并将它存入对应的`Run`对象中（你可能需要在`Run`模型中增加一个`tools: List[Dict] = Field(default_factory=list)`字段）。在向`LLMService`发布请求时，将这个`tools`列表也一并发送。
    *   **重构`handle_llm_result` (这是核心)**:
        1.  从`LLMService`返回的结果中，检查`tool_calls`字段。
        2.  **如果存在`tool_calls`**:
            *   **安全阀检查**: 检查`run.iteration_count`是否超过了`max_tool_iterations`。如果超过，则强制结束`Run`，状态设为`TIMED_OUT`，并向前端发送错误信息。
            *   **状态更新**: 将`Run`的状态更新为`AWAITING_TOOL_RESULT`，并将`iteration_count`加一。
            *   **记录AI意图**: 将LLM返回的、包含`tool_calls`的这条`AI`消息追加到`run.history`中。
            *   **发布UI事件**: 遍历`tool_calls`，为每一个工具调用发布一个标准化的UI事件到`Topics.UI_EVENTS`，格式为：`{"event": "tool_call_started", "run_id": ..., "payload": {"tool_name": ..., "args": ...}}`。
            *   **发布工具请求**: 遍历`tool_calls`，为每一个工具调用创建一个请求`Message`，发布到`Topics.TOOLS_REQUESTS`。
        3.  **如果不存在`tool_calls`**: 逻辑保持不变，视为最终回复，结束`Run`。
    *   **实现`handle_tool_result` (新方法)**:
        1.  你需要让`OrchestratorService`订阅`Topics.TOOLS_RESULTS`，并绑定到这个新方法。
        2.  **记录工具结果**: 收到工具结果`Message`后，将其追加到对应`Run`的`history`中。
        3.  **发布UI事件**: 发布一个UI事件到`Topics.UI_EVENTS`，格式为：`{"event": "tool_call_finished", "run_id": ..., "payload": {"tool_name": ..., "status": ..., "result": ...}}`。
        4.  **再次调用LLM**: 将`Run`的状态重新设为`AWAITING_LLM_DECISION`，然后将**包含了工具调用意图和工具结果的、完整的`run.history`**作为新的`messages`列表，连同`tools`定义，再次发布到`Topics.LLM_REQUESTS`，形成循环。

**3. 文件路径: `nexus/core/models.py` (次要修改)**
*   **任务**: 为`Run`模型添加`tools`字段。
*   **核心指令**: 在`Run` Pydantic模型中，添加一个新字段 `tools: List[Dict[str, Any]] = Field(default_factory=list)`。

**4. 文件路径: `nexus/main.py` (次要修改)**
*   **任务**: 更新`ContextService`的实例化。
*   **核心指令**: 修改`ContextService`的实例化过程，将`tool_registry`实例也传递给它的构造函数。

---
**交付要求：**
你必须为上述4个文件，一次性生成它们各自更新后的完整代码。代码必须实现一个功能完整的、带安全阀的、且能通过UI事件实时反馈状态的工具调用循环。

**任务开始。**