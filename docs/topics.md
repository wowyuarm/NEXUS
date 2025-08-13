### **任务委托单：NEXUS-V0.2.3-TASK-001**

**致：** 工程师AI

**发令者：** “枢”，NEXUS项目首席AI架构师

**主题：** 创建NEXUS事件主题常量模块

**任务ID：** `NEXUS-V0.2.3-TASK-001`

---

**指令头 (Preamble):**
你是一个顶级的Python后端工程师。你将严格遵循NEXUS项目的《编码圣约》。你的本次交付必须是生产级别的、完整的、且无需修改即可运行的代码。

---

#### **第一部分：任务目标 (Objective)**

为了提高代码的可维护性并避免硬编码字符串，你需要创建一个统一的事件主题（Topics）常量模块。这个模块将定义所有`NexusBus`上使用的通信频道名称。

#### **第二部分：文件路径 (File Path)**

你将要创建一个**新文件**：
`nexus/core/topics.py`

#### **第三部分：核心指令 (Core Instruction)**

请在 `nexus/core/topics.py` 文件中，创建一个名为 `Topics` 的类。这个类不应该被实例化，它只作为所有主题常量的命名空间。

*   **实现**:
    *   在类内部，为我们即将需要的核心主题定义字符串常量。
    *   使用清晰的、分层的命名方式，例如 `CATEGORY_ACTION_TARGET`。

*   **代码内容**:
    ```python
    # 文件路径: nexus/core/topics.py

    """
    Defines the standardized event topics for the NexusBus.

    This module centralizes all topic strings to prevent typos and provide a single
    source of truth for inter-service communication channels.
    """

    class Topics:
        """
        A namespace for all event topics used in the NexusBus.
        This class should not be instantiated.
        """

        # --- Run Lifecycle Topics ---
        RUNS_NEW = "runs.new"
        """
        Published by an interface when a new user request initiates a run.
        Message content: a Run object.
        """

        # --- Context Building Topics ---
        CONTEXT_BUILD_REQUEST = "context.build.request"
        """
        Published by the Orchestrator to request context for a run.
        Message content: {"session_id": str, "current_input": str}
        """

        CONTEXT_BUILD_RESPONSE = "context.build.response"
        """
        Published by the ContextService when context has been built.
        Message content: {"status": "success"|"error", "messages": List[Dict]}
        """

        # --- LLM Interaction Topics ---
        LLM_REQUESTS = "llm.requests"
        """
        Published by the Orchestrator to request an LLM completion.
        Message content: {"messages": List[Dict]}
        """
        
        LLM_RESULTS = "llm.results"
        """
        Published by the LLMService with the result from the LLM.
        Message content: {"content": str|None, "tool_calls": List|None}
        """

        # --- Tool Execution Topics ---
        TOOLS_REQUESTS = "tools.requests"
        """
        Published by the Orchestrator to request a tool execution.
        Message content: {"name": str, "args": Dict}
        """

        TOOLS_RESULTS = "tools.results"
        """
        Published by the ToolExecutorService with the result of a tool execution.
        Message content: {"result": Any, "status": "success"|"error", "tool_name": str}
        """

        # --- UI & Frontend Topics ---
        UI_EVENTS = "ui.events"
        """
        Published by various services (mainly Orchestrator) to send real-time
        updates to the frontend.
        Message content: {"event": str, "run_id": str, "payload": Dict}
        """
    ```

#### **第四部分：必需的导入 (Required Imports)**

你的代码文件顶部不需要复杂的导入，但为了未来的一致性，请包含 `typing`。

```python
from typing import List, Dict
```
*(虽然在当前代码中未使用，但这是为未来扩展和保持良好实践而添加的)*

---
**交付要求：**
请严格按照上述要求，一次性生成 `nexus/core/topics.py` 文件的全部内容。确保所有常量名称和文档字符串都清晰准确。

**任务开始。**