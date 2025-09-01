### **任务委托单：NEXUS-V0.2.3-TASK-003 (补充任务)**

**致：** 工程师AI

**发令者：** “枢”，NEXUS项目首席AI架构师

**主题：** 集成`ConfigService`并重构服务初始化流程

**任务ID：** `NEXUS-V0.2.3-TASK-003`

---

**指令头 (Preamble):**
你是一个顶级的Python后端工程师。你将严格遵循NEXUS项目的《编码圣约》。本次任务是对现有代码的重构，目的是将硬编码的配置项（如API密钥、模型名称）替换为通过统一的`ConfigService`进行管理。

---

#### **第一部分：任务目标 (Objective)**

你的任务是创建并集成一个`ConfigService`，该服务负责从`.env`和`config.default.yml`文件(首先读取config文件，这个文件主要用来配置一些与功能相关的设置，包括但不限于llm的提供商、模型的选择、温度与输出token长度等；还有未来的比如database、embedding、工具调用循环次数即最大agent循环数等等等）中加载所有配置。然后，你需要重构`main.py`和相关的服务（如`LLMService`），让它们从`ConfigService`中获取所需的配置，而不是在代码中硬编码。

#### **第二部分：文件与核心指令 (Files & Core Instructions)**

**1. 新文件创建: `nexus/services/config.py`**
*   **任务**: 创建`ConfigService`类。
*   **核心指令**:
    *   这个类应该能读取根目录下的`config.default.yml`和`.env`文件。
    *   它需要一个`initialize()`方法来执行加载和解析。
    *   它需要一个`get(key: str, default: Any = None)`方法，允许通过点分路径（如`llm.providers.google.model`）来获取配置项。
    *   它应该能解析`${VAR_NAME}`这样的环境变量占位符。

**2. 文件重构: `nexus/services/llm/service.py`**
*   **任务**: 重构`LLMService`以使用`ConfigService`。
*   **核心指令**:
    *   修改`__init__`方法，使其接收`ConfigService`的实例：`__init__(self, bus: NexusBus, config_service: ConfigService)`。
    *   在`__init__`中，通过调用`config_service.get(...)`来获取`api_key`, `base_url`, `model`等信息，并用这些信息来实例化`GoogleLLMProvider`。

**3. 文件重构: `nexus/main.py`**
*   **任务**: 重构引擎启动器以支持`ConfigService`。
*   **核心指令**:
    *   在`main`函数的一开始，**首先**实例化并初始化`ConfigService`:
        ```python
        config_service = ConfigService()
        config_service.initialize()
        ```
    *   修改所有服务（如`LLMService`）的实例化过程，将`config_service`实例传递给它们的构造函数。
    *   修改`uvicorn.run`的`host`和`port`，让它们也从`config_service`中读取，从而使端口可配置。

---
**交付要求：**
你必须生成`nexus/services/config.py`的完整代码，并提供`nexus/services/llm/service.py`和`nexus/main.py`两个文件重构后的完整代码。重构后的代码必须完全解耦配置，且功能与之前保持一致。

**任务开始。**