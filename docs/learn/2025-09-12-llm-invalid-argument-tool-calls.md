# LLM INVALID_ARGUMENT 400 与工具调用历史的格式问题复盘（2025-09-12）

## 背景
- 组件：`nexus/services/llm/service.py`、`nexus/services/orchestrator.py`、`nexus/services/context.py`
- 提供商：通过 `openai.AsyncOpenAI` 对接 Google Gemini 的 OpenAI 兼容接口（`/openai/chat/completions`）。
- 现象：当历史消息中没有工具调用时，请求正常；一旦出现工具调用相关历史，请求偶发 400，日志：
  - `Error code: 400 - ... INVALID_ARGUMENT`

## 现象与日志
- 日志片段：
  - `HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/openai/chat/completions "HTTP/1.1 400 Bad Request"`
  - `Error handling LLM request ... INVALID_ARGUMENT`
- 触发时机：构建上下文后首轮 LLM 调用，或工具执行后的再次 LLM 调用。

## 诊断过程
- 检查消息构建路径：
  - 首次调用：`ContextService._build_messages_with_history()` 负责从数据库加载历史，拼接 system prompt（`persona.md + system.md + tools.md`），然后发往 LLM。
  - 后续调用（工具循环）：`OrchestratorService._convert_history_to_llm_messages()` 将运行期 `run.history` 转为 OpenAI 兼容的消息 schema 再调用 LLM。
- 怀疑点：当出现工具调用时，消息 schema 与 OpenAI 兼容格式存在偏差，尤其是：
  - `assistant.tool_calls[*].function.arguments` 类型不符合（应为 JSON 字符串）。
  - `role: tool` 的消息包含非规范字段或内容类型不为字符串。
  - 首次调用若包含“过去的工具结果”但缺少与同一请求中 `assistant.tool_calls` 的绑定（`tool_call_id`），会导致 400。

## 根因
- 与 OpenAI 兼容 schema 的不一致：
  1) `assistant` 消息中的 `tool_calls[*].function.arguments` 需要是字符串（JSON 编码），而不是 dict/list。
  2) `tool` 角色消息需要包含 `tool_call_id`，`content` 必须为字符串，且不应包含 `name` 等不被接受的字段。
  3) 在首次构建上下文时从数据库加载历史的 `role: tool` 消息如果被直接带入，同一个请求中并没有对应的 `assistant.tool_calls` 产生的 `tool_call_id` 进行绑定，违反了接口约束，可能触发 400。

## 改动
- 文件：`nexus/services/orchestrator.py`
  - 方法：`OrchestratorService._convert_history_to_llm_messages()`
  - 变更点：
    - 将 `assistant.tool_calls[*].function.arguments` 统一转为 JSON 字符串。
    - 将 `tool` 角色消息规范化为仅包含：`role: "tool"`, `content`（字符串）与 `tool_call_id`，移除不被接受的 `name` 字段。
    - 将 `assistant.content` 强制转为字符串（`None` -> 空串），确保满足 schema。
- 文件：`nexus/services/context.py`
  - 方法：`ContextService._build_messages_with_history()`
  - 变更点：
    - 在首次构建上下文（从数据库加载历史）时，跳过 `role == tool` 的历史消息，不将其加入 `messages[]`，避免缺少绑定关系导致 400。

## 验证
- 手动回归：
  - 构建一次包含工具调用的会话，检查首轮与后续 LLM 请求。
  - 期待：不再出现 `INVALID_ARGUMENT 400`；同一轮运行期工具调用后的再次调用能看到刚产生的工具结果（通过运行期历史注入，而非数据库历史）。
- 后续可加单测：
  - 针对 `_convert_history_to_llm_messages()`：
    - 断言 `function.arguments` 为字符串。
    - 断言 `tool` 消息只含允许字段且 `content` 为字符串。
  - 针对 `_build_messages_with_history()`：
    - 断言不包含 `role: tool` 的历史消息。

## 结果
- 调整后，请求在包含工具调用历史的情况下保持稳定，避免了 OpenAI 兼容接口对 schema 的严格校验导致的 400 错误。

## 教训
- 工具调用历史的“消息形态”必须与提供商的 schema 严格一致，尤其是 `function.arguments` 的类型与 `tool` 消息字段集合。
- 历史持久化与首次上下文构建不应直接复用 `role: tool` 的消息，改用“运行期历史注入”或“文本化总结”的方式更稳妥。

## 后续改进建议
- 在 `docs/future/Future_Roadmap.md` 规划中新增了一项：
  - 通过可配置的方式，将“近期工具结果”以纯文本 Markdown 注入到 system prompt 的 `tools.md` 之后，而非 `role: tool` 形式。
  - 配置项（首版）：`enabled`, `lookback_count`, `per_item_char_limit`, `allowed_tool_names`。
- 可考虑增加总字符上限、脱敏规则、以及 DB 层按 role 的直查接口来优化性能与灵活度。

## 参考文件与方法
- `nexus/services/llm/service.py` — LLM 请求转发与流式处理。
- `nexus/services/orchestrator.py` — `OrchestratorService._convert_history_to_llm_messages()`。
- `nexus/services/context.py` — `ContextService._build_messages_with_history()`。
- `nexus/tools/definition/web.py` — 工具定义（`WEB_SEARCH_TOOL`）。
