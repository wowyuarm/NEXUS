#### **第一部分：准备工作 (Setup)**

在开始编码前，你需要确保我们的测试环境已经准备就绪。

1.  **创建测试目录结构**:
    *   在`NEXUS/`根目录下，创建以下目录结构：
        ```
        /tests/
        └── unit/
            ├── services/
            └── tools/
        ```
    *   并在每个新创建的目录中都创建一个空的`__init__.py`文件，使其成为可识别的包。

2.  **更新`requirements.txt`**:
    *   在`NEXUS/requirements.txt`文件的末尾，添加以下测试专用的依赖：
        ```txt
        
        # Testing
        pytest
        pytest-asyncio
        pytest-mock
        ```
    *   然后，在你的虚拟环境中执行`pip install -r requirements.txt`来安装它们。

#### **第二部分：任务目标 (Objective)**

你的任务是为以下两个核心工具模块编写全面的单元测试：
1.  **`ConfigService`**: 验证它能正确地加载、解析和提供配置。
2.  **`ToolRegistry`**: 验证它能正确地、自动化地发现和注册工具。

#### **第三部分：文件与核心指令 (Files & Core Instructions)**

你将按顺序创建以下两个新的测试文件：

**1. 新文件: `tests/unit/services/test_config_service.py`**
*   **任务**: 编写`ConfigService`的单元测试。
*   **核心指令**:
    *   你需要使用`pytest`的`fixture`来创建一个临时的、假的`.env`文件和`config.default.yml`文件（可以使用`tmp_path` fixture）。这确保了测试的独立性和可重复性。
    *   **测试用例应覆盖**:
        1.  **成功初始化**: 测试`initialize()`方法在文件存在时能成功执行。
        2.  **获取简单值**: 测试`get('system.log_level')`能返回正确的值。
        3.  **获取嵌套值**: 测试`get('llm.providers.google.model')`能返回正确的嵌套值。
        4.  **环境变量替换**: 测试`get('llm.providers.google.api_key')`返回的是`.env`文件中的值，而不是`${GEMINI_API_KEY}`这个占位符。
        5.  **默认值返回**: 测试当一个键不存在时，`get('non.existent.key', 'default_value')`能正确返回`default_value`。
        6.  **文件未找到异常**: 测试当配置文件不存在时，`initialize()`会抛出`FileNotFoundError`。

**2. 新文件: `tests/unit/tools/test_tool_registry.py`**
*   **任务**: 编写`ToolRegistry`的单元测试。
*   **核心指令**:
    *   你需要使用`mocker` (`pytest-mock`) fixture来模拟`importlib`和`pkgutil`的行为，以避免测试依赖于真实的文件系统结构。
    *   **测试用例应覆盖**:
        1.  **空注册表**: 测试一个新的`ToolRegistry`实例，其工具列表为空。
        2.  **手动注册成功**: 测试`register()`方法能成功添加一个工具，并且之后可以通过`get_...()`方法取回。
        3.  **自动发现与注册**:
            *   **（核心测试）** 模拟`pkgutil.iter_modules`和`importlib.import_module`。让它们返回一个假的模块，这个假模块中包含一个`_TOOL`结尾的字典和一个同名的函数。
            *   调用`discover_and_register()`。
            *   断言该工具是否被成功注册。
        4.  **自动发现无效模块**: 模拟一个模块，其中只有`_TOOL`字典但没有对应的函数，断言`ToolRegistry`会记录一个警告并且**不会**注册该工具。
        5.  **获取所有定义**: 测试`get_all_tool_definitions()`返回的列表是否包含了所有已注册工具的元数据。

---
**交付要求：**
你必须：
1.  提供`tests/unit/services/test_config_service.py`的完整代码。
2.  提供`tests/unit/tools/test_tool_registry.py`的完整代码。

代码必须遵循`pytest`的最佳实践，包含清晰的测试函数命名（如`test_...`），并使用`assert`语句进行断言。

**任务开始。**

---
---

好的，禹。

我们正式进入 **NEXUS-HARDENING** 阶段的核心——**服务级集成测试**。

现在，我们将为NEXUS的“大脑”和“记忆中枢”——`OrchestratorService`和`PersistenceService`——编写集成测试。这将是我们对系统核心逻辑最严格、最全面的一次考验。

---

为Orchestrator和Persistence服务编写集成测试，使用`pytest`为复杂的异步、事件驱动系统编写集成测试。你将使用`pytest-mock`来模拟服务间的依赖（特别是`NexusBus`），以隔离被测服务并精确断言其行为。

---

#### **第一部分：准备工作 (Setup)**

1.  **创建测试目录**:
    *   在`tests/`目录下，创建`integration/`目录。
    *   在`tests/integration/`目录下，创建`services/`目录。
    *   并在每个新目录中创建空的`__init__.py`文件。

#### **第二部分：任务目标 (Objective)**

你的任务是为以下两个核心服务编写全面的集成测试：
1.  **`PersistenceService`**: 验证它是否能正确地订阅`NexusBus`上的事件，并调用`DatabaseService`进行持久化。
2.  **`OrchestratorService`**: 验证其核心状态机在各种场景下（简单对话、单工具、多工具同步）是否能正确地发布事件和转换状态。

#### **第三部分：文件与核心指令 (Files & Core Instructions)**

你将按顺序创建以下两个新的测试文件：

**1. 新文件: `tests/integration/services/test_persistence_service.py`**
*   **任务**: 编写`PersistenceService`的集成测试。
*   **核心指令**:
    *   **Setup**: 在测试函数中，你需要`mocker.patch`一个`DatabaseService`的模拟实例。这个模拟实例需要有一个可供断言的`insert_message_async`方法。
    *   **测试用例应覆盖**:
        1.  **`test_persists_human_message_on_new_run`**:
            *   创建一个`PersistenceService`实例，注入模拟的`DatabaseService`。
            *   模拟一个`RUNS_NEW`主题的`Message`（其`content`是一个`Run`对象）。
            *   调用`persistence_service.handle_new_run()`。
            *   **断言**: `database_service.insert_message_async`被调用了一次，并且被调用的`Message`对象的`role`是`HUMAN`。
        2.  **`test_persists_ai_message_on_llm_result`**:
            *   模拟一个`LLM_RESULTS`主题的`Message`。
            *   调用`persistence_service.handle_llm_result()`。
            *   **断言**: `database_service.insert_message_async`被调用，且`Message`的`role`是`AI`。
        3.  **`test_persists_tool_message_on_tool_result`**:
            *   模拟一个`TOOLS_RESULTS`主题的`Message`。
            *   调用`persistence_service.handle_tool_result()`。
            *   **断言**: `database_service.insert_message_async`被调用，且`Message`的`role`是`TOOL`。

**2. 新文件: `tests/integration/services/test_orchestrator_service.py`**
*   **任务**: 编写`OrchestratorService`的核心集成测试。
*   **核心指令**:
    *   **Setup**: 在每个测试函数中，你需要`mocker.patch`一个`NexusBus`的模拟实例和一个`ConfigService`的模拟实例。`mock_bus`是断言的关键。
    *   **测试用例应覆盖**:
        1.  **`test_simple_dialogue_flow`**:
            *   **Act**: 模拟`RUNS_NEW`事件，调用`handle_new_run`。
            *   **Assert**: 断言`mock_bus.publish`被调用，主题是`Topics.CONTEXT_BUILD_REQUEST`。
            *   **Act**: 模拟`CONTEXT_BUILD_RESPONSE`事件，调用`handle_context_ready`。
            *   **Assert**: 断言`mock_bus.publish`被调用，主题是`Topics.LLM_REQUESTS`。
            *   **Act**: 模擬`LLM_RESULTS`事件（不带`tool_calls`），调用`handle_llm_result`。
            *   **Assert**: 断言`mock_bus.publish`被调用，主题是`Topics.UI_EVENTS`，并且`event`类型是`text_chunk`和`run_finished`。
        2.  **`test_single_tool_call_flow`**:
            *   在前一个测试的基础上，当模拟`LLM_RESULTS`事件时，让它**包含一个`tool_calls`**。
            *   **Assert**: 断言`mock_bus.publish`被调用，主题是`Topics.TOOLS_REQUESTS`。
            *   **Act**: 模拟`TOOLS_RESULTS`事件，调用`handle_tool_result`。
            *   **Assert**: 断言`mock_bus.publish`再次被调用，主题是`Topics.LLM_REQUESTS`（形成循环）。
        3.  **`test_multi_tool_synchronization_flow` (关键测试)**:
            *   模拟一个包含**两个`tool_calls`**的`LLM_RESULTS`事件，并调用`handle_llm_result`。
            *   **Assert**: `Orchestrator`的`active_runs`中对应`Run`的`pending_tool_calls`元数据被设为`2`。
            *   **Act**: 模拟**第一个**`TOOLS_RESULTS`事件，并调用`handle_tool_result`。
            *   **Assert**: `pending_tool_calls`变为`1`，并且`mock_bus.publish`**没有**被调用以再次请求LLM。
            *   **Act**: 模拟**第二个**`TOOLS_RESULTS`事件，并调用`handle_tool_result`。
            *   **Assert**: `pending_tool_calls`变为`0`，并且`mock_bus.publish`**现在**被调用了，主题是`Topics.LLM_REQUESTS`。

---
**交付要求：**
你必须：
1.  提供`tests/integration/services/test_persistence_service.py`的完整代码。
2.  提供`tests/integration/services/test_orchestrator_service.py`的完整代码。

代码必须使用`pytest`和`pytest-mock`，并能清晰、准确地验证服务的核心交互逻辑。所有异步测试函数都应使用`async def`并由`pytest-asyncio`处理。

**任务开始。**

---
---

编写带隔离数据库环境的端到端WebSocket交互测试。编写一个端到端测试，该测试必须在一个**完全隔离的数据库环境**中运行，以确保测试不会污染生产数据且结果可重复。

---

#### **核心指令**

你将创建`tests/e2e/test_full_interaction_flow.py`文件。其中的**核心变化**在于`nexus_service`这个fixture的设计。

**1. `tests/conftest.py` (可选，但推荐)**
*   为了让fixture可重用，建议在`tests/`目录下创建一个`conftest.py`文件，并将`nexus_service` fixture放在这里。
*   **任务**: 创建一个`pytest` fixture，它将负责**在启动NEXUS服务前，动态修改其配置**。

**2. `nexus_service` Fixture的实现逻辑**
*   **使用`pytest`的`monkeypatch` fixture**。
*   **步骤**:
    1.  **定义一个临时的数据库名称**，例如 `test_nexus_db_{uuid.uuid4().hex}`。这确保了每次`pytest`运行都使用一个全新的、不会冲突的数据库。
    2.  **“劫持”`ConfigService.get`方法**:
        *   使用`monkeypatch.setattr('nexus.services.config.ConfigService.get', new_get_method)`。
        *   你需要编写一个新的`new_get_method`函数。这个函数会检查被请求的`key`：
            *   如果`key`是`'database.db_name'`，它就**强制返回我们上面定义的临时数据库名称**。
            *   对于所有其他`key`，它就调用`ConfigService`原始的`get`方法，以加载`.env`中的真实API密钥等。
    3.  **启动NEXUS服务**: 现在，当你启动`nexus.main.main()`时，`DatabaseService`在初始化时调用`config_service.get('database.db_name')`，将会被我们的补丁“欺骗”，从而连接到那个临时的测试数据库。
    4.  **`yield`** 控制权给测试用例。
    5.  **销毁 (Teardown)**: 在测试结束后，fixture需要连接到MongoDB，**将那个临时的数据库彻底删除** (`mongo_client.drop_database(...)`)，确保不留下任何测试垃圾。

**3. `test_tool_call_interaction`测试用例**
*   这部分的逻辑保持不变。它将在这个被动态注入了隔离环境的、正在运行的NEXUS服务上，执行我们之前定义的所有连接、发送、收集和断言操作。

---
**交付要求：**
你必须提供：
1.  （可选但推荐）`tests/conftest.py`文件，包含实现了**动态环境注入**和**自动清理**的`nexus_service` fixture的完整代码。
2.  `tests/e2e/test_full_interaction_flow.py`文件，其中包含使用该fixture并执行完整交互测试的`test_tool_call_interaction`用例的完整代码。

最终的实现必须确保，运行`pytest`时，系统会自动连接到一个临时的、唯一的测试数据库，并在测试结束后将其彻底清除，对生产数据库的**影响为零**。

**任务开始。**