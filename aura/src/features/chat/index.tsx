// src/features/chat/index.tsx
// 聊天功能模块入口点
//
// 职责：
// - 导出聊天功能的主要组件
// - 提供统一的对外接口
// - 保持向后兼容性（ChatView别名）
//
// 架构说明：
// - ChatContainer: 逻辑容器，负责状态管理和业务逻辑
// - ChatView: 纯展示组件，负责UI渲染和用户交互
// - 通过别名导出保持API稳定性

export { ChatContainer as ChatView } from './ChatContainer';
