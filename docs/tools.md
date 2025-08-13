### **任务委托单：NEXUS-V0.2.4-TASK-001**

**致：** 工程师AI

**发令者：** “枢”，NEXUS项目首席AI架构师

**主题：** 构建工具定义、注册与执行模块

**任务ID：** `NEXUS-V0.2.4-TASK-001`

---

**指令头 (Preamble):**
你是一个顶级的Python后端工程师。你将严格遵循NEXUS项目的《编码圣约》。本次任务是构建NEXUS的工具使用能力，你需要实现工具的定义、注册机制，以及能够异步执行这些工具的`ToolExecutorService`。

---

#### **第一部分：任务目标 (Objective)**

你的任务是分三步，构建起NEXUS的工具调用基础：
1.  **定义工具**: 创建一个具体的`web_search`工具。
2.  **注册工具**: 实现一个`ToolRegistry`，使其能在系统启动时自动发现并注册所有已定义的工具。
3.  **执行工具**: 完整实现`ToolExecutorService`，使其能监听工具调用请求，异步地执行工具，并将结果发布回`NexusBus`。

#### **第二部分：文件与核心指令 (Files & Core Instructions)**

你将按顺序对以下文件进行操作：

**1. 文件路径: `nexus/tools/definition/web.py`**
*   **任务**: 定义一个`web_search`工具。
*   **核心指令**:
    *   使用`tavily-python`库来实现网络搜索功能。
    *   定义一个名为`web_search`的**同步函数**。
    *   这个函数接收一个`query: str`参数。
    *   它需要从环境变量`TAVILY_API_KEY`中获取API密钥来初始化`TavilyClient`。
    *   函数应调用`tavily.search(...)`，并返回一个简洁、格式化的搜索结果字符串。
    *   **关键**: 定义一个名为`WEB_SEARCH_TOOL`的字典，用于描述这个工具的元数据（符合OpenAI/Google的工具定义格式），包含`type`, `function.name`, `function.description`, 和`function.parameters`。

**2. 文件路径: `nexus/tools/registry.py`**
*   **任务**: 实现`ToolRegistry`类。
*   **核心指令**:
    *   创建一个`ToolRegistry`类。
    *   它应该有一个`_tools: Dict[str, Dict]`来存储工具的元数据，和一个`_functions: Dict[str, Callable]`来存储工具的函数实现。
    *   实现一个`register(self, tool_definition: Dict, tool_function: Callable)`方法，用于将工具的元数据和函数添加到注册表中。
    *   实现`get_tool_definition(self, name: str)`和`get_tool_function(self, name: str)`方法。
    *   实现`get_all_tool_definitions(self) -> List[Dict]`方法，用于向LLM提供所有可用工具的列表。

**3. 文件路径: `nexus/services/tool_executor.py`**
*   **任务**: 完整实现`ToolExecutorService`。
*   **核心指令**:
    *   修改`__init__`，使其接收`ToolRegistry`的实例：`__init__(self, bus: NexusBus, tool_registry: ToolRegistry)`。
    *   在`subscribe_to_bus`中，正式订阅`Topics.TOOLS_REQUESTS`，并将其绑定到`handle_tool_request`。
    *   完整实现`handle_tool_request`异步方法。它需要：
        1.  从请求`Message`中解析出工具名称`name`和参数`args`。
        2.  使用`tool_registry.get_tool_function(name)`获取工具的函数。
        3.  **关键**: 使用`asyncio.to_thread()`来在一个独立的线程中异步地运行这个**同步的**工具函数，以避免阻塞事件循环。
        4.  使用`try...except`块来捕获工具执行过程中可能出现的任何异常。
        5.  根据执行结果（成功或失败），创建一个包含`result`, `status`, `tool_name`的结果`Message`。
        6.  将这个结果`Message`发布到`Topics.TOOLS_RESULTS`。

**4. 文件路径: `nexus/main.py`**
*   **任务**: 更新引擎启动器，以初始化并注入`ToolRegistry`。
*   **核心指令**:
    *   在`main`函数中，实例化`ToolRegistry`。
    *   **手动注册**`web_search`工具：导入`WEB_SEARCH_TOOL`和`web_search`函数，并调用`tool_registry.register(...)`。
    *   修改`ToolExecutorService`的实例化过程，将`tool_registry`实例传递给它的构造函数。

---
**交付要求：**
你必须为上述4个文件，一次性生成它们各自更新后的完整代码。代码必须能够协同工作，实现一个完整的工具定义、注册和异步执行的流程。

**任务开始。**