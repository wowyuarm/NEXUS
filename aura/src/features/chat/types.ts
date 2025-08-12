// src/features/chat/types.ts
export type MessageRole = 'yu' | 'xi' | 'system';

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
