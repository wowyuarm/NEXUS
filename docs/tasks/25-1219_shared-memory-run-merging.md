# [TASK-25-1219]: SHARED_MEMORY 按 run_id 合并 AI 消息并标注工具调用

**Date:** 2025-12-19
**Status:** ✅ Completed

---

## Part 1: Task Brief

### Background
当前 `[SHARED_MEMORY]` 上下文块将同一 `run_id` 内的多个 AI 消息分别计数，导致历史显得冗长、重复，且计数（`count=N`）不反映真实的"对话轮次"。同时，工具调用信息对 AI 不可见，降低了历史上下文的完整性。用户识别到此问题，要求按 `run_id` 合并 AI 消息，并在适当位置标注工具调用。

### Objectives
1. 按 `run_id` 合并 AI 消息：同一 `run_id` 内的所有 AI 消息合并为一个逻辑响应，保持时间顺序。
2. 标注工具调用：在合并的响应中插入 `[tool_use:name, query:...]` 标注，置于工具调用声明与最终回答之间。
3. 更新计数语义：`[SHARED_MEMORY count=N]` 反映合并后的消息数（Human + 合并的 AI），而非原始消息条数。

### Deliverables
- [ ] `nexus/services/context/formatters.py` - 新增 `_merge_messages_by_run_id()` 和 `_extract_tool_call_annotation()` 方法，修改 `format_shared_memory()`
- [ ] `tests/nexus/unit/services/context/test_formatters.py` - 更新现有测试，新增合并逻辑和工具标注测试
- [ ] `docs/knowledge_base/technical_references/context_architecture_v2.md` - 更新 `[SHARED_MEMORY]` 章节，说明合并行为与计数语义
- [ ] 所有单元测试通过，手动验证合并效果符合预期

### Risk Assessment
- ⚠️ **合并逻辑复杂性**：处理同一 `run_id` 内多个 human 消息、AI 消息的多种排列可能引入边界条件错误。
  - **Mitigation**：实现保守合并策略：保持所有 human 消息，仅合并连续 AI 消息；编写全覆盖的测试用例。
- ⚠️ **工具标注格式被 AI 误解**：`[tool_use:web_search, query:...]` 可能被误解析为消息内容。
  - **Mitigation**：保持格式简洁明确；在 CORE_IDENTITY 中可加入对此格式的说明（如需）；通过真实 LLM 调用验证。
- ⚠️ **向后兼容性**：计数变化可能影响依赖 `count` 的监控或调试工具。
  - **Mitigation**：在相关文档中明确说明计数语义变化；不修改数据库结构，仅改变格式化逻辑。

### Dependencies
**代码依赖**：
- `PersistenceService.get_history()` 返回的消息必须包含 `run_id` 字段（已满足）
- AI 消息的 `metadata.tool_calls` 字段包含工具调用信息（已满足）
- `MemoryFormatter.format_shared_memory()` 的现有接口保持不变

**外部依赖**：无

### References
- `LOGIC_MAP.md` - 项目逻辑映射，CMP-context-builder 组件
- `nexus/services/context/formatters.py` - 现有 MemoryFormatter 实现
- `nexus/services/context/builder.py` - ContextBuilder 调用链
- `nexus/services/persistence.py` - 消息持久化格式与字段
- `docs/knowledge_base/technical_references/context_architecture_v2.md` - 上下文架构 v2
- `docs/tasks/25-1210_context-refactor.md` - 先前上下文重构任务

### Acceptance Criteria
- [x] 同一 `run_id` 的多个 AI 消息合并为一条，内容按时间顺序连接（换行分隔）
- [x] 工具调用正确标注：`[tool_use:web_search, query:人工智能最新发展 2025]`，置于工具调用声明与最终回答之间
- [x] `[SHARED_MEMORY count=N]` 的 N 为合并后的消息数（human + 合并的 ai）
- [x] 所有现有测试通过（更新期望值后）
- [x] 手动运行 `scripts/context_preview.py` 显示合并效果符合预期
- [x] 文档 `context_architecture_v2.md` 更新反映新行为

---

## Part 2: Implementation Plan

### Architecture Overview
本任务修改 `MemoryFormatter` 的格式化逻辑，不涉及数据库结构、总线话题或服务接口变更。核心是在格式化前增加消息合并与工具标注步骤，保持输出格式兼容。

### Phase Decomposition

#### Phase 1: 实现消息合并与工具标注核心逻辑
**Goal**：在 `MemoryFormatter` 中添加 `_merge_messages_by_run_id()` 和 `_extract_tool_call_annotation()` 方法。

**Key Files**：
- **修改文件**：`nexus/services/context/formatters.py`
  - 新增 `_merge_messages_by_run_id(history: list[dict]) -> list[dict]`
  - 新增 `_extract_tool_call_annotation(tool_calls: list) -> str`
  - 修改 `format_shared_memory()` 调用合并逻辑

**Detailed Design**：

**方法签名**：
```python
@staticmethod
def _merge_messages_by_run_id(messages: list[dict]) -> list[dict]:
    """
    按 run_id 合并 AI 消息，标注工具调用。

    输入: 原始消息列表（按时间倒序，最新在前）
    输出: 合并后的消息列表（保持跨 run_id 的时间顺序）

    处理逻辑:
    1. 过滤：只保留 role in ("human", "ai")
    2. 分组：按 run_id 分组
    3. 合并每个 run_id 组:
       - 分离 human 消息和 ai 消息
       - human 消息：保持原样（通常只有一条）
       - ai 消息：按时间顺序合并所有 ai 消息内容
       - 提取工具调用信息，生成标注字符串
       - 构建合并后的 ai 消息（使用最新的时间戳）
    4. 重新排序：按时间戳升序（最旧在前）
    """
```

**工具标注提取**：
```python
@staticmethod
def _extract_tool_call_annotation(tool_calls: list) -> str:
    """
    从 tool_calls 生成标注字符串。

    格式: [tool_use:web_search, query:人工智能最新发展]
    多工具: [tool_use:web_search, query:...; tool_use:calculator, expression:...]

    只提取关键参数：对于 web_search 提取 query，其他工具提取第一个参数。
    """
```

**合并后的 AI 消息结构**：
```python
{
    "id": "merged_ai_{run_id}",  # 或保留最新 AI 消息的 ID
    "run_id": run_id,
    "role": "ai",
    "content": "AI 消息1\nAI 消息2\n[tool_use:web_search, query:...]\nAI 消息3",
    "timestamp": latest_ai_timestamp,
    "metadata": {"source": "merged", "original_count": n}
}
```

**边界情况处理**：
- 缺少 `run_id`：保持原样，不合并（向后兼容）
- 多个 human 消息：全部保留，仅合并 AI 消息
- 无工具调用：不插入标注
- AI 消息内容为空：合并后内容为 `"[工具调用结果]"`（占位符）

**Test Cases**：
**测试文件**：`tests/nexus/unit/services/context/test_formatters.py`
- `test_merge_messages_by_run_id_simple()` - 基础合并功能
- `test_merge_messages_by_run_id_multiple_human()` - 多个 human 消息
- `test_merge_messages_by_run_id_no_run_id()` - 缺少 run_id 的消息
- `test_extract_tool_call_annotation_web_search()` - web_search 工具标注
- `test_extract_tool_call_annotation_empty()` - 空 tool_calls
- `test_extract_tool_call_annotation_multiple_tools()` - 多工具调用

#### Phase 2: 集成到 format_shared_memory 并更新计数
**Goal**：修改 `format_shared_memory()` 使用合并逻辑，更新计数计算。

**Key Files**：
- **修改文件**：`nexus/services/context/formatters.py`
  - 修改 `format_shared_memory()`：先合并，后应用 limit 和格式化
  - 更新计数计算：使用合并后的消息列表长度

**Detailed Design**：
```python
@staticmethod
def format_shared_memory(history: list[dict], limit: int = 20) -> str:
    # 1. 合并消息
    merged_messages = MemoryFormatter._merge_messages_by_run_id(history)

    # 2. 应用 limit（基于合并后的消息数）
    filtered = []
    for msg in merged_messages:
        role = msg.get("role", "").lower()
        if role in ("human", "ai"):
            filtered.append(msg)
        if len(filtered) >= limit:
            break

    # 3. 原有格式化逻辑（反转顺序、格式化行等）
    # ... 保持现有代码，但使用 filtered 而非直接遍历 history
```

**计数更新**：
- 原来：`count=过滤后的消息数`
- 现在：`count=合并后过滤的消息数`（更准确地反映对话轮次）

**Test Cases**：
- `test_format_shared_memory_with_merged_messages()` - 验证合并后的格式化输出
- `test_format_shared_memory_count_updated()` - 验证计数更新
- `test_format_shared_memory_limit_applied_after_merge()` - limit 在合并后应用

#### Phase 3: 更新现有测试与文档
**Goal**：更新现有测试的期望值，更新架构文档。

**Key Files**：
- **修改文件**：
  - `tests/nexus/unit/services/context/test_formatters.py` - 更新现有测试期望值
  - `docs/knowledge_base/technical_references/context_architecture_v2.md` - 更新 `[SHARED_MEMORY]` 章节

**Detailed Design**：
1. **测试更新**：识别受影响的现有测试（约 5-7 个），更新其期望的 `count` 值和格式化行数。
2. **文档更新**：在 `context_architecture_v2.md` 的 `[SHARED_MEMORY]` 章节添加：
   - 合并行为说明
   - 计数语义说明
   - 工具标注格式说明

**Test Cases**：
- 运行完整测试套件：`pytest tests/nexus/unit/services/context/ -v` 确保全部通过

### Implementation Order
1. **阶段 1**：实现核心合并与标注逻辑 + 单元测试（TDD：先写测试）
2. **阶段 2**：集成到 `format_shared_memory` + 集成测试
3. **阶段 3**：更新现有测试期望值与文档

### Key Files
**修改文件（2）**：
- `nexus/services/context/formatters.py`
- `tests/nexus/unit/services/context/test_formatters.py`
- `docs/knowledge_base/technical_references/context_architecture_v2.md`

**不修改但受影响的文件**：
- `nexus/services/context/builder.py`（调用 `MemoryFormatter.format_shared_memory()`）
- `scripts/context_preview.py`（手动验证工具）

### Acceptance Criteria (重复 Part 1)
- [ ] 同一 `run_id` 的多个 AI 消息合并为一条，内容按时间顺序连接（换行分隔）
- [ ] 工具调用正确标注：`[tool_use:web_search, query:人工智能最新发展 2025]`，置于工具调用声明与最终回答之间
- [ ] `[SHARED_MEMORY count=N]` 的 N 为合并后的消息数（human + 合并的 ai）
- [ ] 所有现有测试通过（更新期望值后）
- [ ] 手动运行 `scripts/context_preview.py` 显示合并效果符合预期
- [ ] 文档 `context_architecture_v2.md` 更新反映新行为

---

## Part 3: Completion Report

**Date:** 2025-12-19
**Status:** ✅ Completed

### 1. Implementation Overview

The task successfully implemented message merging by `run_id` and tool call annotation in the `[SHARED_MEMORY]` context block. Key changes were made to `nexus/services/context/formatters.py`:

1. **`_merge_messages_by_run_id()`**: New static method that groups messages by `run_id`, merges AI messages within each group, and inserts tool call annotations at the correct position.
2. **`_extract_tool_call_annotation()`**: New static method that generates annotation strings like `[tool_use:web_search, query:人工智能最新发展]` from tool call metadata.
3. **`format_shared_memory()`**: Updated to use merged messages, ensuring the `count=N` reflects merged message count (human + merged AI).

The implementation follows the user's explicit requirement: "把这个标注放在我来搜索后面，最终回答前面，本来就是有顺序的" – annotations are inserted after the AI message where the tool was declared, before subsequent AI responses.

### 2. Key Technical Decisions

#### 2.1 Message Merging Strategy
- **Grouping by `run_id`**: Messages without `run_id` remain unchanged (backward compatibility).
- **Human messages**: All human messages within a `run_id` are kept unchanged.
- **AI message merging**: All AI messages within the same `run_id` are merged chronologically, with contents joined by newlines.
- **Time ordering**: Merged messages are sorted by timestamp descending, ensuring `format_shared_memory()`'s `reversed()` produces chronological order.

#### 2.2 Tool Annotation Format
- **Single tool**: `[tool_use:web_search, query:人工智能最新发展]`
- **Multiple tools**: `[tool_use:web_search, query:...; tool_use:calculator, expression:...]`
- **Parameter extraction**: For `web_search`, extracts `query` parameter; for other tools, extracts first parameter.

#### 2.3 Annotation Positioning
- **Track first tool call**: The method tracks the index of the first AI message containing tool calls.
- **Insertion point**: Annotation is inserted after that message (at `first_tool_call_index + 1`).
- **Fallback**: If tracking fails, annotation is appended at the end.

#### 2.4 Count Semantics Update
- **Before**: `count=N` reflected filtered message count (each AI message counted separately).
- **After**: `count=N` reflects merged message count (human + merged AI), accurately representing "conversational turns".

### 3. Debugging Process

#### 3.1 Initial Test Failures
1. **`test_format_shared_memory_count_updated`**: Expected `count=3` but got `count=4`.
   - **Root cause**: Test expectation was wrong – there were actually 4 messages (run_abc: human + merged ai, run_def: human + ai).
   - **Fix**: Updated test expectation to `count=4`.

2. **`test_format_shared_memory_chronological_order`**: "First" appeared after "Second".
   - **Root cause**: `_merge_messages_by_run_id()` returned messages in wrong order.
   - **Fix**: Added `merged_messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)` to ensure correct ordering.

3. **`test_format_shared_memory_with_merged_messages`**: IndexError in annotation position check.
   - **Root cause**: Test expected merged content on a single line with `\n` separators, but actual output had separate lines.
   - **Fix**: Updated test to check line ordering rather than splitting content.

#### 3.2 User Requirement Implementation
- **Initial approach**: Annotation appended at the end of merged content.
- **User feedback**: "标注放在我来搜索后面，最终回答前面"
- **Revised approach**: Track `first_tool_call_index` and insert annotation at correct position.

### 4. Test Verification

All 45 unit tests in the context formatters test suite pass:

```
poetry run pytest tests/nexus/unit/services/context/test_formatters.py -v
```

**New test cases added:**
- `test_merge_messages_by_run_id_simple` – basic merging functionality
- `test_merge_messages_by_run_id_multiple_human` – multiple human messages in same run_id
- `test_merge_messages_by_run_id_no_run_id` – messages without run_id
- `test_extract_tool_call_annotation_web_search` – annotation extraction for web_search
- `test_extract_tool_call_annotation_empty` – empty tool_calls handling
- `test_extract_tool_call_annotation_multiple_tools` – multiple tool annotation
- `test_format_shared_memory_with_merged_messages` – integrated formatting with merging
- `test_format_shared_memory_count_updated` – count semantics verification
- `test_format_shared_memory_limit_applied_after_merge` – limit applied after merging

**Integration tests:** All 7 orchestrator integration tests pass, confirming no breakage in the broader system.

### 5. Documentation Updates

Updated `docs/knowledge_base/technical_references/context_architecture_v2.md`:

1. **`[SHARED_MEMORY]` section**: Added detailed description of message merging, tool annotation, count semantics, and processing flow.
2. **Formatters section**: Updated `MemoryFormatter` method signatures to include new `_merge_messages_by_run_id()` and `_extract_tool_call_annotation()` methods.
3. **Example format**: Updated example to show merged messages with tool annotation.

### 6. Manual Verification

Running `scripts/context_preview.py` produces correct output:
- `[SHARED_MEMORY count=4]` – correctly counts 2 human + 2 merged AI messages
- Messages displayed in chronological order
- No tool annotations in mock data (as expected)

### 7. Reflections

#### 7.1 What Worked Well
- **Incremental implementation**: Following TDD workflow (write failing tests first) caught edge cases early.
- **Clear user requirements**: User's explicit positioning requirement prevented incorrect implementation.
- **Backward compatibility**: Messages without `run_id` are handled gracefully.

#### 7.2 Challenges
- **Test maintenance**: Updating existing tests required careful analysis of expected vs. actual behavior.
- **Annotation positioning**: Determining the correct insertion point required tracking the first tool call index.

#### 7.3 Future Considerations
1. **Tool result inclusion**: Currently only annotations are included; future could include condensed tool results.
2. **Annotation format**: Consider if `[tool_use:...]` format is optimal for LLM comprehension.
3. **Multi-turn tools**: Complex tools that require multiple back-and-forth turns may need special handling.

### 8. Commit References

Implementation was done in feature branch `feat/shared-memory-run-merging`. Key commits include:
- `docs/tasks/25-1219_shared-memory-run-merging.md` – Task planning
- `nexus/services/context/formatters.py` – Core implementation
- `tests/nexus/unit/services/context/test_formatters.py` – Test updates
- `docs/knowledge_base/technical_references/context_architecture_v2.md` – Documentation updates

### 9.1 Additional Optimization: Time Display

Based on user feedback to save tokens, an additional optimization was implemented for timestamp display:

#### 9.1.1 Time Display Rules
1. **Human messages**: Always show full timestamp `[YYYY-MM-DD HH:MM]`
2. **AI messages following human**: Indented with two spaces, no timestamp (e.g., `  Nexus: response`)
3. **AI messages not following human**: Show full timestamp (e.g., first message is AI)

#### 9.1.2 Implementation
- Modified `format_shared_memory()` to track previous message role
- AI messages following human are displayed as `  Nexus: content`
- Maintains chronological order (oldest first)
- Handles edge cases: consecutive human messages, first message is AI

#### 9.1.3 Token Savings
- Each AI message saves ~24 characters (`[2025-12-10 15:30] `)
- For 20-message history: ~200 token savings
- Improves readability by visually grouping human-AI pairs

#### 9.1.4 Examples
```
[2025-12-10 10:00] Human: 你好
  Nexus: 你好！                 # AI缩进，无时间戳
[2025-12-10 10:01] Human: 问题1
[2025-12-10 10:02] Human: 问题2 # 连续human都有时间戳
  Nexus: 回答                   # AI跟在最后一个human后
```

### 9.2 Conclusion

The implementation successfully addresses the original problem: `[SHARED_MEMORY]` now provides a cleaner, more accurate representation of conversation history by merging AI messages within the same `run_id` and annotating tool usage. The `count=N` now reflects true conversational turns rather than raw message count, and tool call context is preserved without cluttering the history with multiple AI messages.

Additionally, the time display optimization saves tokens and improves visual grouping of conversational turns, making the history more readable for both humans and the AI.