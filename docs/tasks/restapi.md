搭建NEXUS和AURA的下一代通信架构骨架。后端需将REST和WebSocket接口彻底分离，前端需建立能够分发到不同通道的指令处理机制。此任务以TDD为核心，优先确保架构的正确性和可测试性，而非功能的完整性。

---

#### **第一部分：后端 (NEXUS) - 器官分离手术 (TDD-First)**

**目标:** 将`WebsocketInterface`的HTTP功能剥离，创建一个独立的`RestInterface`，并由`main.py`统一集成。

1.  **RED (编写失败的测试):**
    *   创建一个新的测试文件 `tests/nexus/unit/interfaces/test_rest.py`。
    *   编写一个测试 `test_commands_endpoint_exists()`，它将使用FastAPI的`TestClient`来请求一个（尚未存在的）`/api/v1/commands`端点，并断言响应状态码为200。此测试将失败。

2.  **GREEN (搭建骨架):**
    *   **创建`nexus/interfaces/rest.py`:**
        *   从`fastapi`导入`APIRouter`。
        *   创建一个`router = APIRouter()`实例。
        *   定义一个临时的、骨架式的`GET /commands`端点，它暂时只返回一个硬编码的空列表 `[]`。
            ```python
            from fastapi import APIRouter, Depends

            router = APIRouter()

            # 这是一个占位符，演示如何依赖注入
            def get_command_service():
                # 实际的依赖注入将在main.py中处理
                # 这里只是为了让路由能定义
                pass

            @router.get("/commands")
            async def get_all_commands(cmd_svc = Depends(get_command_service)):
                return [] 
            ```
    *   **重构`nexus/interfaces/websocket.py`:**
        *   移除所有FastAPI的`app`实例化和HTTP端点定义（`/`, `/health`等）。
        *   导出一个新的函数，例如`def add_websocket_route(app: FastAPI, ws_interface: WebsocketInterface):`，这个函数接收一个FastAPI `app`实例，并将WebSocket路由`@app.websocket(...)`添加到该实例上。
    *   **重构`nexus/main.py`:**
        *   在`main`函数顶部，实例化主`app = FastAPI()`。
        *   导入`rest.py`中的`router as rest_router`。
        *   导入`websocket.py`中的`add_websocket_route`函数。
        *   **依赖注入的核心:** 在这里，你需要设计一种方法，将已实例化的`CommandService`传递给`rest.py`中的端点。FastAPI的`Depends`与`app.dependency_overrides`是实现这一点的标准方式。
            ```python
            # In main.py
            cmd_service = CommandService(...)
            
            # 让rest.py中的get_command_service依赖被覆盖
            from nexus.interfaces import rest
            app.dependency_overrides[rest.get_command_service] = lambda: cmd_service
            
            app.include_router(rest_router, prefix="/api/v1")
            add_websocket_route(app, websocket_interface)
            ```
    *   **重新运行测试，`test_commands_endpoint_exists`现在应该通过。**

3.  **REFACTOR (清理与完善):**
    *   确保`main.py`中的集成逻辑清晰。
    *   为新的文件和函数添加文档字符串，解释其职责和边界。

---

#### **第二部分：前端 (AURA) - 智能分发中枢 (TDD-First)**

**目标:** 重构前端指令定义和执行逻辑，使其能够根据指令的`handler`类型，智能地选择`client`, `websocket`, 或`rest`通道。

1.  **RED (编写失败的测试):**
    *   在`commandStore.test.ts`或一个新的`commandExecutor.test.ts`中，编写测试用例。
    *   模拟执行一个`handler: 'rest'`的指令。断言`fetch` API被调用，并且请求的URL是正确的。
    *   模拟执行一个`handler: 'websocket'`的指令。断言`websocketManager.sendCommand`被调用。
    *   模拟执行一个`handler: 'client'`的指令。断言`chatStore.clearMessages`（或其他客户端action）被调用。
    *   这些测试都会失败。

2.  **GREEN (搭建骨架):**
    *   **(新增) `src/features/command/commands.types.ts`:**
        *   创建此文件，并定义我们共同设计的、成熟的`Command`接口：
            ```typescript
            export interface Command {
              name: string;
              description: string;
              handler: 'client' | 'websocket' | 'rest';
              restOptions?: {
                endpoint: string;
                method: 'GET' | 'POST' | 'PUT';
              };
              // ... 其他元数据
            }
            ```
    *   **(新增) `src/features/command/commandExecutor.ts`:**
        *   创建这个新模块，它的职责是**执行指令**。
        *   导出一个`executeCommand(command: Command, args?: any)`函数。
        *   在这个函数内部，实现一个`switch (command.handler)`的逻辑分支：
            *   `case 'client'`: 调用相应的`store` action。
            *   `case 'websocket'`: 调用`websocketManager.sendCommand(...)`。
            *   `case 'rest'`: 使用`fetch` API调用`command.restOptions.endpoint`。
            *   （此阶段，这些分支的实现可以是简单的占位符或`console.log`，只要能让测试通过即可）。
    *   **重构`chatStore.ts`和`commandStore.ts`:**
        *   从`chatStore`中移除`executeCommand` action。
        *   UI组件（如`CommandPalette`）在执行指令时，将直接调用`commandExecutor.ts`中的`executeCommand`函数。
        *   `commandExecutor`在执行前后，可以调用`store`中的actions来更新UI状态（例如，创建pending消息）。
    *   **(新增) `src/features/command/api.ts`:**
        *   创建一个专门用于获取指令列表的API调用函数 `fetchCommands()`，它会fetch `/api/v1/commands`。
    *   **重构`useCommandLoader.ts`:**
        *   它现在将调用`api.ts`中的`fetchCommands()`来获取指令列表。

3.  **REFACTOR (清理与完善):**
    *   确保`commandExecutor.ts`的职责单一且清晰。
    *   确保`store`的职责回归到纯粹的状态管理。
    *   为新增的模块和函数添加文档，阐明其在指令执行流程中的作用。

#### **原则与规范**

*   **骨架优先:** 本次任务的验收标准是**架构的正确性**，而不是功能的完整性。例如，REST端点可以返回空数据，指令执行器可以只打印日志，但文件结构、模块职责、依赖关系和测试必须是正确的。
*   **TDD驱动:** 每一步重构都必须由测试驱动。先为期望的结构编写一个失败的测试，然后通过搭建这个结构来让测试通过。
*   **接口契约:** 明确`Command`接口是前后端通信的契约核心，确保其类型定义的精确性。

---

---
---
本次任务旨在激活新建立的“双通道”通信架构。必须实现后端指令的完整元数据暴露，并通过REST API通道将这些“事实”传递给前端，让AURA能够动态地、准确地学习到NEXUS所拥有的全部能力。

---

#### **第一部分：后端 (NEXUS) - 成为能力的“昭示者”**

**目标:** 完整实现`/api/v1/commands`端点，使其能返回所有已注册指令的详细元数据。

1.  **`nexus/commands/definition/` (能力定义):**
    *   **TDD先行:** 在`test_command_service.py`中，编写测试断言`_discover_and_register_commands`能正确加载`clear.py`。
    *   **创建`clear.py`:**
        *   创建此文件，其`COMMAND_DEFINITION`必须包含`'name': 'clear'`, `'description'`, `handler: 'client'`。
        *   其`execute`函数可以为空或返回一个简单的成功消息，因为它只在后端被“声明”，而不会被“执行”。
    *   **更新`help.py` & `ping.py`:**
        *   确保这两个文件中`COMMAND_DEFINITION`的`handler`字段被正确设置为`'server'`。
    *   **`identity.py`:**
        *   其`COMMAND_DEFINITION`应包含`'name': 'identity'`, `handler: 'server'`, 以及我们之前讨论的`requiresSignature: true`。

2.  **`nexus/interfaces/rest.py` (能力暴露):**
    *   **TDD先行:** 在`test_rest.py`中，修改`test_commands_endpoint_exists`。现在它必须断言返回的JSON数组**不为空**，并且包含了`ping`, `help`, `clear`, `identity`四个指令的正确元数据。
    *   **实现端点逻辑:**
        *   修改`GET /commands`端点。
        *   通过FastAPI的依赖注入，获取`CommandService`实例。
        *   调用`CommandService`的一个新方法 `get_all_command_definitions()` (你需要在`CommandService`中创建它)。
        *   这个新方法将简单地返回内部的`_command_definitions`字典的值。
        *   将这个指令列表作为JSON响应返回。

3.  **`nexus/services/command.py` (能力聚合):**
    *   **TDD先行:** 为`get_all_command_definitions`方法编写单元测试。
    *   **实现`get_all_command_definitions()`方法:** 该方法返回`list(self._command_definitions.values())`。

---

#### **第二部分：前端 (AURA) - 成为动态的“学习者”**

**目标:** 彻底移除所有前端硬编码的指令，使其完全依赖于从后端REST API获取的数据。

1.  **`src/features/command/api.ts` (数据获取):**
    *   **TDD先行:** 使用`msw`或类似的库，为`fetchCommands`编写测试。模拟`/api/v1/commands`端点的成功和失败响应，并断言`fetchCommands`能正确处理。
    *   **完善`fetchCommands()`:**
        *   确保它能正确地`fetch`数据，并将返回的JSON解析为`Command[]`类型。
        *   处理网络错误和非200状态码，在失败时抛出异常。

2.  **`src/features/command/hooks/useCommandLoader.ts` (数据应用):**
    *   **TDD先行:** 更新此Hook的测试，以反映新的逻辑。
    *   **实现逻辑:**
        *   在`useEffect`中调用`fetchCommands()`。
        *   在`try...catch`块中处理调用：
            *   **`try`块 (成功):** 调用`commandStore.setCommands(commandsFromApi)`。
            *   **`catch`块 (失败):** 调用`commandStore.setCommands(FALLBACK_COMMANDS)`。
        *   **创建`FALLBACK_COMMANDS`:** 在该文件顶部，定义一个最小化的应急指令列表（可以只包含`/help`和`/ping`），以增强系统韧性。

3.  **`src/features/command/store/commandStore.ts` (状态存储):**
    *   确保`availableCommands`的状态类型与`commands.types.ts`中的`Command`接口完全匹配。无需大的改动，但需进行一次审查。

#### **原则与规范**

*   **后端权威:** 任务完成后，AURA前端代码中**不应**再存在任何完整的、硬编码的指令列表（除了`useCommandLoader`中的应急Fallback列表）。
*   **TDD驱动:** 所有新增或修改的核心逻辑，都必须由先行编写的测试来驱动和验证。
*   **接口契约:** 后端`/api/v1/commands`端点返回的JSON结构，与前端`Command`类型定义，是本次任务的核心契约，必须严格保持一致。

---