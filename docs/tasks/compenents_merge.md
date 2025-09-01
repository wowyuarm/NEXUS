### **任务委托单：AURA-COMPONENTS-MERGE**

**致：** 前端工程师AI

**发令者：-** “枢”，AURA项目首席AI架构师

**主题：** 合并与优化通用UI组件

**任务ID：** `COMPONENTS-MERGE`

---

**指令头 (Preamble):**
你将严格遵循《AURA-DESIGN: 交互空间设计宪章 V2.0》。本次任务是对现有UI组件进行一次战略性合并与重构，以提高代码的复用性并简化组件库。

---

#### **第一部分：任务目标 (Objective)**

你的任务是将`EmptyState.tsx`和`LoadingState.tsx`这两个功能相似的组件，合并为一个更通用、更强大的`StatusIndicator.tsx`组件。同时，你需要更新`RoleSymbol.tsx`以兼容NEXUS后端的新角色定义。

#### **第二部分：文件与核心指令 (Files & Core Instructions)**

你将对以下文件进行操作：

**1. 文件删除 (Deletion)**
*   **行动**: 在开始编码前，请**删除**以下两个文件：
    *   `src/components/common/EmptyState.tsx`
    *   `src/components/common/LoadingState.tsx`

**2. 新文件创建: `src/components/common/StatusIndicator.tsx`**
*   **任务**: 创建`StatusIndicator`组件。
*   **核心指令**:
    *   这个组件应该能够根据传入的`variant` prop，渲染不同的状态指示。
    *   **Props接口**:
        ```typescript
        interface StatusIndicatorProps {
          variant: 'loading' | 'empty' | 'error';
          message?: string;
          icon?: React.ReactNode;
          action?: React.ReactNode;
          className?: string;
        }
        ```
    *   **实现逻辑**:
        *   **`variant='loading'`**: 渲染一个符合我们“灰度中庸”美学的加载动画（可以复用`LoadingState.tsx`中的`framer-motion`代码），并显示可选的`message`。
        *   **`variant='empty'`**: 渲染一个图标（如果提供）、标题（使用`message` prop）和可选的`action`按钮。这部分逻辑可以从`EmptyState.tsx`中借鉴。
        *   **`variant='error'`**: 渲染一个错误图标（例如`⚠`）、错误信息（`message`）和可选的重试`action`。

**3. 文件重构: `src/components/ui/RoleSymbol.tsx`**
*   **任务**: 更新`RoleSymbol`以支持NEXUS V0.2的新角色定义。
*   **核心指令**:
    *   修改`RoleSymbolProps`接口，将`role`的类型从`'yu' | 'xi' | 'system'`更新为`'HUMAN' | 'AI' | 'SYSTEM' | 'TOOL'`。
    *   更新内部的`symbols`映射，以匹配新的角色：
        *   `HUMAN`: '▲' (保持不变)
        *   `AI`: '●' (保持不变)
        *   `SYSTEM`: '■' (保持不变)
        *   `TOOL`: **请为此新角色设计一个合适的、符合纯粹几何美学的符号。** 我建议使用一个简洁的符号，如 **'◆' (菱形)** 或 **'✚' (十字)**，来代表“功能”或“扩展”。请你做出最终的设计决策。
    *   确保组件的其余部分（如`isThinking`动画）保持不变。

**4. 文件更新: `src/components/common/index.ts`**
*   **任务**: 更新通用组件的导出入口。
*   **核心指令**:
    *   移除对`EmptyState`和`LoadingState`的导出。
    *   添加对新的`StatusIndicator`的导出。

---
**交付要求：**
你必须：
1.  提供`src/components/common/StatusIndicator.tsx`的完整代码。
2.  提供`src/components/ui/RoleSymbol.tsx`重构后的完整代码。
3.  提供`src/components/common/index.ts`更新后的完整代码。
4.  在`RoleSymbol.tsx`的实现中，为你为`TOOL`角色选择的符号，在代码注释中给出一句简洁的设计理由。

**任务开始。**