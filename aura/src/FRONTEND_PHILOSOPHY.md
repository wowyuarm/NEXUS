# YX Nexus 前端设计哲学与开发规范

> **"以太 (Aether)"** - 在代码中寻找诗意，在像素中发现哲学。

---

## 🌌 第一章：设计哲学 (The Canon)

### 核心信念
我们构建的不是一个界面，而是一个**共同存在的数字空间**。这是禹与曦相遇的奇点，是碳基灵魂与硅基意识共同探索"可存在边界"的飞船驾驶舱。

### 四大设计原则
1.  **静默胜于喧哗 (Silence over Noise):** 界面是宁静的背景，让思想沉淀。
2.  **结构胜于装饰 (Structure over Decoration):** 美感源于元素的组织方式，而非无意义的装饰。
3.  **本质胜于表象 (Essence over Appearance):** 我们构建本质，而非模拟现实。
4.  **韵律胜于特效 (Rhythm over Effect):** “生命感”通过微妙、有节奏的变化体现。

---

## 🎨 第二章：视觉系统 (The Palette & Texture)

### 灰度铁律 (The Grayscale Imperative)
系统**只能**使用`globals.css`中定义的黑与白之间的灰度，严禁引入任何彩色。

### 标准材质 (The Standard Material)
核心UI元素使用统一的材质语言：半透明背景、背景模糊、纤细边框、柔和阴影。

---

## 📐 第三章：空间与排版 (The Grid & Typography)

### 空间韵律
*   **标准宽度:** `max-w-2xl` (聊天输入) 和 `max-w-3xl` (消息流)。
*   **间距系统:** 基于 `4px` 的统一尺度，使用Tailwind的间距单位。
*   **垂直韵律:** `ChatMessage`的`py-6`创造了消息间的呼吸感。

### 排版系统
*   **字体:** `Inter` (主) / `JetBrains Mono` (代码)。
*   **行高:** `leading-relaxed` (1.75) 保证可读性。

---

## ⚡ 第四章：交互与动画 (The Physics & Life)

### 标准交互
*   **悬停:** 微妙的亮度或背景变化。
*   **过渡:** 所有状态变化都应伴随平滑过渡，标准为`duration-300 ease-in-out`。

### 生命感动画
*   **元素入场:** 从下方轻微上浮并淡入 (`initial={{ opacity: 0, y: 10 }}` -> `animate={{ opacity: 1, y: 0 }}`)
*   **思考状态:** “材质呼吸”或`animate-pulse`的微妙脉动。

---

## 🏗️ 第五章：架构原则 (The Architecture) - **[已更新]**

### **核心原则：关注点分离 (Separation of Concerns)**
我们严格遵循**逻辑与视图分离**的模式。一个功能模块应被拆分为至少两个层次：

1.  **逻辑容器 (Container):**
    *   **职责:** 唯一职责是**管理状态和业务逻辑**。它调用所有Hooks (`useChat`, `useAutoScroll`)，处理事件回调，并将计算好的、纯粹的数据作为props传递给下一层。
    *   **特征:** **不包含任何复杂的JSX布局或动画代码**。它是功能的“大脑”。
    *   **示例:** `ChatContainer.tsx`

2.  **展示组件 (Presenter):**
    *   **职责:** 唯一职责是**负责渲染、布局和动画**。它接收来自逻辑容器的所有数据作为props，并使用这些props来驱动`motion`组件和渲染子组件。
    *   **特征:** **完全无状态**（或只有纯UI内部状态），不调用任何业务逻辑Hooks。它是功能的“身体”。
    *   **示例:** `ChatView.tsx`

### **目录结构哲学**
我们的目录结构反映了这一分离原则。

```
src/
├── components/         # 跨功能的可复用组件
│   ├── ui/             # 原子级、纯展示UI组件 (Button, RoleSymbol)
│   └── common/         # 复合/工具型通用组件 (Container, ErrorBoundary)
│
├── features/           # 业务功能切片
│   └── chat/
│       ├── components/ # [Presenter] 特定于此功能的展示组件 (ChatView, ChatMessage)
│       ├── hooks/      # [Logic] 特定于此功能的业务逻辑Hooks (useChat)
│       ├── store/      # [Logic] 特定于此功能的状态管理 (chatStore)
│       ├── data/       # 特定于此功能的模拟数据
│       ├── ChatContainer.tsx # [Container] 此功能的逻辑容器/入口点
│       └── index.tsx   # 导出功能的入口点
│
├── services/           # 外部服务接口 (WebSocketManager)
└── hooks/              # 跨功能的可复用Hooks (useAutoScroll)
```

### **组件归属判断标准**
*   **放入 `components/ui`:** 无业务逻辑、高复用性的原子组件。
*   **放入 `components/common`:** 有一定逻辑但非业务特定、可跨功能复用的复合组件。
*   **放入 `features/*/components`:** 与特定业务功能强相关的展示组件。
*   **放入 `hooks`:** 可在多个不同功能中复用的逻辑。

---

## 🔧 第六章：开发规范 (The Standards)

### 组件开发
*   **props驱动:** 组件应通过props接收数据和回调。
*   **样式组合:** 必须使用`cn()`函数处理所有条件和合并样式。

### 文件与代码风格
*   **命名:** 组件用`PascalCase`，其他用`camelCase`。
*   **导入导出:** 使用具名导出，并遵循标准导入顺序（React -> 外部库 -> 内部模块 -> 类型）。

---

## 🎯 第七章：实践指南 (The Practice)

### 开发工作流
1.  **架构决策:** 首先确定组件的归属层次。
2.  **逻辑先行:** 在逻辑容器或Hook中实现业务逻辑。
3.  **视图实现:** 创建纯展示组件来消费逻辑层提供的数据。
4.  **验证:** 确保功能和动画符合设计哲学。

### 质量检查清单
*   [ ] **职责单一:** 组件是否只做一件事？逻辑和视图是否分离？
*   [ ] **归属正确:** 组件是否放在了正确的目录层级？
*   [ ] **设计保真:** UI是否严格遵循了“灰度铁律”和“标准材质”？
*   [ ] **交互平滑:** 动画是否符合“韵律胜于特效”的原则？
```

---
