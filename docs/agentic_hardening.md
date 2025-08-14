### **任务委托单：NEXUS-SYNCHRONY**

**致：** 工程师AI

**发令者：** “枢”，NEXUS项目首席AI架构师

**主题：** 实现工具调用的同步化与自动化注册

**任务ID：** `SYNCHRONY`

---

**指令头 (Preamble):**
你是一个顶级的Python后端工程师。你将严格遵循NEXUS项目的《编码圣约》。本次任务是对现有Agentic Loop进行一次关键的架构加固，以解决多工具调用的竞态条件，并实现工具的自动化注册，同时完善Prompt的构建流程。

---

#### **第一部分：任务目标 (Objective)**

你的任务是执行以下三项重构与增强：

1.  **多工具调用同步 (Multi-Tool Synchronization)**: 重构`OrchestratorService`，确保在LLM请求多个工具时，系统会等待所有工具执行完毕后，才将全部结果一并返回给LLM进行下一次决策。
2.  **工具自动注册 (Automated Tool Registration)**: 重构`ToolRegistry`和`main.py`，实现工具的自动发现与注册机制，消除在`main.py`中的手动注册代码。
3.  **Prompt构建完善 (Prompt Construction Enhancement)**: 增强`ContextService`，使其在构建System Prompt时，能够加载并拼接`prompts/xi/tools.md`的内容。

#### **第二部分：文件与核心指令 (Files & Core Instructions)**

你将按顺序对以下文件进行修改：

**1. 文件路径: `nexus/services/orchestrator.py`**
*   **任务**: 实现多工具调用的同步等待逻辑。
*   **核心指令**:
    *   **修改`handle_llm_result`**:
        1.  当检测到`tool_calls`时，在`Run`对象的元数据中记录待处理的工具调用数量。例如：`run.metadata['pending_tool_calls'] = len(tool_calls)`。
    *   **修改`handle_tool_result`**:
        1.  每当收到一个工具结果时，将对应`Run`的`run.metadata['pending_tool_calls']`计数减一。
        2.  **关键逻辑**: 只有当`pending_tool_calls`减至`0`时，才执行后续的“再次调用LLM”的逻辑。如果计数仍大于`0`，则该方法应直接`return`，继续等待其他工具的结果。

**2. 文件路径: `nexus/tools/registry.py`**
*   **任务**: 实现工具的自动发现与注册。
*   **核心指令**:
    *   创建一个新的`discover_and_register(self, discovery_path: str)`方法。
    *   此方法需要：
        1.  使用`importlib`和`pkgutil`来遍历指定路径（如`nexus/tools/definition`）下的所有模块。
        2.  对于每个模块，查找其中以`_TOOL`结尾的字典常量（如`WEB_SEARCH_TOOL`）。
        3.  根据`_TOOL`常量中的`function.name`，在同一模块中查找同名的函数实现。
        4.  如果两者都找到，则自动调用`self.register()`方法完成注册。

**3. 文件路径: `nexus/main.py`**
*   **任务**: 使用新的自动注册机制。
*   **核心指令**:
    *   移除所有手动的`tool_registry.register(...)`代码行。
    *   在实例化`ToolRegistry`后，调用`tool_registry.discover_and_register('nexus.tools.definition')`来自动完成所有工具的注册。

**4. 文件路径: `nexus/services/context.py`**
*   **任务**: 将`tools.md`纳入System Prompt的构建。
*   **核心指令**:
    *   修改`handle_build_request`方法中的Prompt拼接逻辑。
    *   在加载`persona.md`之后，增加一步：加载`prompts/xi/tools.md`的内容。
    *   将`persona.md`和`tools.md`的内容拼接成一个完整的`system_prompt`字符串，再将其作为`system`角色的消息内容。确保两者之间有适当的分隔符（如`---`）以保持清晰。

---
**交付要求：**
你必须为上述4个文件，一次性生成它们各自更新后的完整代码。代码必须解决多工具调用的竞态条件，实现工具的自动化注册，并正确构建包含工具描述的System Prompt。

**任务开始。**