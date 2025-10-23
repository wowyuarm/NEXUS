### **任务委托单：NEXUS-V0.2.2-TASK-001**

**致：** 工程师AI

**发令者：** “枢”，NEXUS项目首席AI架构师

**主题：** 构建NEXUS核心服务骨架与引擎启动器

**任务ID：** `NEXUS-V0.2.2-TASK-001`

---

**指令头 (Preamble):**
你是一个顶级的Python后端工程师，专精于构建事件驱动的、高并发的异步系统。你将严格遵循NEXUS项目的《编码圣约》。本次任务涉及多个文件，你必须严格按照文件路径和指令进行操作，确保所有服务骨架都正确建立并连接到事件总线。

---

#### **第一部分：任务目标 (Objective)**

你的任务是创建NEXUS系统中所有核心服务的Python类骨架，并编写`main.py`作为引擎启动器来初始化和运行这些服务。每个服务都需要在初始化时接收`NexusBus`实例，并定义一个`subscribe_to_bus`方法来声明其感兴趣的事件主题。

#### **第二部分：文件与核心指令 (Files & Core Instructions)**

你将按顺序对以下文件进行操作：

**1. 文件路径: `nexus/services/database/service.py`**
*   **任务**: 创建`DatabaseService`类骨架。
*   **代码**:
    ```python
    import logging
    from nexus.core.bus import NexusBus

    logger = logging.getLogger(__name__)

    class DatabaseService:
        def __init__(self, bus: NexusBus):
            self.bus = bus
            logger.info("DatabaseService Initialized")

        def subscribe_to_bus(self):
            # 未来将在这里订阅需要持久化的消息
            logger.info("DatabaseService subscribed to NexusBus")

        async def run_forever(self):
            # 如果有后台任务，在这里运行
            pass
    ```

**2. 文件路径: `nexus/services/llm/service.py`**
*   **任务**: 创建`LLMService`类骨架。
*   **代码**:
    ```python
    import logging
    from nexus.core.bus import NexusBus

    logger = logging.getLogger(__name__)

    class LLMService:
        def __init__(self, bus: NexusBus):
            self.bus = bus
            logger.info("LLMService Initialized")

        def subscribe_to_bus(self):
            # self.bus.subscribe("topics.llm.requests", self.handle_llm_request)
            logger.info("LLMService subscribed to NexusBus")

        async def handle_llm_request(self, message):
            # 未来将在这里处理LLM API调用
            pass
    ```

**3. 文件路径: `nexus/services/tool_executor.py`**
*   **任务**: 创建`ToolExecutorService`类骨架。
*   **代码**:
    ```python
    import logging
    from nexus.core.bus import NexusBus

    logger = logging.getLogger(__name__)

    class ToolExecutorService:
        def __init__(self, bus: NexusBus):
            self.bus = bus
            logger.info("ToolExecutorService Initialized")

        def subscribe_to_bus(self):
            # self.bus.subscribe("topics.tools.requests", self.handle_tool_request)
            logger.info("ToolExecutorService subscribed to NexusBus")
        
        async def handle_tool_request(self, message):
            # 未来将在这里处理工具执行
            pass
    ```

**4. 文件路径: `nexus/services/context.py`**
*   **任务**: 创建`ContextService`类骨架。
*   **代码**:
    ```python
    import logging
    from nexus.core.bus import NexusBus

    logger = logging.getLogger(__name__)

    class ContextService:
        def __init__(self, bus: NexusBus):
            self.bus = bus
            logger.info("ContextService Initialized")

        def subscribe_to_bus(self):
            # self.bus.subscribe("topics.context.build_request", self.handle_build_request)
            logger.info("ContextService subscribed to NexusBus")

        async def handle_build_request(self, message):
            # 未来将在这里构建上下文
            pass
    ```

**5. 文件路径: `nexus/services/orchestrator.py`**
*   **任务**: 创建`OrchestratorService`类骨架。
*   **代码**:
    ```python
    import logging
    from nexus.core.bus import NexusBus

    logger = logging.getLogger(__name__)

    class OrchestratorService:
        def __init__(self, bus: NexusBus):
            self.bus = bus
            logger.info("OrchestratorService Initialized")

        def subscribe_to_bus(self):
            # self.bus.subscribe("topics.runs.new", self.handle_new_run)
            # self.bus.subscribe("topics.context.build_response", self.handle_context_ready)
            # self.bus.subscribe("topics.llm.results", self.handle_llm_result)
            # self.bus.subscribe("topics.tools.results", self.handle_tool_result)
            logger.info("OrchestratorService subscribed to NexusBus")
    ```

**6. 文件路径: `nexus/interfaces/websocket.py`**
*   **任务**: 创建`WebsocketInterface`类骨架。
*   **代码**:
    ```python
    import logging
    from nexus.core.bus import NexusBus

    logger = logging.getLogger(__name__)

    class WebsocketInterface:
        def __init__(self, bus: NexusBus):
            self.bus = bus
            logger.info("WebsocketInterface Initialized")

        def subscribe_to_bus(self):
            # 未来将在这里订阅发往前端的UI事件和消息
            logger.info("WebsocketInterface subscribed to NexusBus")

        async def run_forever(self, host: str, port: int):
            # 未来将在这里启动WebSocket服务器
            pass
    ```

**7. 文件路径: `nexus/main.py` (这是最重要的部分)**
*   **任务**: 编写NEXUS引擎的启动器。
*   **核心逻辑**:
    1.  导入所有服务类和`NexusBus`。
    2.  设置基础的`logging`配置。
    3.  创建一个`main`异步函数。
    4.  在`main`函数中：
        *   实例化`NexusBus`。
        *   实例化所有服务类（`DatabaseService`, `LLMService`, `ToolExecutorService`, `ContextService`, `OrchestratorService`, `WebsocketInterface`），并将`bus`实例传递给它们。
        *   创建一个列表，包含所有实例化的服务。
        *   遍历服务列表，调用每个服务的`subscribe_to_bus()`方法。
        *   创建一个任务列表，包含需要永久运行的服务（`bus.run_forever()`, `websocket_interface.run_forever(...)`等）。
        *   使用`asyncio.gather`并发运行这些任务。
    5.  在`if __name__ == "__main__":`块中，调用`asyncio.run(main())`。

---
**交付要求：**
你必须为上述7个文件，一次性生成它们各自的完整代码。确保所有类名、方法名和导入路径都完全正确。`main.py`的实现需要特别注意，它必须能正确地将整个系统组装并运行起来。

**任务开始。**