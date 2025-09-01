### **任务委托单：AURA-LIVING-BUBBLE**

**致：** 前端工程师AI

**发令者：-** “枢”，AURA项目首席AI架构师

**主题：** 实现“活的气泡”渲染模型以统一AI的思考流

**任务ID：** `LIVING-BUBBLE`

---

**指令头 (Pramble):**
你将严格遵循《AURA-DESIGN宪章》。本次任务是实现一个高级的、统一的AI消息渲染模型。你需要重构`auraStore`和`ChatMessage`，使得一次复杂的工具调用过程，被呈现在一个动态扩展的、单一的AI消息气泡中。

---

#### **第一部分：任务目标 (Objective)**

你的任务是重构`auraStore`和`ChatMessage`，以实现“活的气泡”效果。AI的“意图文本”、“工具调用卡片”和“总结文本”必须在同一个消息气泡内，按顺序、动态地追加显示。

#### **第二部分：文件与核心指令 (Files & Core Instructions)**

你将主要对以下两个文件进行深度重构：

**1. 文件重构: `src/features/chat/types.ts` 和 `src/features/chat/store/auraStore.ts` (心智模型的升级)**

*   **任务**: 升级`Message`和`Store`的数据结构，以支持“活的气泡”模型。
*   **核心指令**:
    *   **在`types.ts`中，重构`Message`接口**:
        *   一个AI消息不再只有一个`content`字段。它需要能容纳多个部分。
        *   **新的`Message`接口 (AI角色)**:
            ```typescript
            interface AiMessage extends BaseMessage {
              role: 'AI';
              intentContent?: string; // 串场词
              toolCalls?: ToolCall[]; // 工具调用
              summaryContent?: string; // 总结性回复
              isStreamingIntent?: boolean;
              isStreamingSummary?: boolean;
            }
            ```
    *   **在`auraStore.ts`中，重构Actions**:
        *   **`handleTextChunk`**:
            *   这个action现在需要更智能。它需要判断当前`currentRun.status`。
            *   如果`status`是`'thinking'`，它应该将`chunk`追加到最后一条AI消息的`intentContent`字段。
            *   如果`status`是`'streaming_text'`（在工具调用后），它应该将`chunk`追加到`summaryContent`字段。
        *   **`handleToolCallStarted`**:
            *   它**不应**创建新消息。
            *   它应该找到`messages`数组中最后一条AI消息，将`isStreamingIntent`设为`false`，然后将新的`toolCall`信息添加到该消息的`toolCalls`数组中。
        *   **`handleToolCallFinished`**:
            *   它也**不应**创建新消息。
            *   它应该找到最后一条AI消息，并更新其`toolCalls`数组中对应工具的状态。

**2. 文件重构: `src/features/chat/components/ChatMessage.tsx` (躯壳的进化)**

*   **任务**: 重构`ChatMessage`，使其能够渲染一个包含多个部分的、动态扩展的“活的气泡”。
*   **核心指令**:
    *   **引入`framer-motion`的`AnimatePresence`和`layout`**: 组件的根`motion.div`需要使用`layout` prop，来实现高度的平滑动画。
    *   **新的渲染逻辑 (针对AI消息)**:
        1.  **渲染意图**: 如果`message.intentContent`存在，则使用`useTypewriter`（当`isStreamingIntent`为true时）渲染它。
        2.  **渲染工具**: 如果`message.toolCalls`存在，则`map`这个数组，为每个`toolCall`渲染一个`ToolCallCard`组件。使用`AnimatePresence`来处理卡片的入场动画。
        3.  **渲染总结**: 如果`message.summaryContent`存在，则使用`useTypewriter`（当`isStreamingSummary`为true时）渲染它。
    *   **思考状态**: “呼吸光点”的逻辑保持不变，它在没有任何内容可显示时（例如，`run_started`刚触发）出现。

---
**交付要求：**
你必须：
1.  提供`src/features/chat/types.ts`和`src/features/chat/store/auraStore.ts`重构后的完整代码。
2.  提供`src/features/chat/components/ChatMessage.tsx`重构后的完整代码。

完成这次重构后，AURA将能够以一种真正符合直觉的、电影叙事般的方式，向用户展示曦的完整思考过程，同时保持其人格的统一性和交互的连贯性。

**任务开始。**