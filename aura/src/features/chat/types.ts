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
  /** Text insertion index when this tool call started (for interleaving) */
  insertIndex?: number;
}

/**
 * System message content structure
 * - For pending state: only command is present
 * - For completed state: both command and result are present
 */
export interface SystemMessageContent {
  command: string;
  result?: string | Record<string, unknown>;
}

export interface Message {
  id: string;
  role: MessageRole;
  // For SYSTEM role, content can be structured object; otherwise string
  content: string | SystemMessageContent;
  timestamp: Date | string;
  runId?: string;
  metadata?: {
    isStreaming?: boolean;
    status?: 'pending' | 'completed';
    commandResult?: Record<string, unknown>;
    [key: string]: unknown;
  };
  // Compatible with fields in the store
  isStreaming?: boolean;
  // Tool call information - supports multiple tool calls within the same message
  toolCalls?: ToolCall[];
  // When tool cards need to be inserted in the middle of text, records the text split position when the first tool starts
  toolInsertIndex?: number;
}
