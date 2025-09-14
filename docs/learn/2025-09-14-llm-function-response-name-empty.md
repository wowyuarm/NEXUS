# Google OpenAI 兼容接口 400 INVALID_ARGUMENT 错误：因 `function_response.name` 为空 (2025-09-14)

## 背景
- 涉及组件：`nexus/services/llm/service.py`、`nexus/services/orchestrator.py`、`nexus/services/tool_executor.py`、`nexus/services/persistence.py`
- 提供方：通过 OpenAI 兼容端点 (`/openai/chat/completions`) 调用 Google Gemini
- 症状：首次 LLM 调用正常；在工具执行后再次调用 LLM，请求失败并返回 400 INVALID_ARGUMENT，提示 `function_response.name` 为空。

## 观测日志
- `HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/openai/chat/completions "HTTP/1.1 400 Bad Request"`
- `Error handling LLM request ... * GenerateContentRequest.contents[2].parts[0].function_response.name: Name cannot be empty.`

## 诊断
- 错误仅发生在工具调用结果产生后、随后的 LLM 调用。
- 在 Google 的 OpenAI 兼容栈中，`role: "tool"` 消息会被转换为原生的 `function_response`，必须包含非空的 `name`，且最好与前一条 assistant 的 `tool_calls[].function.name` 一致。该映射依赖于有效的 `tool_call_id`。
- 消息流水线中的问题点：
  - 工具结果消息未将原始 `call_id` 从工具请求传回 orchestrator/persistence 层。
  - `orchestrator` 构造 `role: "tool"` 消息时没有设置非空 `name` 兜底值。
  - 在发送流式请求前，消息未进行最终的归一化处理，未保证符合 provider 特定要求（例如通过 `tool_call_id` 回填 `name`）。

## 修改内容
- 文件：`nexus/services/tool_executor.py`  
  - 方法：`ToolExecutorService.handle_tool_request()` 与 `_create_tool_result_message()`  
  - 修改：在工具结果消息中传播工具请求的 `call_id` (`content.call_id`)，保持与 assistant tool call 的关联。

- 文件：`nexus/services/persistence.py`  
  - 方法：`PersistenceService.handle_tool_result()`  
  - 修改：在工具消息元数据中持久化 `call_id`，保证历史消息可重建时包含它。

- 文件：`nexus/services/orchestrator.py`  
  - 方法：`OrchestratorService._convert_history_to_llm_messages()`  
  - 修改：为 `role: "tool"` 消息补充非空 `name`，来源于 `hist_msg.metadata["tool_name"]`，缺失时默认 `"unknown"`，同时保留 `tool_call_id`。

- 文件：`nexus/services/llm/service.py`  
  - 方法：`LLMService._create_streaming_response()` 与新增的 `_normalize_messages_for_provider()`  
  - 修改：在发送请求前执行归一化：
    - 从 `assistant.tool_calls[].id` 建立 id -> function.name 的映射。
    - 对每个 `role: "tool"` 消息：
      - 若 `name` 为空，则通过 `tool_call_id` 回填，否则兜底 `"unknown"`。
      - 确保 `content` 为字符串（必要时进行 JSON 序列化）。

## 验证
- 本地测试：161 项测试全部通过。
- 手工测试：在工具调用周期后，后续 LLM 调用成功；不再出现 `function_response.name` 为空的 INVALID_ARGUMENT 错误。

## 经验教训
- 各厂商的 “OpenAI 兼容” 并非完全一致，有的会额外强制约束。Google 要求 `function_response.name` 非空，并由工具消息或 assistant 的 tool call 提供。
- 必须保证 `tool_call_id` 全流程传递，以便工具结果消息能被匹配并补充正确的工具名。
- 在 API 调用前增加 provider 无关的消息归一化层，以确保最小模式合规。

## 与 2025-09-12 事件的关系
- 2025-09-12 的问题聚焦在 OpenAI 兼容模式下参数正确性，避免将未关联的 `role: tool` 消息注入首个 LLM 请求。
- 本次问题则是 provider 特有的：即便 schema 正确，Google 仍要求工具响应必须有非空 `name`。通过保留 `call_id`、补充工具消息 `name`、增加归一化步骤解决。
- 参考文档：`docs/learn/2025-09-12-llm-invalid-argument-tool-calls.md`

## 后续措施
- 考虑统一通过 provider 抽象层路由所有流式调用，以集中处理错误与配置。
- 扩展归一化逻辑到非流式路径，作为通用工具，预防其他 provider 出现类似严格要求。
- 增加针对性测试：
  - 验证 `tool_call_id` 从请求 -> 结果 -> 持久化 -> 历史 -> 后续 LLM 调用的完整传播。
  - 验证通过 assistant `tool_calls` 映射正确回填 `name`。
