# NEXUS

> An event-driven memory-centered chatbot, built as a learning experiment in
> agent infrastructure: how memory, context, tools, and runtime should be
> organized when "the chatbot" is treated as a small living system instead of
> a stateless API wrapper.

NEXUS 由两部分组成：

- **NEXUS** — Python / FastAPI 后端，事件驱动 runtime；
- **AURA** — React 19 + TypeScript + Vite 前端，灰度极简交互。

整个项目是一次围绕**长期记忆 + 多层上下文 + 事件总线**的全栈实验，
而不是一个面向终端用户的产品。

---

## Why NEXUS

主流 chatbot 实现往往是：

```
HTTP request → load history → call LLM → return text
```

历史是一坨字符串、记忆是一锅 embedding、工具调用混在 prompt 里。
项目越长越乱，行为越来越难解释。

NEXUS 的出发点正相反：把 chatbot 视为一个**有结构、有节律、可观测**
的小型系统，从一开始就把以下问题分开建模：

- 记忆：短期上下文窗口、长期特征、reflection 摘要、关于用户的画像
- 上下文：每个 turn 实际进入 prompt 的多层信息（capabilities / shared
  memory / user profile / current moment）
- 工具：函数 + metadata 自动注册，行为可观测
- 运行时：事件总线 + 服务解耦 + 可重放的 message stream

---

## Core Ideas

### 1. Simulate life, don't just respond

引擎核心是异步事件循环、不是一次性请求-响应。这是一个明确的建模选择：
chatbot 是一个连续的、可被驱动的 process，而不是无状态的 RPC 接口。

### 2. Events as the stream of consciousness

系统中发生的一切都是不可变的 `Message` 事件。数据库不是状态快照，
而是这条意识流的永久日志。这种 Event Sourcing 的姿态保证了
**完全的可审计性与状态可重建性**。

### 3. Decoupled organs, unified by a nervous system

服务（`Orchestrator`、`ContextService`、`LLMService`、`ToolExecutor`、
`PersistenceService`、`IdentityService`、`ConfigService` ……）作为独立
"器官"，每个只负责一件事。它们**不直接相互调用**，所有交互都通过
`NexusBus` 完成——这套总线就是系统的神经系统。

### 4. Clarity over cleverness

代码必须透明地反映 `Message` 事件流。一个藏在聪明类里的复杂算法，
不如一段简单的、可观察的事件序列。我们优先架构出**可观测、可读懂**
的系统。

### 5. Database as configuration

行为的真实来源不是写死的代码，而是数据库里的动态配置（LLM catalog、
可编辑字段、prompts 等）。允许参数实时调整，为后续的"自我演化"留下
入口。

### 6. TDD as a mandate

逻辑的演化必须由测试驱动：先写失败测试定义契约，再实现最小可通过版本，
再重构。测试套件是这个系统的可执行规格。

---

## Architecture at a glance

```
Frontend (AURA)                          Backend (NEXUS)
─────────────────                        ─────────────────────────
WebSocket client      ──────────►        WebsocketInterface
Zustand stores                            │
                                          ▼
                                       NexusBus  ◄─────────────┐
                                          │                    │
                ┌─────────────┬───────────┴──────────┬─────────┴──────────┐
                ▼             ▼                      ▼                    ▼
          Orchestrator   ContextService         LLMService          ToolExecutor
                                                                          │
                                                                          ▼
                                                                  ToolRegistry
                                          ▲
                                          │
                                  PersistenceService
                                          │
                                          ▼
                                    DatabaseService (Mongo)
```

每个服务只做一件事；它们之间通过 `NexusBus` 上的事件协作。
PersistenceService 在总线上被动监听，把所有重要事件写入数据库——
保证一切"想过的"和"经历过的"都被永久存档。

---

## Multi-message context

NEXUS 不把所有信息塞进一个巨型 prompt，而是为每个 turn 编译多层上下文：

| Layer            | 内容 |
|------------------|------|
| **Capabilities** | 可用工具、能力描述 |
| **Shared memory**| 与当前对话相关的长期记忆召回 |
| **User profile** | 关于用户的稳定特征与偏好 |
| **Current moment** | 时间、客户端状态、当前 turn 输入 |

这些层以结构化形式（XML-friendly）注入，便于 LLM 提供商缓存复用，
也便于在调试时单独观察哪一层贡献了什么。

> 设计目标：上下文不是"把历史塞进去"，而是**组织出当前需要的工作集**。

---

## Tools

工具系统采取"约定优于配置"的姿态：

- 把同步函数和 metadata 常量写在 `nexus/tools/definition/*.py`；
- 启动时 `ToolRegistry.discover_and_register('nexus.tools.definition')`
  会自动发现并注册；
- 工具调用结果通过事件总线流回，对前端 UI 与 LLM 都可见。

---

## AURA — The expression layer

AURA 是 NEXUS 的"表达层"，遵循"灰度克制"美学：

1. **Silence over noise** — 信息靠结构与节奏传达，不靠颜色和装饰。
2. **Structure over decoration** — 美感来自布局、排版、留白的秩序。
3. **Input as the nexus** — 对话和命令共用一个输入框（`/` 切换命令模式），
   拒绝 GUI 菜单堆砌。
4. **Living interaction: state as animation** — 动效不是装饰，而是 NEXUS
   引擎内部状态（`thinking`、`tool_running` ……）的真实可视化。

---

## Repository layout

```
nexus/                Backend (FastAPI + event-driven services)
├── core/             NexusBus, topics, shared models
├── services/         Orchestrator, Context, LLM, Tools, Persistence, …
├── interfaces/       rest.py, websocket.py
├── prompts/          prompt-layer templates
└── tools/definition/ auto-discovered tool definitions

aura/                 Frontend (React 19 + TypeScript + Vite)
├── src/app/
├── src/components/
├── src/features/
├── src/hooks/
├── src/services/
├── src/stores/
└── src/lib/

tests/                Backend tests (unit / integration / e2e)
docs/
├── knowledge_base/   Vision, philosophy, architecture, references
├── developer_guides/ Setup, contributing, testing, AI charter
├── rules/            Frontend principles, logic schema
├── tasks/            Three-part task files
├── strategic_plans/  Multi-conversation initiatives
└── learn/            Past incidents and lessons
LOGIC_MAP.md          Project logic map (FLOW-* / CMP-* / INV-*)
```

---

## Status

NEXUS / AURA 是一个**学习与实验性质的全栈项目**，承担了几件事：

- 验证事件驱动架构是否能让 chatbot 行为更可观测、更可重构；
- 把"记忆"从单一 embedding 池拆成多层结构（短期 / 长期 / profile）；
- 把工具和上下文从 prompt 字符串里独立出来；
- 把灰度极简前端做成对引擎状态的真实表达，而不是装饰。

它不是面向真实用户的产品；很多决策（例如 grayscale-only、命令行式输入）
是为了把"系统的形状"表达清楚。后续的更现实化的协作工作台思考被沉淀到
另一个项目 [HaL](https://github.com/wowyuarm/HaL)。

---

## Further reading

- [`docs/knowledge_base/01_VISION_AND_PHILOSOPHY.md`](docs/knowledge_base/01_VISION_AND_PHILOSOPHY.md) — 项目宪法与设计哲学
- [`docs/knowledge_base/02_NEXUS_ARCHITECTURE.md`](docs/knowledge_base/02_NEXUS_ARCHITECTURE.md) — 后端架构与事件流
- [`docs/knowledge_base/technical_references/context_architecture_v2.md`](docs/knowledge_base/technical_references/context_architecture_v2.md) — 多消息上下文架构
- [`docs/rules/frontend_design_principles.md`](docs/rules/frontend_design_principles.md) — 前端设计原则
- [`LOGIC_MAP.md`](LOGIC_MAP.md) — 项目逻辑地图
