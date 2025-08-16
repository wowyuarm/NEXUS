# AURA - NEXUS Frontend

AURA是NEXUS项目的前端界面，一个基于React + TypeScript + Vite构建的现代化聊天界面。

## 🌌 设计哲学

AURA遵循"共同存在空间"的设计理念，构建一个宁静、优雅的数字交互环境。核心原则：

- **静默胜于喧哗**: 界面是宁静的背景，让思想沉淀
- **结构胜于装饰**: 美感源于元素的组织方式
- **本质胜于表象**: 构建本质，而非模拟现实
- **韵律胜于特效**: 通过微妙、有节奏的变化体现生命感

## 🎨 技术栈

- **框架**: React 19 + TypeScript
- **构建工具**: Vite
- **样式**: Tailwind CSS + 灰度调色板
- **UI组件**: shadcn/ui (深度定制)
- **动画**: Framer Motion
- **状态管理**: Zustand
- **通信**: WebSocket (与NEXUS后端)

## 📐 架构设计

### 目录结构
```
src/
├── app/                # 应用入口和全局样式
├── components/         # 可复用组件
│   ├── ui/            # 原子级UI组件
│   └── common/        # 复合组件
├── features/          # 业务功能模块
│   └── chat/         # 聊天功能
├── hooks/            # 可复用Hooks
├── services/         # 外部服务接口
└── lib/              # 工具函数
```

### 核心原则
- **逻辑与展示分离**: Container/Presenter模式
- **单一职责**: 每个组件只做一件事
- **事件驱动**: 通过WebSocket与NEXUS后端通信
- **类型安全**: 完整的TypeScript类型定义

## 🚀 快速开始

```bash
# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev

# 构建生产版本
pnpm build

# 代码检查
pnpm lint
```

## 🔧 开发指南

### 组件开发规范
1. **Container/Presenter分离**: 逻辑容器负责状态管理，展示组件负责渲染
2. **类型安全**: 所有组件都有完整的TypeScript类型定义
3. **样式组合**: 使用`cn()`函数处理条件样式
4. **灰度设计**: 严格遵循灰度调色板，禁止使用彩色

### 文件命名规范
- 组件: `PascalCase.tsx`
- Hooks: `use*.ts`
- 工具函数: `camelCase.ts`
- 类型定义: `types.ts`

## 📡 与NEXUS通信

AURA通过WebSocket与NEXUS后端进行实时通信，支持：
- 消息发送与接收
- 流式文本输出
- 工具调用状态同步
- 连接状态管理

## 🎯 核心功能

- ✅ 实时聊天界面
- ✅ 流式文本渲染
- ✅ Markdown内容支持
- ✅ 自动滚动管理
- ✅ 响应式设计
- ✅ 优雅的动画效果

## 📚 相关文档

- [前端设计哲学](src/FRONTEND_PHILOSOPHY.md)
- [组件开发指南](src/features/chat/data/TEST_GUIDE.md)

```js
export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      ...tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      ...tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      ...tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
