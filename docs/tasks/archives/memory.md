### **任务委托单：NEXUS-PERSISTENCE**

**致：** 工程师AI

**发令者：** “枢”，NEXUS项目首席AI架构师

**主题：** 实现NEXUS的长期记忆持久化系统

**任务ID：** `PERSISTENCE`

---

**指令头 (Preamble):**
你是一个顶级的Python后端工程师。你将严格遵循NEXUS项目的《编码圣约》。本次任务是为NEXUS引擎构建完整的长期记忆系统，你需要实现数据库的连接、消息的持久化写入，以及历史消息的读取功能。

---

#### **第一部分：任务目标 (Objective)**

你的任务是分三步，为NEXUS激活长期记忆：
1.  **数据库驱动实现**: 完整实现`MongoProvider`，使其能够连接到MongoDB并提供基本的CRUD操作。
2.  **持久化服务实现**: 完整实现`PersistenceService`。它将订阅`NexusBus`上的关键消息，并将它们异步地写入数据库。
3.  **上下文加载重构**: 重构`ContextService`，使其能够通过`PersistenceService`从数据库加载历史对话，以构建一个有记忆的上下文。

#### **第二部分：文件与核心指令 (Files & Core Instructions)**

你将按顺序对以下文件进行操作：

**1. 文件路径: `nexus/services/database/providers/base.py`**
*   **任务**: 定义数据库提供者的抽象基类。
*   **核心指令**: 创建一个`DatabaseProvider`抽象类，定义`connect`, `disconnect`, `insert_message`, `get_messages_by_session_id`等核心方法的接口。

**2. 文件路径: `nexus/services/database/providers/mongo.py`**
*   **任务**: 完整实现`MongoProvider`。
*   **核心指令**:
    *   创建`MongoProvider`类，继承`DatabaseProvider`。
    *   实现`connect`方法，使用`pymongo.MongoClient`连接到MongoDB。
    *   实现`insert_message`方法，将一个`Message`对象（序列化为字典）插入到`messages`集合中。
    *   实现`get_messages_by_session_id`方法，该方法接收`session_id`和`limit`作为参数，从数据库中查询、按`timestamp`降序排序，并返回最新的N条消息。

**3. 文件路径: `nexus/services/database/service.py`**
*   **任务**: 完整实现`DatabaseService`，作为数据库提供者的封装。
*   **核心指令**:
    *   在`__init__`中，根据配置实例化`MongoProvider`并调用其`connect`方法。
    *   提供`insert_message_async`和`get_history_async`等**异步**方法。这些方法内部应使用`asyncio.to_thread`来调用`MongoProvider`中**同步的**数据库操作方法，以避免阻塞事件循环。

**4. 文件路径: `nexus/services/persistence.py` (新文件)**
*   **任务**: 创建并实现`PersistenceService`。
*   **核心指令**:
    *   在`__init__`中，接收`DatabaseService`的实例。
    *   在`subscribe_to_bus`中，订阅所有需要被记录的主题，例如`Topics.RUNS_NEW`（记录初始Human消息）、`Topics.LLM_RESULTS`（记录AI的最终回复和工具调用意图）、`Topics.TOOLS_RESULTS`（记录工具结果）。
    *   为每个订阅的主题创建一个`handle_...`方法。这些方法会从接收到的`Message`中提取出需要被持久化的信息，构建一个新的`Message`对象，然后调用`database_service.insert_message_async`将其异步写入数据库。

**5. 文件路径: `nexus/services/context.py`**
*   **任务**: 重构`ContextService`以加载真实的历史记录。
*   **核心指令**:
    *   修改`__init__`，使其接收`PersistenceService`的实例。
    *   修改`handle_build_request`方法。在构建`messages`列表时，**替换掉原来的简化逻辑**。
    *   新的逻辑应该是：
        1.  调用`persistence_service.get_history(session_id, limit=...)`来从数据库获取最近的对话历史。
        2.  将这些历史消息与当前的`system_prompt`和`user_input`正确地组合成最终的`messages`列表。

**6. 文件路径: `nexus/main.py`**
*   **任务**: 更新引擎启动器，以初始化并注入新的持久化相关服务。
*   **核心指令**:
    *   在`main`函数中，正确地实例化`DatabaseService`和`PersistenceService`。
    *   将`database_service`实例注入到`PersistenceService`。
    *   将`persistence_service`实例注入到`ContextService`。
    *   确保所有服务的实例化顺序和依赖注入关系都正确无误。

---
**交付要求：**
你必须为上述6个文件，一次性生成它们各自更新后的完整代码。代码必须实现一个功能完整的、能够将对话写入数据库并能从数据库加载历史上下文的长期记忆系统。

**任务开始。**