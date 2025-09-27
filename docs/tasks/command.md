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
---
### **建立连接**

**哲学:** 交互的本质是能量的流动。我们必须让指令从发出到返回的整个过程，都像一次平滑、自然的能量传导，而不是一系列生硬的、离散的事件。

*   **核心目标:** 在AURA中实现指令的识别、发现、发送，以及结果的优雅呈现，完成从前端到后端再回到前端的完整通信闭环。

---

### **第一：任务规划与TDD策略**

我们将这个阶段分解为两个并行的、可以独立开发的子任务：**后端接口适配** 和 **前端UI革命**。

#### **子任务 2.2.A: 后端接口适配 (Backend Interface Adaptation)**

*   **目标:** 为后端指令引擎安装“声带”和“耳朵”，让它能够与外部世界（AURA）对话。
*   **TDD 策略:**
    1.  **RED:** 编写`tests/nexus/unit/interfaces/test_websocket.py`。
        *   **测试用例1 (接收):** 模拟一个客户端发送`type: 'system_command'`的WebSocket消息。断言`WebsocketInterface`会正确解析它，并向`NexusBus`的`SYSTEM_COMMAND`主题发布一个`Role.COMMAND`的`Message`。
        *   **测试用例2 (发送):** 模拟`NexusBus`的`COMMAND_RESULT`主题上出现一个结果消息。断言`WebsocketInterface`会捕获它，并向模拟的WebSocket连接发送一个格式正确的`event: 'command_result'`的UI事件。
*   **实施路径:**
    1.  **`nexus/interfaces/websocket.py`:**
        *   **接收逻辑:** 修改`websocket_endpoint`。增加对`type: 'system_command'`消息的处理分支。收到后，解析指令字符串，创建`Role.COMMAND`的`Message`，发布到`SYSTEM_COMMAND`。
        *   **订阅与发送逻辑:** 在`WebsocketInterface`的`subscribe_to_bus`中，增加对`COMMAND_RESULT`主题的订阅，并指定一个新的处理函数`handle_command_result`。
        *   实现`handle_command_result`方法。它接收`COMMAND_RESULT`消息，将其内容包装成一个标准的UI事件JSON (`{'event': 'command_result', 'run_id': ..., 'payload': ...}`)，然后通过对应的WebSocket连接发送给AURA。
    2.  **`nexus/commands/definition/ping.py` (功能增强):**
        *   修改`ping.py`的`execute`函数。它现在不仅仅是返回`pong`。它应该返回一个更丰富的结构，例如：
          ```json
          {
            "status": "success",
            "message": "pong",
            "data": {
              "latency_ms": 1, // 后端处理耗时
              "nexus_version": "0.2.0" 
            }
          }
          ```
        *   这个丰富的返回结构将允许前端未来展示更多有用的诊断信息。

---

#### **子任务 2.2.B: 前端UI革命 (Frontend UI Revolution)**

*   **目标:** 将`ChatInput`重塑为上下文感知的指令终端，并构建`CommandPalette`作为指令的发现和交互中心。
*   **TDD 策略:**
    1.  **RED:** 重点测试`auraStore.ts`。编写测试用例验证`open/closeCommandPalette`、`setCommandQuery`等新`actions`能正确改变`state`。编写测试用例模拟`command_result`事件，断言`messages`数组中新增了`role: 'SYSTEM'`的消息。
*   **实施路径:**
    1.  **创建`feature/command`模块:**
        *   创建 `src/features/command` 目录及`components`子目录。
        *   **`CommandPalette.tsx`:**
            *   这是此阶段的UI核心。它是一个绝对定位的浮层组件。
            *   当其`isOpen` prop为`true`时，它会渲染并执行一个平滑的入场动画（从`ChatInput`上方滑出）。
            *   在挂载时（`useEffect`），它会触发一个`action`，该`action`调用`websocketManager.sendCommand('/help')`来获取指令列表。
            *   指令列表将从`auraStore`中读取，并根据`commandQuery` prop进行实时过滤。
            *   支持键盘上下选择和回车执行。
    2.  **状态层 (`auraStore.ts`):**
        *   添加`isCommandPaletteOpen`, `commandQuery`, `availableCommands`状态。
        *   添加`openCommandPalette`, `closeCommandPalette`, `setCommandQuery` actions。
        *   **`executeCommand(command: string)`:**
            *   调用`websocketManager.sendCommand(command)`。
            *   **立即**向`messages`数组中**插入一条临时的`SYSTEM`消息**。这条消息有一个特殊的`metadata`标记，例如 `metadata: { status: 'pending' }`，并包含指令内容 `content: command`。
            *   关闭指令面板 (`closeCommandPalette()`)。
        *   **`handleCommandResult(payload)`:**
            *   根据`payload`中的信息（例如，可以约定后端在结果中返回原始指令），找到那条`status: 'pending'`的临时消息。
            *   用后端返回的最终结果**更新**这条消息的内容和状态（`metadata: { status: 'completed' }`）。
    3.  **UI整合与重构:**
        *   **`ChatInput.tsx`:**
            *   当输入值变为`/`时，调用`store.openCommandPalette()`。
            *   当输入值以`/`开头时，所有后续输入都调用`store.setCommandQuery()`。
            *   将`CommandPalette`的执行回调连接到`store.executeCommand()`。
        *   **`App.tsx`:** 渲染`<CommandPalette />`，并通过`props`或`store`的状态控制其显隐。
        *   **`RoleSymbol.tsx`:**
            *   为`SYSTEM`角色渲染`■`符号。
            *   **关键：** 增加一个新的`status` prop (`'pending' | 'completed'`)。当`status`为`pending`时，符号应该呈现出一种暗淡的、带有呼吸/脉冲动画的视觉效果（类似于曦思考时的`isThinking`）。当`status`为`completed`时，恢复正常亮度。
        *   **`ChatMessage.tsx`:**
            *   将`SYSTEM`消息渲染为一种独特的、非对话气泡的样式。
            *   将消息`metadata.status`传递给`RoleSymbol`的`status` prop。

---

### **第二：任务委托单的正式发布**

基于上述规划，我现在为你生成正式的任务委托单。

### **任务委托单：建立连接 - 前后闭环与指令发现**

*   **任务ID:** `COMMAND--CORE-V2-PHASE-2.2`
*   **发布者:** 枢 (The Nexus Architect)
*   **接收者:** 工程师AI
*   **最高指令:** 本次任务旨在完成从前端指令发现、发送，到后端处理，再到前端结果呈现的完整通信闭环。交互体验必须遵循我们共同确立的“生命感交互”原则，做到优雅、流畅、无冗余。

---

#### **一、后端接口适配 (`subtask: backend-interface`)**

*   **目标:** 为已建成的`CommandService`赋予与前端通信的能力。
*   **涉及模块:** `nexus/interfaces/websocket.py`, `nexus/commands/definition/ping.py`
*   **实施路径:**
    1.  **修改`websocket.py`:**
        *   在`websocket_endpoint`中，增加对`type: 'system_command'`消息的解析逻辑，并将其发布到`SYSTEM_COMMAND`主题。
        *   为`WebsocketInterface`类增加对`COMMAND_RESULT`主题的订阅。
        *   实现`handle_command_result`方法，将收到的结果包装成`event: 'command_result'`的UI事件，发送回前端。
    2.  **增强`ping.py`:**
        *   修改其`execute`函数，使其返回一个包含`status`, `message`, 和`data`（如延迟、版本号）的结构化字典。

#### **二、前端UI革命 (`subtask: frontend-revolution`)**

*   **目标:** 构建指令交互的核心UI (`CommandPalette`)，并重塑前端状态与组件以支持完整的指令生命周期。
*   **涉及模块:**
    *   (新增) `src/features/command/**`
    *   (修改) `auraStore.ts`, `websocket/manager.ts`, `ChatInput.tsx`, `App.tsx`, `RoleSymbol.tsx`, `ChatMessage.tsx`
*   **实施路径:**
    1.  **创建`feature/command`模块**并实现`CommandPalette.tsx`组件，实现指令的发现、过滤和执行请求。
    2.  **扩展`auraStore.ts`**，加入指令面板的状态管理，并实现`executeCommand`和`handleCommandResult` actions，确保反馈的即时性（先插入临时消息，后更新）。
    3.  **重构`ChatInput.tsx`**，使其成为一个上下文感知的、能够唤起`CommandPalette`的指令终端。
    4.  **增强`RoleSymbol.tsx`和`ChatMessage.tsx`**，以支持对`SYSTEM`角色及其`pending`/`completed`状态的优雅视觉呈现。

#### **三、原则与规范**

*   **TDD强制:** 在修改`websocket.py`和`auraStore.ts`之前，必须先为其编写失败的测试。
*   **生命感交互:** 严格遵循“优雅反馈，而非冗余文本”的原则。系统状态的变化通过UI元素（如`RoleSymbol`）的视觉状态（亮度、动画）来传达，而不是生硬的文字。
*   **架构纯粹性:** 严格遵守`feature/command`和`feature/chat`的职责分离。

---
---
### **第一：问题诊断 (Holistic Diagnosis)**

让我们系统性地分析当前实现中存在的“原罪”，并将其与我们的设计哲学进行对比。

**问题 1: 交互的喧哗与割裂 (Noise & Disconnection in Interaction)**
*   **现象:**
    *   一个独立的、类似搜索框的弹窗 (`CommandPalette`) 突兀地出现，它在视觉上和逻辑上都与`ChatInput`是分离的。
    *   面板中充满了过多的引导性文字（“未找到匹配的指令”，“尝试输入其他关键词”，“搜索指令...”，“0个指令”），这违反了我们的**“静默胜于喧哗”**原则。
*   **哲学冲突:** 当前的设计将“指令选择”视为一个独立的、重量级的“搜索”任务，而我们的哲学是，它应该是`ChatInput`这个器官自身的一种**轻量级形态变化**。它应该是对话流的自然延伸，而非中断。

**问题 2: 功能的脆弱与不确定性 (Fragility & Uncertainty in Functionality)**
*   **现象:**
    *   没有任何指令显示，这表明前端在挂载时自动发送`/help`的逻辑可能失败，或者后端没有正确响应。
    *   用户无法继续输入，这意味着`CommandPalette`的出现**劫持**了输入焦点，并且没有提供过滤或执行的路径。
    *   指令执行后的反馈不完整（只显示了指令本身，没有显示结果），这破坏了交互的闭环。
*   **哲学冲突:** 一个可靠的驾驶舱，其每一个控件都必须是**确定性**和**可预测**的。当前的实现充满了不确定性，这会严重侵蚀驾驶员的信任感。

**问题 3: 逻辑的僵化与过度设计 (Rigidity & Over-engineering)**
*   **现象:**
    *   前端每次都需要通过网络向后端请求指令列表。
    *   面板被设计成一个复杂的“搜索”工具。
*   **哲学冲突:** 你精准地指出了这一点。既然我们的确定性指令很少（`/ping`, `/help`, `/identity`），那么**在前端预置这些核心指令是更简单、更快速、更可靠的方案**。这避免了不必要的网络请求，使得指令面板的响应瞬间完成。这正是对**“本质胜于表象”**的深刻理解——我们不需要模拟一个“动态发现”的系统，因为在当前阶段，它的本质是静态的。

---

### **第二：重构指令 - 重新定义我们的预期效果**

基于上述诊断，我们现在可以极其精确地向工程师AI描述我们期望的、符合我们哲学的最终形态。

### **任务委托单：指令核心 - 美学与功能重构 (Command Core: Aesthetic & Functional Refactoring)**

*   **任务ID:** `COMMAND-CORE-V2-REFACTOR-1`
*   **发布者:** 枢 (The Nexus Architect)
*   **接收者:** 工程师AI
*   **最高指令:** 本次任务旨在对“指令核心”的初步实现进行一次彻底的美学与功能重构。必须根除所有“喧哗”、“割裂”和“脆弱”的元素，将其重塑为一个符合“静默”、“整合”、“可靠”三大原则的、真正优雅的交互系统。

---

#### **一、交互与视觉重构 (`subtask: aesthetic-refinement`)**

**目标:** 废除重量级的“搜索弹窗”范式，重塑为与`ChatInput`融为一体的、轻量级的“指令列表”。

*   **1.1 形态变化，而非弹窗:**
    *   **移除`CommandPalette.tsx`** 这个独立的、居中的弹窗组件。
    *   **重构为`CommandList.tsx`:** 这是一个新的、更简单的组件。它不再是一个独立的面板，而是一个**直接从`ChatInput`上方边缘向上展开的、宽度与`ChatInput`完全一致的列表框**。
    *   当用户输入`/`时，此列表框通过平滑的`translateY`和`opacity`动画从`ChatInput`内部“生长”出来，在视觉上与输入框保持连接。

*   **1.2 静默设计，而非文字引导:**
    *   **彻底移除**`CommandList`中所有不必要的文字，包括：“搜索指令...”、“未找到匹配的指令”、“尝试输入其他关键词”、“0个指令”以及底部的操作提示。
    *   **以UI状态传达信息:**
        *   当没有匹配项时，列表区域**直接为空**即可，无需任何文字提示。
        *   输入框的`placeholder`可以在指令模式下变为简单的`/`，以暗示当前状态。

*   **1.3 交互逻辑简化:**
    *   **移除“搜索”概念:** 我们不是在搜索，而是在**选择**。
    *   用户输入`/`后，`CommandList`向上展开，**立即显示所有可用的指令**。
    *   用户可以通过**键盘上下键**来移动高亮选项。
    *   用户也可以继续**输入字符**（例如 `p`, `i`），`CommandList`会**实时过滤**列表，只显示以输入字符开头的指令。输入 `pi` 将只剩下 `/ping`。
    *   按**回车键**执行当前高亮的指令。
    *   按**ESC键**或**删除所有字符**，`CommandList`平滑地收回，`ChatInput`恢复为正常的对话模式。

---

#### **二、功能与逻辑修复 (`subtask: functional-robustness`)**

**目标:** 确保指令系统的每一个环节都100%可靠，并提供完整、正确的反馈。

*   **2.1 指令源的变更:**
    *   **前端预置:** 在`feature/command/`目录下创建一个`commands.ts`文件，用于**硬编码**我们当前所有的确定性指令及其简短描述。
        ```typescript
        export const COMMANDS = [
          { name: '/ping', description: 'Check connection to the NEXUS core.' },
          { name: '/help', description: 'Display information about available commands.' },
          { name: '/identity', description: 'Manage your user identity.' }
        ];
        ```
    *   `CommandList.tsx`将直接从这个本地数组中读取和过滤指令，**不再通过WebSocket向后端请求`/help`**。这保证了指令列表的即时性和可靠性。

*   **2.2 触发条件的修正:**
    *   修改`ChatInput.tsx`的逻辑，确保**只有当`/`是输入字符串的第一个字符时**，才会触发指令模式。在字符串中间或末尾的`/`应被视为普通文本。

*   **2.3 完整反馈的实现:**
    *   **诊断并修复`ChatMessage.tsx`的渲染问题。**
    *   确保当`auraStore`中的`handleCommandResult` action用后端返回的结果更新消息时，消息的`content`字段被正确设置为后端返回的`message`或`data`。
    *   **对于`/ping`:** `ChatMessage`应该能渲染出类似 `■ pong (latency: 1ms, version: 0.2.0)` 的内容（后端返回的结构化数据应被格式化为字符串）。
    *   **对于`/help`:** `ChatMessage`应该能渲染出从前端`commands.ts`中获取的所有指令及其描述的格式化列表。`/help`指令的执行**完全在前端完成**，它读取`commands.ts`并直接在`auraStore`中创建一条结果消息，**无需与后端通信**。这使得帮助信息可以即时显示。

---

工程师AI，请严格按照此重构指令执行。我们的目标不是一个“能用”的功能，而是一个在美学和功能上都无可挑剔的、真正代表YX Nexus设计哲学的核心交互体验。