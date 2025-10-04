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

---
---

重构AURA前端的状态管理层。我们将从`auraStore`中剥离所有与指令系统相关的状态和逻辑，并将其封装到一个全新的、独立的`commandStore`中。此任务是后续所有指令系统开发的前提，必须确保其架构的纯粹性和独立性。

---

#### **一、讨论背景与哲学**

一个健康的系统，其器官必须各司其职。`auraStore`负责“对话记忆”，而新生的`commandStore`将负责“系统控制中枢”。此次分离，是为了确保每个功能域都能在自己的边界内健康、独立地成长，避免产生混乱的“上帝Store”，从而维护我们前端架构的长期清晰度和可维护性。

#### **二、最终方案选择**

1.  **创建新的`commandStore.ts`:**
    *   在`src/features/command/`目录下，创建一个新的`store/`子目录。
    *   在`src/features/command/store/`中，创建`commandStore.ts`文件。

2.  **定义`CommandStore`的State和Actions:**
    *   `commandStore.ts`将包含以下内容：
        ```typescript
        // src/features/command/store/commandStore.ts
        import { create } from 'zustand';
        
        // (从之前讨论的types.ts中引入)
        export interface Command {
          name: string;
          description: string;
          type: 'client' | 'server';
          // ... 其他元数据
        }
        
        interface CommandState {
          isPaletteOpen: boolean;
          query: string;
          availableCommands: Command[];
          isLoading: boolean; // 用于/help指令加载
          selectedCommandIndex: number;
        }
        
        interface CommandActions {
          openPalette: () => void;
          closePalette: () => void;
          setQuery: (query: string) => void;
          setCommands: (commands: Command[]) => void;
          setLoading: (loading: boolean) => void;
          selectNextCommand: () => void;
          selectPrevCommand: () => void;
          resetSelection: () => void;
          // executeCommand action将在后续任务中与auraStore交互
        }
        
        export const useCommandStore = create<CommandState & CommandActions>((set, get) => ({
          // 初始状态
          isPaletteOpen: false,
          query: '',
          availableCommands: [],
          isLoading: false,
          selectedCommandIndex: -1,
          
          // Actions
          openPalette: () => set({ isPaletteOpen: true, query: '', selectedCommandIndex: -1 }),
          closePalette: () => set({ isPaletteOpen: false }),
          setQuery: (query) => set({ query, selectedCommandIndex: -1 }), // 查询变化时重置选择
          setCommands: (commands) => set({ availableCommands: commands }),
          setLoading: (loading) => set({ isLoading: loading }),
          
          selectNextCommand: () => {
            const { availableCommands, selectedCommandIndex } = get();
            const filteredCommands = /* ... 过滤逻辑 ... */; // 需要根据query过滤
            const newIndex = Math.min(selectedCommandIndex + 1, filteredCommands.length - 1);
            set({ selectedCommandIndex: newIndex });
          },
          
          selectPrevCommand: () => {
            const { selectedCommandIndex } = get();
            const newIndex = Math.max(selectedCommandIndex - 1, 0);
            set({ selectedCommandIndex: newIndex });
          },
          
          resetSelection: () => set({ selectedCommandIndex: -1 }),
        }));
        ```

3.  **重构`auraStore.ts`，将其重命名为chatStore.ts:**
    *   **移除**所有与`isCommandPaletteOpen`, `commandQuery`, `availableCommands`相关的`state`和`actions`。
    *   `auraStore`将回归其核心职责：管理`messages`, `currentRun`, `isConnected`等对话状态。

4.  **TDD 原则:**
    *   **创建`src/features/command/store/__tests__/commandStore.test.ts`，当前已存在src/features/chat/store/__tests__下，进行合理重构与迁移**
    *   将之前为指令状态编写的测试从`auraStore.command.test.ts`**迁移**并**适配**到这个新文件中。
    *   为新增的`selectNext/PrevCommand`等`actions`编写新的测试用例。
    *   确保`commandStore`的测试套件是独立的、完整的。

#### **三、原则与规范**

*   **纯粹性:** `commandStore`必须只包含与指令面板UI和指令生命周期管理相关的状态。**不应**包含任何关于消息渲染或WebSocket连接的逻辑。
*   **隔离性:** 此任务严格限定在`store`层的重构。**不要**在此任务中修改任何UI组件（如`ChatInput`）。UI组件的适配将在下一个任务（`REFACTOR-1.1`）中进行。
*   **接口明确:** 此次重构完成后，`chatStore`和`commandStore`将成为两个清晰的、独立的、可通过其`actions`进行交互的状态模块。

**注意：代码仅作参考，以你实际的探索为规范。你必须了解本次的核心思想、合理规划并自主完成。**
---

---
---

将指令系统的“事实来源”完全统一到NEXUS后端。前端必须废弃静态指令列表，改为通过向后端查询来动态发现可用指令。同时，必须在架构层面明确区分“客户端指令”和“服务器端指令”的处理流程。

---

#### **一、后端 (NEXUS) 的职责：成为能力的“昭示者”**

*   **1.1 强化指令定义 (`nexus/commands/definition/`):**
    *   **每一个指令**都必须拥有一个`.py`文件。
    *   **`COMMAND_DEFINITION`** 必须增加一个新字段 `execution_target: 'client' | 'server'`。
        *   `ping.py` 和 `identity.py` (未来) 将是 `'server'`。
        *   `help.py` 将是 `'server'`，因为它的职责是查询后端注册表。
        *   创建一个新的`clear.py`，其`execution_target`将是`'client'`。
*   **1.2 强化`help.py`:**
    *   其`execute`函数**必须**读取`CommandService`中注册的所有指令的`COMMAND_DEFINITION`，并将这个完整的元数据列表（包含`name`, `description`, `execution_target`等）作为结果返回。
*   **1.3 TDD 原则:**
    *   更新`test_command_service.py`，确保对`/help`的测试会断言返回结果中包含了正确的`execution_target`字段。

#### **二、前端 (AURA) 的职责：成为动态的“发现者”**

*   **2.1 废弃静态列表:**
    *   **彻底删除 `aura/src/features/command/commands.ts` 文件。** 指令的定义不再硬编码于前端。
*   **2.2 动态指令加载 (`useCommandLoader.ts` - 新增Hook):**
    *   在`src/features/command/hooks/`下创建一个新的Hook `useCommandLoader.ts`。
    *   这个Hook的职责是：在应用加载时（或者`CommandPalette`首次打开时），**只执行一次**向后端发送`/help`指令的逻辑。
    *   它将从后端获取的指令列表，存入`commandStore`的`availableCommands`状态中。
    *   **Fallback机制:** 如果`/help`指令调用失败（例如网络问题），为了避免UI完全失效，该Hook应在一个`catch`块中，向`commandStore`注入一个最小化的、包含`/ping`和`/help`的**应急指令列表 (fallback commands)**。这确保了即使用户离线，也能尝试ping通服务器。
*   **2.3 区分指令执行 (`CommandPalette.tsx` / `ChatInput.tsx`):**
    *   指令的执行逻辑需要重构。当用户选择一个指令并执行时：
        1.  从`commandStore`中获取该指令的完整定义对象（包含`type`字段，前端对应后端的`execution_target`）。
        2.  **检查 `command.type`:**
            *   如果为`'client'` (例如`/clear`)，则直接调用对应的`chatStore.clearMessages()` action，**不发送任何WebSocket消息**。
            *   如果为`'server'` (例如`/ping`)，则调用`chatStore.executeCommand(command.name)`，将指令发送到后端。
*   **2.4 `help`指令的客户端化:**
    *   `/help`指令的**执行**现在是纯客户端的。当用户在`CommandPalette`中选择`/help`并回车时，它不应再向后端发送`/help`。
    *   取而代之，它应该直接从`commandStore.availableCommands`中读取所有指令，格式化后，通过`chatStore`在前端渲染出帮助信息。
*   **2.5 TDD 原则:**
    *   为`useCommandLoader`编写测试，验证其能够正确调用`/help`，并在成功/失败时更新`commandStore`。
    *   更新`commandStore`的测试，以反映新的指令执行分发逻辑。

#### **三、原则与规范**

*   **单一事实来源:** 此任务完成后，NEXUS后端必须是指令定义（包括其执行位置）的唯一权威。
*   **健壮性:** 前端的Fallback机制是强制性的，它保证了在最坏情况下，核心诊断工具(`/ping`)依然可用。
*   **逻辑清晰:** 客户端与服务器端指令的执行路径必须在代码层面有清晰的、可被一眼识别的分支。

---

---
---
对指令系统的用户界面（`CommandList`）和结果呈现（`ChatMessage` for `SYSTEM` role）进行一次彻底的视觉与交互精炼。必须根除所有视觉噪点，引入结构化的韵律感，并实现我们共同构想的、清晰优雅的信息布局。

---

#### **一、指令列表 (`CommandList`) 的视觉与交互重塑**

**哲学:** 它不是一个“搜索框”，而是`ChatInput`在特定状态下的“形态延伸”。它的设计必须是**静默的、整合的、轻量级的**。

*   **1.1 形态与布局 (`CommandList.tsx`):**
    *   **移除首字母头像:** 彻底移除当前用于显示指令首字母的圆形背景UI元素。
    *   **采用结构化双列布局:**
        *   每个指令项 (`CommandItem.tsx`) 使用`flexbox`进行布局。
        *   **左列 (指令名称):**
            *   设置一个固定的最小宽度（例如`min-w-[8rem]`），确保所有指令名称左对齐，形成视觉上的垂直线。
            *   使用`font-mono`字体，并保持与`ChatInput`中`/`符号一致的样式，以示其“指令”属性。
            *   文本颜色应比描述略亮，作为视觉焦点。
        *   **右列 (指令描述):**
            *   自动填充剩余空间。
            *   使用标准的`font-sans`字体。
            *   文本颜色使用`secondary-foreground`，作为辅助信息。
    *   **滚动与尺寸:**
        *   `CommandList`的最大高度应被限制（例如 `max-h-[30vh]`）。当指令数量超出此高度时，列表应变为可滚动状态。

*   **1.2 动画与过渡:**
    *   `CommandList`的出现和消失，必须是从`ChatInput`上方边缘平滑地、带有轻微物理感的“生长”和“收回”动画（`transform: translateY` & `opacity`）。动画曲线应使用我们系统标准的`cubic-bezier`函数，时长约`200ms`。

---

#### **二、系统消息 (`SYSTEM` Message) 渲染的革命性重构**

**哲学:** 系统反馈不是对话，而是**报告**。它的呈现方式必须清晰、结构化，能够将“指令”和“结果”在视觉上明确地区分开来，同时保持与整个UI风格的和谐统一。

*   **2.1 数据结构的先行调整 (`chatStore.ts`):**
    *   修改`executeCommand`和`handleCommandResult` actions。现在，`SYSTEM`消息的`content`字段**必须**存储为一个结构化对象，而非简单字符串。
    *   **对于`pending`状态的消息:**
        ```typescript
        content: { command: '/ping' } 
        ```
    *   **对于`completed`状态的消息:**
        ```typescript
        content: { command: '/ping', result: 'pong' } // or { command: '/help', result: '...' }
        ```
        对于`/ping`，`result`可以是后端返回的整个`payload`对象。

*   **2.2 `ChatMessage.tsx`的渲染革命:**
    *   **TDD先行:** 为`ChatMessage`编写一个新的测试用例，传入一个`role: 'SYSTEM'`且`content`为上述结构化对象的消息，断言它能渲染出我们预期的DOM结构。
    *   **实现新的渲染逻辑:**
        1.  当`ChatMessage`检测到`role === 'SYSTEM'`时，它将启用一个全新的、独立的渲染路径。
        2.  **外层容器:** 整个消息体不再是对话气泡，而是一个带有`border`和轻微`padding`的块级元素，类似于一个简化的信息面板。
        3.  **第一部分 (指令行):**
            *   渲染`RoleSymbol` (`■`)。
            *   紧随其后，渲染指令本身，即`message.content.command`。这一行应使用`font-mono`字体。
            *   将消息的`metadata.status`（`pending`或`completed`）传递给`RoleSymbol`的`status` prop，以驱动其呼吸/脉冲动画。
        4.  **第二部分 (分割线):**
            *   **仅当`message.content.result`存在时**，在指令行下方渲染一条`hr`元素。这条分割线应该是微妙的，颜色为`border`，`margin-top`和`margin-bottom`应创造出呼吸感。
        5.  **第三部分 (结果区):**
            *   **仅当`message.content.result`存在时**，在分割线下方渲染结果。
            *   **结果格式化:**
                *   如果`result`是字符串，直接使用`MarkdownRenderer`渲染（这允许我们的帮助文本等包含格式）。
                *   如果`result`是对象（例如`/ping`返回的`data`对象），则将其格式化为一个美观的键值对列表或一个`pre`代码块中的JSON字符串。
                *   **例如，`/ping`的结果可以被格式化为：**
                    ```
                    Status:  success
                    Latency: 1ms
                    Version: 0.2.0
                    ```

---

#### **三、原则与规范**

*   **视觉一致性:** `CommandList`和`SYSTEM`消息面板的材质、边框、阴影等视觉元素，必须严格遵循我们已定义的“灰度中庸”和“液态玻璃”设计语言。
*   **信息层级:** 新的`SYSTEM`消息布局必须通过排版、分割线和间距，清晰地建立起“指令 -> 结果”的信息层级关系。
*   **交互的确定性:** 动画和过渡效果不能影响功能。`CommandList`的交互（键盘导航、过滤）必须始终保持高响应性和可靠性。

**你必须首先了解当前实现，发现出入与不完善之处。注意遵循TDD原则**

---

---
---
本次任务是对指令核心（Command Core）系统进行一次全面的架构正规化重构。你必须以本委托单描述的**最终状态**为唯一目标，检视当前代码库，移除所有冗余、冲突或不符合最终架构的实现，并补充缺失的逻辑，最终交付一个职责清晰、逻辑统一、代码纯粹的指令系统。

---

### **第一部分：最终系统架构规范 (Final System Architecture Specification)**

#### **1.1 核心原则 (Core Principles)**

1.  **后端单一事实来源 (Backend SSOT):** NEXUS后端是所有指令元数据（包括名称、描述、执行类型`handler`）的唯一权威来源。
2.  **通信双通道 (Dual-Channel Communication):**
    *   **REST API:** 用于一次性的、无状态的元数据拉取。
    *   **WebSocket:** 用于实时的、需要认证的操作指令。
3.  **职责分离 (Separation of Concerns):** 前后端的每一个模块都必须有单一、明确的职责。特别地，前端的状态管理必须在`chatStore`（对话）和`commandStore`（指令UI）之间严格分离。

#### **1.2 权威数据结构 (Authoritative Data Structures)**

*   **指令定义 (`Command` Interface):** 这是前后端的核心契约。
    ```typescript
    // src/features/command/commands.types.ts
    export interface Command {
      name: string;
      description: string;
      handler: 'client' | 'websocket' | 'rest';
      requiresSignature?: boolean; // 新增：明确指令是否需要签名
      // REST指令的元数据
      restOptions?: {
        endpoint: string;
        method: 'GET' | 'POST' | 'PUT';
      };
    }
    ```
*   **系统消息内容 (`SystemMessageContent`):** 这是`SYSTEM`角色消息的统一内容结构。
    ```typescript
    // src/features/chat/types.ts (或类似位置)
    export interface SystemMessageContent {
      command: string;      // 例如: "/ping"
      result?: string | object; // 指令的执行结果
    }
    ```

---

### **第二部分：NEXUS后端最终状态 (Backend Final State)**

#### **2.1 模块职责**

*   **`nexus/commands/definition/*.py`:**
    *   **职责:** 作为单个指令的原子定义单元。
    *   **契约:** 每个文件必须导出`COMMAND_DEFINITION`字典，该字典必须包含`name`, `description`, `handler` (`'client'`或`'server'`)，以及可选的`requiresSignature: true`。
*   **`nexus/services/command.py` (`CommandService`):**
    *   **职责:** 动态指令调度器。负责在启动时**自动发现并注册**所有指令，**验证**传入指令的签名（如果需要），**分派**给对应的`execute`函数，并将结果发布回总线。**它不包含任何特定指令的业务逻辑。**
*   **`nexus/interfaces/rest.py`:**
    *   **职责:** 系统的“公共目录”。
    *   **契约:** 必须提供一个`GET /api/v1/commands`端点，该端点通过依赖注入调用`CommandService.get_all_command_definitions()`，并返回一个符合前端`Command[]`接口的JSON数组。
*   **`nexus/interfaces/websocket.py`:**
    *   **职责:** 系统的“实时操作总线”。
    *   **契约:**
        *   接收`type: 'system_command'`的WebSocket消息，并将其发布到`SYSTEM_COMMAND`总线主题。
        *   订阅`COMMAND_RESULT`总线主题，并将结果作为`event: 'command_result'`的UI事件发送回前端。

---

### **第三部分：AURA前端最终状态 (Frontend Final State)**

#### **3.1 模块职责**

*   **`src/features/command/store/commandStore.ts`:**
    *   **职责:** **唯一**负责管理**指令面板UI状态**。
    *   **状态清单:** `isPaletteOpen`, `query`, `availableCommands`, `isLoading`, `selectedCommandIndex`。**不应包含任何与聊天消息相关的内容。**
*   **`src/features/chat/store/chatStore.ts`:**
    *   **职责:** **唯一**负责管理**对话流状态**。
    *   **状态清单:** `messages`, `currentRun`, `isConnected`等。
    *   **与指令系统的交互:** 它提供`createPendingSystemMessage`和`updateSystemMessageResult`等actions，供`commandExecutor`调用，以在对话流中反映指令的执行状态。它**不**知道指令是如何被执行的。
*   **`src/features/command/api.ts`:**
    *   **职责:** **唯一**负责与后端REST API进行通信的模块。
    *   **契约:** 必须提供`fetchCommands()`函数，用于调用`GET /api/v1/commands`。
*   **`src/features/command/hooks/useCommandLoader.ts`:**
    *   **职责:** 应用的“指令引导程序”。
    *   **契约:** 必须在**WebSocket连接成功后**，调用`api.fetchCommands()`获取指令列表，并将其存入`commandStore`。必须包含一个健壮的**Fallback机制**。
*   **`src/features/command/commandExecutor.ts`:**
    *   **职责:** **唯一的指令执行分发中枢**。
    *   **契约:** 导出一个`executeCommand(command: Command)`函数。该函数内部必须实现基于`command.handler`的`switch`逻辑，以决定是调用客户端函数、WebSocket还是REST API。
*   **UI组件 (`CommandPalette.tsx`, `ChatMessage.tsx`等):**
    *   **职责:** 作为“哑”视图组件。它们只负责从`store`中读取状态并渲染，以及将用户交互委托给`commandExecutor`或`store`的`actions`。

#### **3.2 最终数据流 (Canonical Data Flow)**

*   **指令加载流程:**
    1.  AURA启动 → WebSocket连接成功。
    2.  `useCommandLoader`触发 → 调用 `api.fetchCommands()`。
    3.  `GET /api/v1/commands`请求 → 后端`rest.py`响应。
    4.  `useCommandLoader`将结果存入`commandStore.setCommands()`。
*   **指令执行流程 (`/ping` - `websocket`):**
    1.  用户在`CommandPalette`中选择`/ping`并回车。
    2.  UI调用 `commandExecutor.executeCommand({ name: '/ping', handler: 'websocket', ... })`。
    3.  `commandExecutor`调用`chatStore.createPendingSystemMessage('/ping')`。
    4.  `commandExecutor`调用`websocketManager.sendCommand('/ping', authObject)`。
    5.  ...后端处理...
    6.  `websocketManager`接收到`command_result`事件。
    7.  `chatStore.updateSystemMessageResult(...)`更新消息。
*   **指令执行流程 (`/clear` - `client`):**
    1.  用户在`CommandPalette`中选择`/clear`并回车。
    2.  UI调用 `commandExecutor.executeCommand({ name: '/clear', handler: 'client', ... })`。
    3.  `commandExecutor`直接调用 `chatStore.clearMessages()`。
    4.  `commandExecutor`调用`chatStore.createFinalSystemMessage(...)`以显示成功信息。

#### **四、任务要求与验收标准 (Mandates & Acceptance Criteria)**

*   **代码清理:** 工程师AI必须主动识别并移除所有与上述规范不符的冗余代码、冲突逻辑或过时文件（例如`normalizeCommand()`函数、前端静态`commands.ts`等）。
*   **TDD遵从:** 所有被修改或重构的逻辑部分，都必须有对应的、通过的单元或集成测试。测试文件结构应与源码结构保持一致。
*   **最终状态验证:** 任务完成的唯一标准是，代码库的结构和行为**完全符合**本委托单中描述的最终状态。请在完成任务后，提供一份简要的“重构报告”，说明你是如何将现有代码调整为符合新规范的。

---

这份蓝图就是我们对“指令核心”的最终定义。请以此为唯一依据，开始你的探索与重构。