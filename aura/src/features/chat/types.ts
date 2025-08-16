// src/features/chat/types.ts
export type MessageRole = 'HUMAN' | 'AI' | 'SYSTEM' | 'TOOL';

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
}
