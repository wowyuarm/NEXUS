本次任务的核心是构建NEXUS后端的指令处理引擎。此引擎必须是**确定性的、可自动发现的、且完全解耦的**。我们将通过TDD的方式，首先锻造这个看不见但至关重要的系统内核，为所有未来的交互能力奠定坚实的基础。

---

#### **一、讨论背景与哲学**

我们正在为YX Nexus构建其操作系统。这个操作系统的内核，即`CommandService`，必须像一个优秀的操作系统内核一样：稳定、高效、且对上层应用（即具体的指令）一无所知，只负责调度。我们采用“声明式定义”和“自动发现”的原则，确保系统的每一次能力扩展，都像是安装一个新的、独立的软件，而非修改内核代码。

#### **二、权衡与决策**

我们采纳“混合范式”中的“精确模式”作为此阶段的实现基础。这意味着：

*   **架构模式:** 仿照`ToolRegistry`的成功经验，我们将创建一个`commands/definition`目录，用于存放所有指令的独立定义模块。
*   **执行流程:** 指令的执行是**确定性的函数调用**，不涉及任何LLM，以保证速度、可靠性和成本效益。
*   **依赖管理:** `CommandService`将作为依赖注入的中心，向各个指令模块提供其所需要的系统服务。

#### **三、最终方案选择：构建`CommandService`及其生态**

**涉及模块:**
*   **(新增)** `nexus/commands/definition/ping.py`
*   **(新增)** `nexus/commands/definition/help.py`
*   **(新增)** `nexus/services/command.py`
*   **(新增)** `tests/nexus/integration/services/test_command_service.py`
*   **(修改)** `nexus/core/models.py`
*   **(修改)** `nexus/core/topics.py`
*   **(修改)** `nexus/main.py`

**探索与实施路径 (遵循TDD):**

1.  **创建测试骨架 (RED):**
    *   **立即创建 `tests/nexus/integration/services/test_command_service.py`。**
    *   编写第一个集成测试 `test_ping_command_e2e()`:
        *   它需要一个模拟的`NexusBus`。
        *   它将实例化一个（尚未存在的）`CommandService`。
        *   它会模拟向`system.command`主题发布一个`Role.COMMAND`的消息，内容为`/ping`。
        *   它会断言模拟的`NexusBus`的`publish`方法被调用，且发布到了`command.result`主题，内容为`{'status': 'success', 'message': 'pong'}`。
    *   **运行测试，确认它因为缺少几乎所有依赖而失败。**

2.  **构建基础协议 (GREEN - Step 1):**
    *   **`nexus/core/models.py`:** 在`Role`枚举中添加 `COMMAND = "COMMAND"`。
    *   **`nexus/core/topics.py`:** 添加 `SYSTEM_COMMAND = "system.command"` 和 `COMMAND_RESULT = "command.result"`。
    *   **重新运行测试**，失败信息应该会变化，指向缺失的服务。

3.  **创建指令定义 (GREEN - Step 2):**
    *   创建新目录 `nexus/commands/definition/`。
    *   **`nexus/commands/definition/ping.py`:**
        *   创建`COMMAND_DEFINITION`字典，包含`name: 'ping'`和`description`。
        *   创建异步`execute(context)`函数，它不使用`context`，直接返回`{'status': 'success', 'message': 'pong'}`。
    *   **`nexus/commands/definition/help.py`:**
        *   创建`COMMAND_DEFINITION`字典。
        *   创建异步`execute(context)`函数。它将从`context['command_definitions']`（我们将在`CommandService`中注入这个）获取所有指令的定义，并格式化后返回。

4.  **实现`CommandService`内核 (GREEN - Step 3):**
    *   **`nexus/services/command.py`:**
        *   创建`CommandService`类。其`__init__`方法应能接收`bus`和其他服务依赖（如`db_service`）。
        *   实现`_discover_and_register_commands`方法，使用`importlib`和`pkgutil`扫描`nexus.commands.definition`目录，填充`_command_registry`（执行函数）和`_command_definitions`（元数据）。
        *   实现`handle_command`方法：
            *   解析收到的`Message`内容（指令字符串）。
            *   根据指令名从`_command_registry`查找执行器。
            *   构建`context`字典，注入必要的依赖（对于`/help`，需要注入`self._command_definitions`）。
            *   调用`await executor(context)`。
            *   处理成功和异常情况，构建结果`Message`。
            *   将结果`Message`发布到`COMMAND_RESULT`主题。
    *   **再次运行测试，此时`test_ping_command_e2e`应该通过。**
    *   **为`/help`指令编写一个新的测试用例**，并确保它也能通过。

5.  **系统整合 (GREEN - Step 4):**
    *   **`nexus/main.py`:**
        *   在`main`函数中，实例化`CommandService`。注意构造函数参数，需要将已实例化的其他服务（如`database_service`）传递给它。
        *   将其添加到`services`列表中，以便其`subscribe_to_bus`方法被自动调用。

6.  **重构 (REFACTOR):**
    *   审视整个实现，特别是`CommandService`。确保代码清晰、注释完备、错误处理健壮。确保指令的发现机制对未来新增的指令是可扩展的。

#### **四、原则与规范**

*   **TDD强制:** **必须**以`test_command_service.py`中的失败测试作为起点。每一个功能的实现都必须以使一个测试通过为直接目标。
*   **解耦:** `CommandService`内核**绝不能**包含任何针对特定指令（如`ping`或`help`）的硬编码逻辑。它必须是一个纯粹的、动态的调度器。
*   **接口稳定性:** `execute(context)`函数签名和返回的`{'status': ..., 'message': ...}`结构必须在所有指令中保持一致，这是指令系统的内部API。

---