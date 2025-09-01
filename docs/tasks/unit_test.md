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