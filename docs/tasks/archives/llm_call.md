### **任务委托单：NEXUS-V0.2.3-TASK-002**

**致：** 工程师AI

**发令者：** “枢”，NEXUS项目首席AI架构师

**主题：** 实现NEXUS的首次端到端对话流

**任务ID：** `NEXUS-V0.2.3-TASK-002`

---

**指令头 (Preamble):**
你是一个顶级的Python后端工程师，专精于构建事件驱动的、高并发的异步系统。你将严格遵循NEXUS项目的《编码圣约》。本次任务涉及多个文件的修改，你需要精准地实现一个简化的端到端对话流，确保事件在各个服务间正确传递并处理。

---

#### **第一部分：任务目标 (Objective)**

你的核心任务是实现一个**不涉及工具调用**的、最简单的对话处理循环。你需要让`WebsocketInterface`能够接收和发送消息，并让`Orchestrator`、`ContextService`和`LLMService`协同处理这次请求，最终返回一个由真实LLM生成的回复。

#### **第二部分：文件与核心指令 (Files & Core Instructions)**

你将按顺序对以下文件进行修改。**注意：你必须导入并使用 `nexus.core.topics.Topics` 中的常量来代替所有硬编码的主题字符串。**

**1. 文件路径: `nexus/services/llm/providers/google.py`**
*   **任务**: 完整实现`GoogleLLMProvider`。
*   **前置代码**:
    ```python
    # nexus/services/llm/providers/base.py
    from abc import ABC, abstractmethod
    from typing import List, Dict, Any
    
    class LLMProvider(ABC):
        @abstractmethod
        def chat_completion(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
            pass
    ```
*   **核心指令**: 创建`GoogleLLMProvider`类，继承`LLMProvider`。实现`__init__`和`chat_completion`方法。`chat_completion`需要使用`openai`库调用Google Gemini API，并返回一个包含`content`和`tool_calls`（在此阶段为`None`）的字典。

**2. 文件路径: `nexus/services/llm/service.py`**
*   **任务**: 完善`LLMService`。
*   **核心指令**:
    *   在`__init__`中，根据（未来会有的）配置，实例化`GoogleLLMProvider`。
    *   在`subscribe_to_bus`中，正式订阅`Topics.LLM_REQUESTS`，并将其绑定到`handle_llm_request`。
    *   完整实现`handle_llm_request`异步方法。它需要：
        *   从接收到的`Message`中解析出`messages`列表和`run_id`。
        *   调用内部`provider`的`chat_completion`方法。
        *   将返回的结果（包含`content`和`tool_calls`）包装在一个新的`Message`中。
        *   将此结果`Message`发布到`Topics.LLM_RESULTS`。

**3. 文件路径: `nexus/services/context.py`**
*   **任务**: 完善`ContextService`的简化逻辑。
*   **核心指令**:
    *   在`subscribe_to_bus`中，订阅`Topics.CONTEXT_BUILD_REQUEST`，绑定到`handle_build_request`。
    *   完整实现`handle_build_request`异步方法。它需要：
        *   从`prompts/xi/persona.md`加载内容作为`system_prompt`。
        *   从请求`Message`中解析出`current_input`和`run_id`。
        *   **（简化逻辑）** 创建一个`messages`列表，包含两条消息：一条`system`角色的消息（内容为`system_prompt`），和一条`user`角色的消息（内容为`current_input`）。
        *   将这个`messages`列表包装在一个新的`Message`中，发布到`Topics.CONTEXT_BUILD_RESPONSE`。

**4. 文件路径: `nexus/services/orchestrator.py`**
*   **任务**: 完善`OrchestratorService`的简化状态机。
*   **核心指令**:
    *   在`__init__`中，添加一个`active_runs: Dict[str, Run] = {}`成员变量。
    *   在`subscribe_to_bus`中，正式订阅`Topics.RUNS_NEW`, `Topics.CONTEXT_BUILD_RESPONSE`, `Topics.LLM_RESULTS`。
    *   实现`handle_new_run`方法：接收`Message`，创建`Run`对象存入`active_runs`，然后发布到`Topics.CONTEXT_BUILD_REQUEST`。
    *   实现`handle_context_ready`方法：接收到上下文后，更新`Run`状态，并发布到`Topics.LLM_REQUESTS`。
    *   实现`handle_llm_result`方法：接收到LLM结果后，**检查是否有`tool_calls`**。
        *   **（简化逻辑）** 如果没有`tool_calls`，则将`Run`状态设为`COMPLETED`，将LLM的`content`包装在一个UI事件`Message`中，发布到`Topics.UI_EVENTS`，然后从`active_runs`中删除该`Run`。

**5. 文件路径: `nexus/interfaces/websocket.py`**
*   **任务**: 完整实现`WebsocketInterface`。
*   **核心指令**:
    *   你需要导入`fastapi`和`websockets`。
    *   在`subscribe_to_bus`中，订阅`Topics.UI_EVENTS`。
    *   完整实现`run_forever`方法。它需要：
        *   创建一个`FastAPI`应用实例。
        *   定义一个`@app.websocket("/ws/{session_id}")`端点。
        *   在这个端点函数中，处理WebSocket连接、接收客户端消息。
        *   当收到消息时，创建`Run`和`Message`对象，发布到`Topics.RUNS_NEW`。
        *   维护一个连接池（如字典），将`session_id`映射到`websocket`连接对象。
    *   实现一个`handle_ui_event`方法（被`subscribe_to_bus`绑定）：当收到`UI_EVENTS`消息时，根据`run_id`（需要设法从`Run`中获取`session_id`）找到对应的`websocket`连接，并将消息内容（payload）发送给前端。
    *   在`run_forever`的最后，使用`uvicorn`启动FastAPI应用。

**6. 文件路径: `nexus/main.py`**
*   **任务**: 更新启动器以支持FastAPI。
*   **核心指令**:
    *   修改`main`函数。现在它不需要直接调用`websocket_interface.run_forever()`。
    *   `WebsocketInterface`的`run_forever`方法应该返回FastAPI的`app`对象。
    *   `main`函数应该获取这个`app`对象，并用`uvicorn`来运行它。
    *   确保所有其他服务的`run_forever`（如果它们有的话，比如`NexusBus`）仍然被`asyncio.gather`并发运行。

---
**交付要求：**
你必须为上述6个文件，一次性生成它们各自更新后的完整代码。代码必须能够协同工作，实现一个完整的对话流程。重点在于事件的正确发布、订阅和处理。

**任务开始。**