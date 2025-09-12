## CONFIG-API-SUITE：构建 NEXUS 的动态配置管理 API 套件

### 出发点

在 `GENESIS-CONFIG` 重构中，我们成功地将 NEXUS 系统的配置“事实来源”从静态的 `config.default.yml` 文件迁移到了动态的 MongoDB 数据库。这为系统的“活性”和“可进化性”奠定了基础。但当时我们有意做了战略简化：仅实现“读取”，而“写入”仍依赖手动数据库操作。随着系统发展，这将成为瓶颈。

### 项目进展

当前，`ConfigService` 在启动时从数据库加载配置。系统已具备从动态源读取配置的能力。

### 如何扩展 (The Plan)

我们将分阶段为 NEXUS 构建一套生产级的配置管理 API，并将变更实时同步至系统运行状态。

#### 阶段一：基础 API 层 (`rest_api.py`)

- **目标**：创建安全、健壮的 CRUD（创建/读取/更新/删除）API，用于管理 `system_configurations` 集合中的配置文档。
- **实现**：
  - `GET /api/v1/admin/configs`：列出所有配置文档（如 `global_config`, `agent_prompts`）。
  - `GET /api/v1/admin/configs/{config_id}`：获取特定配置文档内容。
  - `PUT /api/v1/admin/configs/{config_id}`：接收 JSON body，校验 schema 后更新数据库（核心）。
  - **安全**：上述 `admin` 端点由健壮的认证/授权机制保护（如专用 API Key 头）。

#### 阶段二：事件通知与热重载

- **目标**：配置变更可实时、无需重启地在 NEXUS 引擎中生效。
- **实现**：
  - **发布事件**：`PUT` 更新成功后，向 `NexusBus` 发布 `Topics.CONFIG_UPDATED` 事件，payload 包含 `config_id`。
  - **ConfigService 刷新**：订阅该主题，收到事件后调用 `reload_config(config_id)` 重新加载到内存。
  - **服务级热重载**：需动态响应配置的服务（如 `LLMService`）订阅此主题，收到后读取最新参数并按需重新初始化内部组件（如更换 LLM Provider 或默认模型）。

#### 阶段三：前端集成（可选管理界面）

- **目标**：为操作者提供可视化的配置管理界面。
- **实现**：
  - 在 AURA 中创建受保护路由（如 `/admin`）。
  - 前端页面调用配置管理 API，以表单展示所有可配置参数。
  - 管理员可修改 Prompt、切换默认模型、开关特性；点击保存后实时生效。

### 扩展效果 (The Outcome)

完成上述扩展后，NEXUS 将从“启动时被设定的系统”，进化为一个真正的“活性有机体”：

- 在系统运行时，安全、实时地调整其核心行为，就像调节恒温器一样简单。
- 为 AI 的自我进化提供 API 基础：未来“反思 Agent”可通过调用该 API 动态修改自己的 Prompt。
- 极大提升运维效率与灵活性，将配置管理从“代码部署”转变为“在线运营”。

---
---

## 计划项：将“近期工具结果”以 Markdown 文本注入到 system prompt（tools.md 之后）

本计划暂不实施，仅进行方案沉淀，待后续把 prompts 迁移至数据库后统一推进。

目标
- 在首次构建上下文时（`ContextService._build_messages_with_history()`），仍旧跳过历史 `role: tool` 消息进入 `messages[]`，以避免 OpenAI/Gemini 兼容 API 的 schema 问题。
- 同时，提供一个可配置的策略，将“最近的工具调用结果”以纯文本 Markdown 形式，拼接在 system prompt 的 `tools.md` 段落之后，让模型在“首轮”也能看到有限的工具历史要点。

注入位置
- 拼接到 `nexus/prompts/xi/tools.md` 之后（即 persona.md + system.md + tools.md + 近期工具结果 注释段）。

配置项（通过 ConfigService 读取；模板示例放在 `config.example.yml`）
- `memory.tool_results.enabled`: 是否启用该特性（默认 false）。
- `memory.tool_results.lookback_count`: 纳入的最近工具结果条数上限（建议默认 3 或 5）。
- `memory.tool_results.per_item_char_limit`: 每条工具结果的最大字符数，超出截断（建议默认 1000）。
- `memory.tool_results.allowed_tool_names`: 工具白名单（数组），为空表示不过滤。

行为说明
- 仅当 `enabled` 为 true 时生效；否则完全保持现状。
- 依赖同一次上下文构建中从数据库加载的历史（默认 20 条，由 `memory.history_context_size` 控制），从中筛选 `role == tool` 的消息，按时间倒序取最近 `lookback_count` 条。
- 将每条结果格式化为 Markdown 文本（可包含工具名、时间等基础元信息），并对内容进行长度截断（`per_item_char_limit`）。
- 不以 `role: tool` 的消息形式传给提供商，仅作为 system prompt 的普通文本，避免 schema 约束问题。
- 运行期的工具循环（同一 Run 内）不受影响，依旧由 `OrchestratorService._convert_history_to_llm_messages()` 严格按 OpenAI 兼容 schema 传递 `assistant(tool_calls)` 与 `tool(tool_call_id)`。

边界与后续
- 先不做脱敏/正则清洗（可在后续增强）。
- prompts 迁移至数据库后，可将“注入到 tools.md 后面”的逻辑统一为“在 DB 中对最终合成的 system prompt 进行动态拼接”。
- 上述 4 个配置项已足够支撑首版能力，未来如需增加总字数上限或更多显示策略，再迭代。
