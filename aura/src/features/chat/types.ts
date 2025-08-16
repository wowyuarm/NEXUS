// src/features/chat/types.ts
export type MessageRole = 'HUMAN' | 'AI' | 'SYSTEM' | 'TOOL';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  metadata?: {
    isStreaming?: boolean;
    [key: string]: any;
  };
}
