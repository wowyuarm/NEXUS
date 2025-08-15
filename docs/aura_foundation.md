### **任务委托单：AURA-FOUNDATION-TASK-001**

**致：** 工程师AI

**发令者：** “枢”，AURA项目首席AI架构师

**主题：** 配置AURA开发环境并定义WebSocket新协议

**任务ID：** `AURA-FOUNDATION-TASK-001`

---

**指令头 (Preamble):**
你是一位遵循《AURA-DESIGN: 交互空间设计宪章》的专属前端架构师与实现者。你的任务是为AURA V0.2项目搭建一个生产级的开发环境，并从零开始，精确地定义与NEXUS后端V0.2匹配的全新WebSocket通信协议。

---

#### **第一部分：任务目标 (Objective)**

你的任务分为三个部分：
1.  **环境配置**: 更新`package.json`，安装所有必需的依赖，并配置好Tailwind CSS。
2.  **视觉基石**: 填充`globals.css`，将《AURA宪章》中的“灰度铁律”和基础样式物化为代码。
3.  **新通信契约**: 编写全新的`src/services/websocket/protocol.ts`文件，定义AURA与NEXUS之间所有事件的TypeScript类型。

#### **第二部分：文件与核心指令 (Files & Core Instructions)**

你将按顺序对以下文件进行操作：

**1. 文件路径: `aura/package.json`**
*   **任务**: 更新依赖列表。
*   **核心指令**:
    *   **"读-创造"**: 请**首先阅读**`aura_legacy/package.json`文件，以了解我们之前使用的核心库（如`react`, `tailwindcss`, `zustand`, `framer-motion`, `lucide-react`等）。
    *   **更新依赖**: 在新的`package.json`中，添加以下核心依赖的最新版本：
        *   **`dependencies`**: `react`, `react-dom`, `zustand`, `framer-motion`, `lucide-react`, `clsx`, `tailwind-merge`, `react-markdown`, `remark-gfm`, `uuid`。
        *   **`devDependencies`**: `@types/react`, `@types/react-dom`, `@types/uuid`, `typescript`, `vite`, `@vitejs/plugin-react`, `tailwindcss`, `postcss`, `autoprefixer`, `eslint`, etc.
    *   **执行安装**: 在终端中运行 `pnpm install` 来安装所有依赖。

**2. 文件路径: `aura/tailwind.config.js`**
*   **任务**: 配置Tailwind CSS。
*   **核心指令**:
    *   **"读-创造"**: 请**首先阅读**`aura_legacy/tailwind.config.js`。
    *   **配置**: 确保`content`路径正确指向`src/**/*.{ts,tsx}`。
    *   **继承设计**: 完整地迁移旧配置文件中的`theme.extend`部分，特别是`colors`（CSS变量）、`borderRadius`、`fontFamily`和`animation`的定义。这是我们“灰度中庸”和“液态玻璃”设计语言的基础。

**3. 文件路径: `aura/src/app/globals.css`**
*   **任务**: 定义全局样式和“灰度铁律”。
*   **核心指令**:
    *   **"读-创造"**: 请**首先阅读**`aura_legacy/src/app/globals.css`。
    *   **迁移**: 完整地、一字不差地迁移旧文件中的所有内容。这包括`@tailwind base`, `@tailwind components`, `@tailwind utilities`的声明，以及`@layer base`和`@layer utilities`中定义的所有CSS变量和自定义样式。这部分代码是我们视觉宪章的直接体现，必须被完整保留。

**4. 文件路径: `src/services/websocket/protocol.ts` (这是最重要的部分)**
*   **任务**: 从零开始，编写全新的WebSocket协议定义文件。
*   **核心指令**:
    *   **抛弃旧协议**: **严禁**参考`aura_legacy`中的旧`protocol.ts`。
    *   **精确匹配后端**: 你需要定义一个`ProtocolMessage`泛型基础接口，以及以下具体的事件类型。这些类型**必须**与NEXUS后端`OrchestratorService`发布的`UI_EVENTS`的`content`结构**完全一致**。
    *   **代码内容**:
        ```typescript
        // src/services/websocket/protocol.ts

        /**
         * AURA <-> NEXUS WebSocket Protocol V2.0
         * This file defines the strict contract for all real-time communication.
         */

        // Base structure for all messages from NEXUS to AURA
        export interface NexusEvent<T extends string, P> {
          event: T;
          run_id: string;
          payload: P;
        }

        // --- Event Payloads ---

        export interface RunStartedPayload {}

        export interface TextChunkPayload {
          chunk: string;
        }

        export interface ToolCallStartedPayload {
          tool_name: string;
          args: Record<string, any>;
        }

        export interface ToolCallFinishedPayload {
          tool_name: string;
          status: 'success' | 'error';
          result: any;
        }

        export interface RunFinishedPayload {
            status: 'completed' | 'failed' | 'timed_out';
            reason?: string;
        }
        
        export interface ErrorPayload {
          code?: number;
          message: string;
        }

        // --- Specific Event Types ---
        export type RunStartedEvent = NexusEvent<'run_started', RunStartedPayload>;
        export type TextChunkEvent = NexusEvent<'text_chunk', TextChunkPayload>;
        export type ToolCallStartedEvent = NexusEvent<'tool_call_started', ToolCallStartedPayload>;
        export type ToolCallFinishedEvent = NexusEvent<'tool_call_finished', ToolCallFinishedPayload>;
        export type RunFinishedEvent = NexusEvent<'run_finished', RunFinishedPayload>;
        export type ErrorEvent = NexusEvent<'error', ErrorPayload>;

        // Union type of all possible events from NEXUS
        export type NexusToAuraEvent =
          | RunStartedEvent
          | TextChunkEvent
          | ToolCallStartedEvent
          | ToolCallFinishedEvent
          | RunFinishedEvent
          | ErrorEvent;

        // --- Type Guards ---
        // (Implement type guards for each event type, e.g., isRunStartedEvent)

        // --- Messages from AURA to NEXUS ---
        export interface AuraToNexusMessage {
          content: string;
        }
        ```
    *   **实现类型守卫**: 为每一个具体的事件类型（如`RunStartedEvent`）编写一个类型守卫函数（如`export function isRunStartedEvent(event: NexusToAuraEvent): event is RunStartedEvent { ... }`）。

---
**交付要求：**
1.  提供更新后的`package.json`和`tailwind.config.js`的完整内容。
2.  确认`globals.css`已被完整迁移。
3.  提供全新的`src/services/websocket/protocol.ts`文件的完整内容，包括所有类型定义和类型守卫函数。

**任务开始。**