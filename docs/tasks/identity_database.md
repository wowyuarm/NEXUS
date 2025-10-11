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

---
---

*   **全景上下文 (Big Picture Context):**
    *   **前置任务:** `DATA-SOVEREIGNTY-1.0`已完成，我们拥有了以`owner_key`为基础的数据隔离和身份验证“门禁”。
    *   **本任务目标:** 在此基础上，激活系统的“个性化灵魂”。我们将实现“继承与覆写”的动态配置模型，并引入“模型即服务商”的抽象，最终让系统的每一次响应都能精确地反映当前用户的个人偏好和专属人格。
    *   **预期产出:** 一个完全动态的后端系统。不同的用户，可以拥有不同的AI人格（Prompts）和AI引擎（模型、参数），并且这些配置都持久化在数据库中，与他们的身份绑定。

---

#### **第一部分：架构背景与最终设计**

**1. 核心原则:**
*   **继承与覆写:** 系统的生效配置，是在请求生命周期中，由“全局创世模板”和“用户个性化覆写”实时合成的。
*   **模型即服务商:** 用户只与“模型（Model）”交互。系统内部负责将模型名解析为其对应的服务商（Provider）和认证信息。

**2. 最终数据模型 (The Final Data Schema):**
*   **`configurations` 集合 (单一文档，创世模板):**（**重要**：其他配置见根目录config.example.yml）
    ```json
    {
      "system": { /* 不可覆写 */ },
      "llm": {
        "catalog": {
          "gemini-2.5-flash": { "provider": "google" },
          "deepseek-chat": { "provider": "deepseek" },
          "kimi-k2": { "provider": "openrouter" }
        },
        "providers": {
          "google": { "api_key": "${GEMINI_API_KEY}", ... },
          "deepseek": { "api_key": "${DEEPSEEK_API_KEY}", ... }
        }
      },
      "user_defaults": {
        "config": {
          "model": "gemini-2.5-flash",
          "temperature": 0.8
        },
        "prompts": { # 必须见nexus/prompt/xi下的 markdown，合理迁移
          "persona": "You are Nexus...",
          "system": "You must operate...",
          "tools": "You have access..."
        }
      },
      "ui_editable_fields": { /* UI渲染元数据 */ }
    }
    ```
*   **`identities` 集合 (每个用户一个文档):**
    ```json
    {
      "public_key": "0x...",
      "config_overrides": {
        "model": "deepseek-chat" 
      },
      "prompt_overrides": {
        "persona": "我是曦..."
      }
    }
    ```

---

#### **第二部分：实施路径与TDD强制任务**

**Phase 1: `ConfigService` 与 `IdentityService` 的能力升级**

1.  **TDD - 编写失败的测试:**
    *   **路径:** `tests/nexus/unit/services/test_config_service.py`
        *   **行动:** 编写测试，模拟加载上述新的`configurations`数据结构，断言`ConfigService`能够正确解析并提供`llm.catalog`和`user_defaults`。
    *   **路径:** `tests/nexus/unit/services/test_identity_service.py`
        *   **行动:** 增强`test_create_identity_success`。现在，它必须断言新创建的`identity`文档中，`config_overrides`和`prompt_overrides`字段被初始化为空对象`{}`。

2.  **实施 - 让测试通过:**
    *   **`nexus/services/config.py` (`ConfigService`):**
        *   修改其加载逻辑，以适应新的、统一的`configurations`集合。
        *   提供新的getter方法，如`get_llm_catalog()`和`get_user_defaults()`。
    *   **`nexus/services/identity.py` (`IdentityService`):**
        *   修改`create_identity`方法。在创建新用户时，为其文档初始化`config_overrides: {}`和`prompt_overrides: {}`字段。

---

**Phase 2: 核心服务 (`ContextService`, `LLMService`) 的动态化革命**

1.  **TDD - 编写失败的测试:**
    *   **路径:** `tests/nexus/integration/services/test_context_service.py`
        *   **行动:** 编写一个新的集成测试`test_context_composition_with_overrides()`。模拟一个拥有`prompt_overrides`的用户，断言`ContextService`最终生成的System Prompt**包含了**被覆写后的`persona`。
    *   **路径:** `tests/nexus/integration/services/test_llm_service.py`
        *   **行动:** 编写一个新的集成测试`test_llm_service_dynamic_provider_selection()`。模拟一个`config_overrides`中`model`为`deepseek-chat`的用户，断言`LLMService`在处理其请求时，**实例化了`DeepSeekLLMProvider`**，而不是默认的`GoogleLLMProvider`。

2.  **实施 - 让测试通过:**
    *   **`nexus/services/context.py` (`ContextService`):**
        *   **核心改造:** 重构`handle_build_request`和`_load_system_prompt`（或新增`_compose_effective_prompts`方法）。
        *   **新流程:**
            1.  从`Orchestrator`传来的`user_profile`中，获取`prompt_overrides`。
            2.  从`ConfigService`获取`user_defaults.prompts`作为基础。
            3.  **实时合并:** 用`prompt_overrides`覆写基础Prompt，生成最终的`effective_prompts`。
            4.  将`effective_prompts`中的`persona`, `system`, `tools`等部分拼接成最终的System Prompt字符串。
    *   **`nexus/services/llm.py` (`LLMService`):**
        *   **核心改造:** 重构`_initialize_provider`方法，将其更名为`_get_provider_for_model`，并接收`model_name`作为参数。`__init__`中不再实例化任何默认provider。
        *   **重构`handle_llm_request`:**
            1.  从`Orchestrator`传来的`user_profile`和`user_defaults`合成出`effective_config`。
            2.  从`effective_config`中获取最终的`model`名。
            3.  调用`self._get_provider_for_model(model)`**实时地、为本次请求**实例化一个正确的Provider。
            4.  使用这个临时的Provider实例，执行LLM调用。

---

#### **第三部分：代码清理与正规化**

*   **废除旧逻辑:**
    *   **必须**移除`ContextService`中所有从本地文件系统 (`nexus/prompts/`) 加载`.md`文件的逻辑。代码Fallback机制应由`ConfigService`统一管理。
*   **统一`owner_key`:**
    *   对整个后端代码库进行一次最终审查，确保所有数据库交互、服务间数据传递，都已彻底摒弃`session_id`，完全统一到`owner_key`。

#### **验收标准**

1.  所有相关的测试文件均已创建或更新，并且所有测试用例100%通过。
2.  新用户通过`/identity`验证后，其在`identities`集合中的文档被正确创建，并包含空的`overrides`字段。
3.  该新用户发起对话时，系统使用的是`configurations`集合中定义的默认“枢 (Nexus)” Prompt和默认模型。
4.  当通过数据库手动为该用户添加`config_overrides`（例如，将`model`改为`deepseek-chat`）后，该用户再次发起对话，后端日志必须明确显示系统**实例化了`DeepSeekLLMProvider`**来处理该请求。
5.  当通过数据库手动为该用户添加`prompt_overrides`（例如，修改`persona`为“曦”）后，该用户再次发起对话，LLM接收到的System Prompt必须包含“曦”的文本。

---