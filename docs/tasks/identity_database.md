*   **全景上下文 (Big Picture Context):**
    *   **当前阶段:** 这是“主权个性化宇宙”架构的第一阶段。
    *   **本任务目标:** 建立以用户身份（`public_key`）为核心的数据隔离基础，并实现强制身份验证的“门禁”机制。此阶段专注于后端数据结构和核心服务逻辑的重构，为下一阶段的动态个性化（`DYNAMIC-PERSONALIZATION-1.0`）奠定基础。
    *   **预期产出:** 一个能够区分“访客”与“成员”身份，并确保“成员”的所有对话数据都严格与其身份绑定的后端系统。

---

#### **一、核心原则与指令**

1.  **代码清理:** **必须**移除所有与旧`session_id`相关的逻辑。所有数据表单中，使用`owner_key`作为唯一的用户身份标识符。**不保留**任何向后兼容的冗余字段或逻辑。
2.  **数据清理:** 按照指示，我们**不**进行任何数据迁移。这是一个破坏性变更，系统将在一个全新的、干净的数据模型上运行。
3.  **TDD强制:** 所有新增或修改的核心业务逻辑，**必须**由先行编写的、最初会失败的测试用例来驱动。

---

#### **二、实施路径与具体任务 (TDD-Driven)**

**Phase 1: 数据库与模型层重构 (Database & Model Layer Refactoring)**

1.  **TDD - 编写失败的测试:**
    *   **路径:** `tests/nexus/unit/services/database/providers/test_mongo_provider.py`
    *   **行动:**
        *   修改`test_insert_message_success`，使其断言被插入的文档**必须**包含`owner_key`字段。
        *   修改`test_get_messages_success`，使其断言`find`操作的查询条件是`{"owner_key": ...}`而不是`{"session_id": ...}`。
        *   编写新的测试`test_create_and_find_identity()`，用于验证`identities`集合的增查操作。

2.  **实施 - 让测试通过:**
    *   **`nexus/core/models.py`:**
        *   在`Message`模型中，**移除`session_id`字段**，**添加`owner_key: str`字段**。
    *   **`nexus/services/database/providers/mongo.py`:**
        *   在`__init__`和`connect`方法中，增加`self.identities_collection`的初始化，并在`public_key`上创建唯一索引。
        *   修改`insert_message`方法，使其接受并存储`owner_key`。
        *   修改`get_messages_by_session_id`方法，将其**重命名**为`get_messages_by_owner_key`，并修改查询逻辑，使其基于`owner_key`进行查找。
        *   新增`find_identity_by_public_key`和`create_identity`方法，用于操作`identities`集合。

---

**Phase 2: 身份服务层构建 (Identity Service Layer Construction)**

1.  **TDD - 编写失败的测试:**
    *   **路径:** `tests/nexus/unit/services/test_identity_service.py` (新建文件)
    *   **行动:**
        *   编写`test_get_identity_not_found()`，断言对一个不存在的`public_key`调用`get_identity`返回`None`。
        *   编写`test_create_identity_success()`，断言`create_identity`能成功在数据库中创建一条记录，并返回该记录。

2.  **实施 - 让测试通过:**
    *   **`nexus/services/identity.py` (新建文件):**
        *   创建`IdentityService`类。
        *   其`__init__`接收`db_service: DatabaseService`作为依赖。
        *   实现`get_identity(self, public_key: str)`方法，调用`db_service.find_identity_by_public_key`。
        *   实现`create_identity(self, public_key: str)`方法，调用`db_service.create_identity`。

---

**Phase 3: 核心服务层重构 (Core Services Refactoring)**

1.  **TDD - 编写失败的测试:**
    *   **路径:** `tests/nexus/integration/services/test_orchestrator_service.py`
    *   **行动:**
        *   编写新的集成测试`test_handle_new_run_for_unverified_user()`。模拟一个来自**未注册**公钥的`RUNS_NEW`事件，断言`Orchestrator`**不会**发布`CONTEXT_BUILD_REQUEST`，而是直接发布一个包含特定引导信息的`UI_EVENTS`事件。
        *   修改现有的`test_simple_dialogue_flow`，使其在启动时模拟一个**已注册**的公钥，并断言对话流程能正常继续。
    *   **路径:** `tests/nexus/integration/services/test_persistence_service.py`
    *   **行动:** 修改`test_persists_human_message_on_new_run`，断言被持久化的`Message`对象现在包含`owner_key`而不是`session_id`。

2.  **实施 - 让测试通过:**
    *   **`nexus/main.py`:**
        *   实例化`IdentityService`，并将其注入到`OrchestratorService`和`CommandService`的构造函数中。
    *   **`nexus/services/orchestrator.py` (`OrchestratorService`):**
        *   修改`__init__`以接收`identity_service`。
        *   重构`handle_new_run`方法，实现**“门禁”逻辑**：
            *   提取`public_key`。
            *   调用`identity_service.get_identity`。
            *   根据结果执行“访客流程”（发布引导消息并中断）或“成员流程”（继续发布`CONTEXT_BUILD_REQUEST`）。
    *   **`nexus/services/persistence.py` (`PersistenceService`):**
        *   修改所有`handle_*`方法，从传入的`Message`中提取`owner_key`，并将其用于创建新的、待持久化的`Message`对象。
    *   **`nexus/services/context.py` (`ContextService`):**
        *   将其`get_history`的调用，从基于`session_id`改为基于`owner_key`。

---

**Phase 4: 指令层适配 (Command Layer Adaptation)**

1.  **TDD - 编写失败的测试:**
    *   **路径:** `tests/nexus/integration/services/test_command_service.py`
    *   **行动:** 修改与`/identity`相关的测试。模拟执行`/identity`指令时，断言`IdentityService`的`create_identity`方法被调用。

2.  **实施 - 让测试通过:**
    *   **`nexus/commands/definition/identity.py`:**
        *   重构`execute`函数。它现在的主要职责是调用`IdentityService.get_or_create_identity`。
        *   `IdentityService`需要从`context['identity_service']`中获取。
    *   **`nexus/services/command.py` (`CommandService`):**
        *   确保`IdentityService`实例被正确地注入到传递给指令的`context`字典中。

---

**最终验收标准 (Acceptance Criteria):**

1.  所有旧的、与`session_id`相关的代码和数据库字段已被彻底清除。
2.  所有新增和修改的逻辑，都有对应的、通过的测试用例。
3.  一个来自未注册公钥的新WebSocket连接，在发送第一条消息后，会收到一条引导其执行`/identity`的系统消息，且不会触发任何后续的LLM或数据库历史查询操作。
4.  一个已注册的公钥，在执行`/identity`指令后，系统状态不变。
5.  一个已注册的公钥，在发送消息后，系统能够基于其`owner_key`正确地查询历史记录，并完成整个对话流程。