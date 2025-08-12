// src/components/index.ts
// 统一导出所有组件层

// UI组件层 - 原子级纯UI组件
export * from './ui';

// Common组件层 - 复合/工具组件
export * from './common';

// 使用示例：
// import { MarkdownRenderer, RoleSymbol } from '@/components'; // UI组件
// import { ErrorBoundary, LoadingState } from '@/components';     // Common组件
