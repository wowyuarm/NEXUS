### **任务委托单：NEXUS-AURA-CONTEXT-REVOLUTION**

**致：** 工程师AI

**发令者：** “枢”，NEXUS项目首席AI架构师

**主题：** 对NEXUS & AURA的上下文构建范式进行一次根本性革命

**任务ID：** `CONTEXT-REVOLUTION`

---

#### **一、 讨论背景与战略意图 (Background & Strategic Intent)**

我们经过深度讨论后发现，当前向LLM传递上下文的方式存在两个根本性缺陷：

1.  **缓存失效**: 在工具调用循环中，任何动态信息的注入（如时间戳）都会改变历史消息列表，导致LLM服务端的KV缓存失效，从而大幅降低多步推理的速度。
2.  **扩展性受限**: 将所有信息（人格、历史、动态情景）都扁平化地放入一个消息列表中，使得未来扩展新的动态信息（如用户情绪、地理位置）变得笨拙且缺乏结构。

因此，本次任务的**战略意含**是：我们要从根本上**重新定义“一次思考的上下文”**。我们将引入“**思考循环不变性**”和“**结构化情景输入**”两大核心原则，将我们的上下文构建能力，提升到一个全新的、更健壮、更具扩展性的范式。

#### **二、 权衡与最终方案选择 (Deliberation & Final Decision)**

我们权衡了多种方案，从简单的“列表中插入动态消息”到复杂的“元数据传递”。

最终，我们决定采纳一个兼具优雅、高效和强大扩展性的**最终方案**：

1.  **确立“思考循环” (The Thinking Loop)**: 将用户的每一次输入，视为一个独立的“思考循环”。**在此循环内部，System Prompt和历史消息列表必须是不可变的**，以最大限度地利用LLM缓存并保证逻辑的一致性。
2.  **结构化“即时情景” (Structured "Now")**: 所有在“思考循环”开始时需要注入的**动态信息**（如当前时间、用户位置等），以及用户本次的**输入**，将被组织成一个**结构化的XML格式字符串**。
3.  **最终组合**: 这个结构化的XML字符串，将作为**最后一条`HUMAN`角色消息的`content`**，被追加到不变的（System Prompt + 历史消息）列表之后，形成最终发送给LLM的完整上下文。

这个方案将“我是谁”（System Prompt）和“我感知到了什么”（XML情景），在语义和结构上都进行了完美的区分。

#### **三、 总体路径与探索指导 (Pathfinding & Exploration Guidance)**

这是一个涉及前后端协同的、影响深远的重构。你需要按照以下路径进行探索和实现：

**路径一：前端 - “感官”升级 (The Sensory Upgrade)**

*   **探索目标**: 让AURA前端能够捕获并传递“即时情景信息”。
*   **探索区域**:
    *   `aura/src/services/websocket/protocol.ts`
    *   `aura/src/features/chat/store/auraStore.ts`
    *   `aura/src/features/chat/store/__tests__/auraStore.test.ts`
*   **指导**:
    1.  **审查并扩展协议**: `ClientMessage`的`payload`需要被扩展，除了`content`，还必须包含一个`client_timestamp`字段（ISO 8601格式）。
    2.  **捕获时间**: 在`auraStore`的`sendMessage` action中，你需要获取**浏览器的当前时间**，并将其与用户输入一同打包，通过`websocketManager`发送。

**路径二：后端 - “认知”重构 (The Cognitive Reshape)**

*   **探索目标**: 重构`ContextService`，使其能够实现我们全新的上下文构建范式。
*   **探索区域**:
    *   `nexus/services/context.py`
    *   `tests/nexus/unit/services/test_context_service.py`
*   **指导**:
    1.  **解析新信息**: `WebsocketInterface`和`Orchestrator`需要能够正确地解析出`client_timestamp`，并将其传递给`ContextService`的`handle_build_request`。
    2.  **重构核心逻辑**: `ContextService._format_llm_messages`（或相关方法）需要被彻底重构。你需要探索如何实现以下逻辑：
        *   构建不变的“基础部分”（System Prompt + 历史消息）。
        *   从`client_timestamp`中，将其格式化为人类可读的北京时间字符串。
        *   使用XML标签（`<Context>`, `<Current_Time>`, `<Human_Input>`等）将动态信息和用户输入，组合成一个**单一的、结构化的字符串**。
        *   将这个字符串作为最后一条`user`消息的内容。

#### **四、 原则规范 (Governing Principles)**

1.  **测试驱动开发 (TDD) - 强制**:
    *   **你必须先从`tests/nexus/unit/services/test_context_service.py`开始。**
    *   **第一步**: 重写或创建一个新的测试用例，该用例需要**精确地断言**我们期望的、包含XML标签的最终`messages`列表结构。**你必须先让这个测试失败。**
    *   **第二步**: 再去修改`nexus/services/context.py`的生产代码，让这个测试通过。
    *   **第三步**: 最后进行重构。

2.  **架构纯粹性**:
    *   保持服务间的解耦。`ContextService`的变更不应影响`Orchestrator`的核心状态机逻辑。
    *   XML标签的设计应清晰、自解释。

#### **五、 涉及模块与文件 (Affected Modules & Files)**

*   **后端**:
    *   `nexus/services/context.py` (核心重构区)
    *   `nexus/interfaces/websocket.py` (可能需要微调以传递`client_timestamp`)
    *   `nexus/services/orchestrator.py` (同上)
    *   `tests/nexus/unit/services/test_context_service.py` (TDD的起点)
*   **前端**:
    *   `aura/src/services/websocket/protocol.ts` (协议扩展)
    *   `aura/src/features/chat/store/auraStore.ts` (捕获和发送时间)

---
**任务开始。请首先提交你的`IMPLEMENTATION_PLAN.md`草案。**

---
---

(修正) 将上下文时间戳处理升级为全球适用的UTC标准。你之前的`CONTEXT-REVOLUTION`任务已成功完成，但其中对时间的处理被硬编码为了“北京时间”。你的新任务是对该实现进行一次精炼，将其升级为一个处理标准化UTC时间的、全球适用的解决方案。

---

#### **一、 讨论背景与战略意图 (Background & Strategic Intent)**

我们认识到，将AI感知的时间硬编码为“北京时间”，与我们构建一个“以用户为中心”的系统的理念相悖。AI应该感知到用户设备所在的真实时间情景，而不是服务器的。

因此，本次修正的**战略意图**是：将系统的时间处理逻辑，从一个**特定区域的实现**，升级为一个**全球统一的、基于UTC标准的架构**，将时区转换的复杂性交由LLM根据上下文自主处理。

#### **二、 权衡与最终方案选择 (Deliberation & Final Decision)**

我们确认，前端通过`new Date().toISOString()`传递的**UTC时间戳**，是完美的、无损的信息源。后端的职责不是进行任何本地化转换，而是以一种清晰、无歧义的方式，将这个UTC时间呈现给LLM。

#### **三、 总体路径与探索指导 (Pathfinding & Exploration Guidance)**

这是一个目标极其明确的修正任务。你需要对`ContextService`的核心逻辑进行一次精准的修改。

**路径一：后端 - “认知”修正 (The Cognitive Refinement)**

*   **探索目标**: 修正`ContextService`中对客户端时间戳的处理方式。
*   **探索区域**:
    *   `nexus/services/context.py`
    *   `tests/nexus/unit/services/test_context_service.py`
*   **指导**:
    1.  **审查`_format_llm_messages`**: 找到你之前添加的、将`client_timestamp`格式化为北京时间的代码块。
    2.  **重构逻辑**:
        *   接收到的`client_timestamp`是一个ISO 8601格式的UTC字符串 (e.g., `"2025-09-17T01:16:03.123Z"`)。
        *   你需要使用Python的`datetime`库来解析这个字符串。
        *   然后，将其**重新格式化**为一个更简洁、但**依然保持UTC时区信息**的字符串。**推荐格式**: `YYYY-MM-DD HH:MM:SS UTC`。
        *   将这个新的UTC时间字符串，放入`<Current_Time>` XML标签中。

#### **四、 原则规范 (Governing Principles)**

1.  **测试驱动开发 (TDD) - 强制**:
    *   **你必须先从`tests/nexus/unit/services/test_context_service.py`开始。**
    *   **第一步**: 修改你之前编写的`test_formats_llm_messages_includes_beijing_timestamp`测试用例。将其重命名为`..._includes_utc_timestamp`。
    *   **第二步**: 修改测试中的“冻结时间”和**断言**。现在，它应该断言`content`中包含的是**格式化后的UTC时间字符串**，而不是北京时间。**让这个测试因为生产代码尚未修改而失败 (RED)。**
    *   **第三步**: 再去修改`nexus/services/context.py`，让测试通过 (GREEN)。
    *   **第四步**: 进行任何必要的重构 (REFACTOR)。

#### **五、 涉及模块与文件 (Affected Modules & Files)**

*   **后端**:
    *   `nexus/services/context.py` (核心修正区)
    *   `tests/nexus/unit/services/test_context_service.py` (TDD的起点)
*   **前端**:
    *   **无需任何修改。** 前端已经在了正确的轨道上。

---
**任务开始。请严格遵循TDD流程，首先提交你对测试文件的修改计划。**