// src/features/chat/types.ts
export type MessageRole = 'HUMAN' | 'AI' | 'SYSTEM' | 'TOOL';

export interface ToolCall {
  id: string;
  toolName: string;
  args: Record<string, unknown>;
  status: 'running' | 'completed' | 'error';
  result?: string;
  startTime: Date;
  endTime?: Date;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date | string;
  runId?: string;
  metadata?: {
    isStreaming?: boolean;
    [key: string]: unknown;
  };
  // 兼容store中的字段
  isStreaming?: boolean;
  // 工具调用信息 - 支持在同一消息内包含多个工具调用
  toolCalls?: ToolCall[];
}
