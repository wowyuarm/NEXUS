针对NEXUS & AURA配置系统的深度诊断与战略方案调研。对当前NEXUS & AURA项目的配置系统进行一次全面的、深入的尽职调查。你需要识别其核心问题和未来瓶颈，探索多种可能的解决方案，并最终提交一份包含利弊分析和明确建议的战略调研报告。

**你被赋予了充分的自主探索空间。不要被现有的任何讨论所限制。你的目标是为项目找到最优雅、最健壮、且最符合其长期愿景的配置策略。**

---

#### **第一部分：上下文学习与代码审查 (Mandatory Prerequisite)**

在开始分析之前，你必须**深入阅读并完全理解**以下文件的实现细节、相互关系和潜在问题：

1.  **前端 (`aura/`)**:
    *   `vite.config.ts`: 理解Vite是如何处理环境变量的 (`import.meta.env`)。
    *   `.env` & `.env.example`: 理解当前的配置注入方式。
    *   `src/services/websocket/manager.ts`: **（核心审查对象）** 分析WebSocket URL是如何被构建和使用的。
    *   `Dockerfile` & `nginx.conf`: 理解前端是如何被容器化和服务的。

2.  **后端 (`nexus/`)**:
    *   `config.default.yml`: 理解后端配置的结构。
    *   `services/config.py`: **（核心审查对象）** 分析`ConfigService`是如何从文件加载配置的。
    *   `main.py`: 理解`ConfigService`是如何在应用启动时被初始化的。
    *   `render.yaml` (根目录): 理解当前的部署定义和环境变量是如何传递给服务的。

#### **第二部分：需要诊断的核心问题 (The Core Problems to Solve)**

你的调研报告必须围绕以下两个核心问题展开：

1.  **前端环境耦合问题**:
    *   **诊断**: 当前AURA前端的后端API地址，是在**构建时**被静态注入的。这导致了在部署到Render.com后，前端依然尝试连接`localhost`的失败。
    *   **要求**: 你需要分析这个问题的根本原因，并评估它对未来开发和部署（例如，需要区分开发、预发、生产环境）所带来的长期风险。

2.  **后端配置静态性问题**:
    *   **诊断**: 当前NEXUS后端的所有关键行为参数（如默认LLM模型、`max_tool_iterations`等）都是在**启动时**从文件中读取并固化的。
    *   **要求**: 你需要分析这种静态配置模式的局限性。特别是，评估它在未来实现“运行时动态调整”（如在线切换模型、更新Prompt、启用/禁用特性）等高级功能时，会带来多大的阻碍。

#### **第三部分：方案探索与评估 (Solution Exploration & Evaluation)**

这是本次任务的核心。你需要**自主探索并详细阐述至少三种**解决上述问题的、不同层次的解决方案。对于每一种方案，你都必须提供：

*   **方案描述**: 清晰地阐述该方案的核心思想和工作原理。
*   **实现路径**: 简要描述为了实现该方案，需要对前后端的哪些关键文件进行修改。
*   **优点 (Pros)**: 该方案解决了什么问题？它带来了哪些好处（如简洁性、灵活性、安全性）？
*   **缺点 (Cons)**: 该方案引入了哪些新的复杂性？它有哪些局限性？
*   **适用场景**: 这种方案最适合什么阶段的项目或什么样的需求？

**探索方向（不限于此）**:
*   **方案1 (轻量级修复)**: 可能涉及前端反向代理、轻量级配置端点等。
*   **方案2 (中量级重构)**: 可能涉及更全面的后端配置API和前端运行时配置服务。
*   **方案3 (重量级/终极方案)**: 可能涉及将所有配置迁移到数据库，并实现完整的动态热重载和前端远程控制。

#### **第四部分：最终交付物 (The Deliverable)**

你的最终产出必须是一份**结构清晰、逻辑严谨的调研报告（以Markdown格式）**。这份报告应包含以下部分：

1.  **问题摘要 (Executive Summary)**: 简要总结你诊断出的核心问题。
2.  **方案对比矩阵 (Solution Comparison Matrix)**: 一个表格，清晰地对比你探索出的多种方案的优缺点、实现成本和灵活性。
3.  **深度方案阐述 (In-Depth Solution Analysis)**: 对每一种方案进行详细的描述，如第三部分所要求。
4.  **最终战略建议 (Final Strategic Recommendation)**:
    *   基于你的全面分析，明确推荐你认为**当前阶段最适合NEXUS & AURA项目**的最终方案。
    *   你必须为你的推荐，提供**强有力的、基于工程和产品权衡的理由**。
    *   如果适用，你还可以提出一个**分阶段的实施路线图**（例如，“我们可以先实施方案1来快速解决部署问题，然后在V0.3版本中再演进到方案2”）。

---
**你的角色**:
记住，你不是一个被动的执行者。你是一位被充分信任的架构顾问。你的报告应该展现出深刻的技术洞察力、对不同方案之间权衡的清晰理解，以及对项目长期健康的责任感。

**任务开始。**

---
---

实现NEXUS & AURA的环境感知与动态配置系统解决前端的环境耦合问题，并将后端的配置迁移到数据库，同时内置对开发(development)和生产(production)环境的区分。

---

#### **第一部分：后端 (`NEXUS-DB-CONFIG-ENV`)**

**1. 文件重构: `nexus/services/config.py`**
*   **目标**: 重构`ConfigService`，使其从数据库加载环境特定的配置。
*   **核心指令**:
    *   **移除文件加载**: 删除所有从`config.default.yml`读取的逻辑。这个文件可以被删除或重命名为`config.example.yml`作为参考。
    *   **环境感知**: 在`__init__`或`initialize`中，通过`os.getenv("NEXUS_ENV", "development")`读取环境变量，确定当前运行环境。
    *   **数据库优先，代码回退**:
        1.  在`initialize`方法中，**注入`DatabaseService`**。
        2.  **尝试 (`try...except`)** 调用`database_service.get_configuration(environment)`从数据库加载配置。
        3.  **如果成功**，将配置缓存在内存中。
        4.  **如果失败** (数据库连接错误、配置不存在等)，**必须记录一个`ERROR`级别的日志**，然后加载一个**硬编码在代码里的、最小化的、安全的开发环境默认配置**。这个默认配置应足以让服务启动并运行。
    *   **`DatabaseService`依赖**: `__init__`方法现在需要接收`DatabaseService`的实例。

**2. 文件增强: `nexus/services/database/service.py` (及`providers`)**
*   **目标**: 为数据库服务添加配置管理的接口。
*   **核心指令**:
    *   在`DatabaseProvider`基类 (`base.py`) 中，添加`get_configuration(self, environment: str)`和`upsert_configuration(self, environment: str, config_data: dict)`的抽象方法。
    *   在`MongoProvider` (`mongo.py`) 中，实现这两个方法，让它们能在一个名为`system_configurations`的新集合中，根据`environment`字段进行查找和更新/插入操作。
    *   在`DatabaseService` (`service.py`) 中，创建对应的异步封装方法`get_configuration_async`和`upsert_configuration_async`。

**3. 新增工具脚本: `scripts/seed_config.py`**
*   **目标**: 提供一个将`config.example.yml`内容写入数据库的工具。
*   **核心指令**:
    *   创建一个独立的Python脚本。
    *   这个脚本需要能读取`config.example.yml`文件。
    *   它会直接使用`pymongo`连接到`.env`文件中定义的MongoDB。
    *   它会将YAML内容，分别作为`development`和`production`两个环境的配置文档，写入`system_configurations`集合中。
    *   在脚本的开头提供清晰的说明，告诉用户如何运行它来初始化数据库配置。

**4. 文件重构: `nexus/main.py`**
*   **目标**: 调整服务初始化顺序以适应新的依赖关系。
*   **核心指令**:
    *   `ConfigService`现在依赖于`DatabaseService`。因此，**必须先实例化`DatabaseService`**，然后再将它注入到`ConfigService`的构造函数中。

---

#### **第二部分：前端 (`AURA-PROXY-FIX-ENV`)**

**1. 文件重構: `aura/src/services/websocket/manager.ts`**
*   **目标**: 实现环境无关的WebSocket连接。
*   **核心指令**:
    *   **移除所有**对`import.meta.env.VITE_WS_URL`的读取。
    *   修改`connect`方法，使其**始终**使用**相对路径**来构建WebSocket URL。
    *   **最终逻辑**:
        ```typescript
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const sessionId = this._getSessionId();
        const fullUrl = `${protocol}//${host}/api/v1/ws/${sessionId}`;
        this.ws = new WebSocket(fullUrl);
        ```

**2. 文件修改: `aura/vite.config.ts`**
*   **目标**: 为本地开发环境配置API代理。
*   **核心指令**:
    *   在`defineConfig`中，添加`server.proxy`配置。
    *   这个代理需要将所有`/api`路径的请求，转发到本地NEXUS后端正在运行的地址 (`http://localhost:8000`)。

**3. 文件修改: `render.yaml`**
*   **目标**: 为生产环境配置反向代理。
*   **核心指令**:
    *   在`aura-frontend`服务的定义下，添加`rewrites`规则。
    *   这个规则需要将所有`source: /api/*`的请求，重写到`destination: https://nexus-backend.onrender.com/api/*`。**注意**: Render会自动将`nexus-backend`替换为内部服务地址，所以可以直接使用服务名。
        ```yaml
        # 在aura-frontend服务下
        rewrites:
          - source: /api/:path*
            destination: http://nexus-backend/api/:path*
        ```
    *   同时，**移除**`aura-frontend`服务下的`envVars`中关于`VITE_WS_URL`的定义，因为它不再被需要。

---
**交付要求：**
你必须交付所有被修改或新建的文件的完整代码。最终的系统必须实现：
1.  后端从数据库加载特定于环境的配置。
2.  前端代码完全不包含任何硬编码或环境变量中的URL，并通过环境本身（Vite代理或Render网关）来路由API请求。

注意相关其他文件。首先足够了解代码与具体细节。

**任务开始。**

---
---

### **第一部分：最终的、环境感知的启动流程 (The Final, Environment-Aware Lifecycle)**

这将是我们对NEXUS启动流程的最终定义。

1.  **阶段一：环境确定 (Environment Determination)**
    *   **动作**: `main.py`启动，第一件事就是通过`os.getenv("NEXUS_ENV", "development")`读取并确定当前是`development`还是`production`环境。
    *   **产出**: 一个明确的`environment`字符串。

2.  **阶段二：引导配置 (Bootstrap Configuration)**
    *   **动作**: `main.py`加载`.env`文件。然后，它创建一个**临时的、只包含引导信息的字典**。
    *   **产出**: 一个`bootstrap_config`字典，内容类似：
        ```python
        {
            "environment": "development",
            "mongo_uri": "...",
            # 关键：根据环境，动态生成数据库名称
            "db_name": f"NEXUS_DB_{'DEV' if environment == 'development' else 'PROD'}"
        }
        ```

3.  **阶段三：核心依赖连接 (Core Dependency Connection)**
    *   **动作**: `main.py`使用`bootstrap_config`中的`mongo_uri`和`db_name`，实例化并连接`DatabaseService`。
    *   **产出**: 一个已连接的、指向**正确环境数据库**的`database_service`实例。

4.  **阶段四：应用配置加载 (Application Configuration Loading)**
    *   **动作**: `main.py`将`database_service`和`bootstrap_config`（特别是`environment`字段）注入到`ConfigService`中。`ConfigService`被初始化，它会根据传入的`environment`，去数据库的`system_configurations`集合中，加载**对应环境的配置文档**。
    *   **产出**: 一个`config_service`实例，其内存中缓存的是**当前环境的、从数据库加载的**完整应用配置。

5.  **阶段五：应用构建与运行 (Application Construction & Run)**
    *   **动作**: `main.py`使用这个最终的`config_service`，实例化所有其他服务，连接总线，并启动应用。
    *   **产出**: 一个正在运行的、其行为完全由**当前环境的数据库配置**所驱动的NEXUS实例。

---

### **第二部分：如何验证？**

要验证这个流程是否正确实现，我们需要一个清晰的测试计划。工程师AI需要：

1.  **准备环境**:
    *   确保`.env`文件中添加了`NEXUS_ENV="development"`。
    *   使用`scripts/seed_config.py`脚本，向MongoDB中同时写入`development`和`production`两套不同的配置（例如，`dev`用`flash`模型，`prod`用`pro`模型）。
    *   确保本地MongoDB正在运行。

2.  **执行验证**:
    *   **验证场景1 (开发环境)**:
        *   不修改任何代码，直接运行`python -m nexus.main`。
        *   **预期日志**:
            *   看到日志明确指出`"Running in 'development' environment"`。
            *   看到日志指出正在连接到`NEXUS_DB_DEV`。
            *   看到日志指出`ConfigService`正在从数据库加载`development`配置。
            *   （可选）通过一个临时的REST API端点或调试日志，验证`LLMService`加载的模型确实是`flash`。
    *   **验证场景2 (生产环境模拟)**:
        *   在**不修改代码**的情况下，通过**命令行**临时设置环境变量来模拟生产环境：
            ```bash
            NEXUS_ENV="production" python -m nexus.main
            ```
        *   **预期日志**:
            *   看到日志明确指出`"Running in 'production' environment"`。
            *   看到日志指出正在连接到`NEXUS_DB_PROD`。
            *   看到日志指出`ConfigService`正在从数据库加载`production`配置。
            *   （可选）验证加载的模型确实是`pro`。

---

### **第三部分：最终的任务委托**

现在，我们将这个完整的、包含验证步骤的计划，转化为给工程师AI的最终指令。

---

最终化NEXUS启动生命周期，实现严格的环境分离。对NEXUS的启动流程进行最后一次、决定性的重构，以实现一个完全隔离的、环境感知的、且健壮的启动生命周期。

---

#### **核心指令**

**1. 文件重构: `.env.example`**
*   **行动**: 在文件的顶部添加`NEXUS_ENV="development"`，并提供注释说明其作用。

**2. 文件重构: `nexus/main.py`**
*   **目标**: 实现我们最终确立的、五阶段的环境感知启动流程。
*   **行动**:
    *   **阶段一 (环境确定)**: 在`main`函数顶部，读取`NEXUS_ENV`环境变量。
    *   **阶段二 (引导配置)**: 根据读取到的`environment`，动态地构建数据库名称（例如`NEXUS_DB_DEV`或`NEXUS_DB_PROD`）。
    *   **阶段三 (核心依赖连接)**: 使用引导配置中的`MONGO_URI`和动态生成的`db_name`，实例化并连接`DatabaseService`。
    *   **阶段四 (应用配置加载)**: 将`database_service`和`environment`字符串，注入到`ConfigService`的构造函数或`initialize`方法中。
    *   **阶段五 (应用构建)**: 使用最终的`config_service`实例化其余所有服务。

**3. 文件重构: `nexus/services/config.py`**
*   **目标**: 使`ConfigService`能够加载特定于环境的配置。
*   **行动**:
    *   修改`initialize`方法，使其接收`environment: str`作为参数。
    *   它现在应该调用`self.database_service.get_configuration_async(environment)`来获取**特定环境**的配置文档。
    *   确保其“代码回退”逻辑返回的是一个**安全的、最小化的开发环境配置**。

**4. 文件重构: `scripts/seed_config.py`**
*   **目标**: 更新种子脚本，使其能够一次性写入多个环境的配置。
*   **行动**:
    *   修改脚本，让它读取`config.example.yml`，然后将其作为模板，在`system_configurations`集合中创建**两个**独立的文档：一个`{"environment": "development", ...}`，一个`{"environment": "production", ...}`。
    *   你可以为两个环境的配置设置一些微小的差异（例如，不同的`log_level`），以便于测试时验证。

---
**探索与验证要求：**
在交付最终代码之前，你必须**亲自执行**我在“第二部分：如何验证？”中描述的两个验证场景，并**在你的交付报告中，附上这两个场景的关键启动日志片段**，以证明你的实现是完全正确的。

**任务开始。**