### **任务委托单：AURA-RENDER**

**致：** 前端工程师AI

**发令者：** “枢”，AURA项目首席AI架构师

**主题：** 重构AURA核心UI组件以展现动态生命感

**任务ID：** `RENDER`

---

**指令头 (Preamble):**
你将严格遵循《AURA-DESIGN: 交互空间设计宪章 V2.0》。本次任务是重构AURA的核心UI组件，使其能够连接到我们新构建的状态管理系统，并根据后端广播的实时事件，渲染出富有生命感的动态交互界面。

---

#### **第一部分：任务目标 (Objective)**

你的任务是重构和创建一个核心UI组件，并最终将它们整合进主聊天视图中：
1.  **创建`ToolCallCard.tsx`**: 一个全新的组件，用于可视化工具调用的状态。
2.  **重构`ChatMessage.tsx`**: 使其能够根据全局状态，动态渲染文本、思考动画或工具卡片。
3.  **重构`ChatContainer.tsx`**: 将其连接到新的`useAura` Hook，驱动整个视图。

#### **第二部分：文件与核心指令 (Files & Core Instructions)**

你将按顺序对以下文件进行操作：

**1. 新文件创建: `src/features/chat/components/ToolCallCard.tsx`**
*   **任务**: 创建一个用于展示工具调用状态的专用组件。
*   **核心指令**:
    *   **Props接口**: `interface ToolCallCardProps { toolCall: ToolCall }` (其中`ToolCall`类型来自`auraStore.ts`)。
    *   **设计语言**: 严格遵循“液态玻璃”设计语言（半透明、模糊、边框、阴影）。
    *   **内容**:
        *   显示工具名称 (`toolCall.toolName`) 和一个状态图标。
        *   当`toolCall.status`为`'running'`时，显示一个加载动画，并开始**“液态光晕”**动画（可以通过`box-shadow`或伪元素实现）。
        *   当`toolCall.status`为`'finished'`时，光晕消失，状态图标变为成功（`对勾`）或失败（`错号`）。注意都是无颜色的线性符号，比如可以是一个小圆圈内的勾号和叉号。
        *   （可选）可以有一个折叠/展开功能，点击后显示工具的参数`args`和返回的`result`。

**2. 文件重构: `src/features/chat/components/ChatMessage.tsx`**
*   **任务**: 将其从一个简单的消息渲染器，重构为一个智能的AI状态展示器。
*   **核心指令**:
    *   **Props修改**: 它的`message` prop现在可能是一个占位符。因此，它需要从外部接收一个`currentRunStatus: Run['status']`和`activeToolCalls: ToolCall[]`。
    *   **关键逻辑重构**:
        *   这个组件的核心将是一个**条件渲染逻辑**。
        *   **只在`message.role === 'AI'`且`isLastMessage`为`true`时**，才执行以下判断：
            *   如果`currentRunStatus`是`'thinking'`，则不渲染`MarkdownRenderer`，而是渲染**“呼吸光点”**动画。
            *   如果`currentRunStatus`是`'tool_running'`，则遍历`activeToolCalls`数组，为每一个`toolCall`渲染一个`ToolCallCard`组件。
            *   如果`currentRunStatus`是`'streaming_text'`，则执行原有的`useTypewriter`和`MarkdownRenderer`逻辑。
        *   在所有其他情况下（历史消息、用户消息），它应该直接、完整地渲染`message.content`，**不使用**打字机效果。

**3. 文件重构: `src/features/chat/components/ChatView.tsx`**
*   **任务**: 保持其作为纯展示组件的职责，但更新其props以接收新的状态。
*   **核心指令**:
    *   修改`ChatViewProps`接口，使其接收`currentRunStatus`和`activeToolCalls`，并将它们传递给`ChatMessage`组件。

**4. 文件重构: `src/features/chat/ChatContainer.tsx`**
*   **任务**: 将所有部分连接起来，完成最终的整合。
*   **核心指令**:
    *   **替换Hook**: 将`useChat`的调用，替换为我们新创建的`useAura`。
    *   **状态传递**: 从`useAura`中获取`messages`, `currentRun`, `sendMessage`等所有必要的状态和函数。
    *   将这些状态（包括`currentRun.status`和`currentRun.activeToolCalls`）作为props，正确地传递给`ChatView`组件。
    *   确保`onSendMessage`和自动滚动逻辑与新的Hook和状态正确集成。

---
**交付要求：**
你必须：
1.  提供`src/features/chat/components/ToolCallCard.tsx`的完整代码。
2.  提供`src/features/chat/components/ChatMessage.tsx`重构后的完整代码。
3.  提供`src/features/chat/components/ChatView.tsx`重构后的完整代码。
4.  提供`src/features/chat/ChatContainer.tsx`重构后的完整代码。

这些代码必须能够协同工作，将AURA的状态管理与UI渲染完全打通，实现一个能够实时、动态地反映NEXUS后端思考和行动过程的、富有生命感的交互界面。

**任务开始。**