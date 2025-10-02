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
  // 兼容store中的字段
  isStreaming?: boolean;
  // 工具调用信息 - 支持在同一消息内包含多个工具调用
  toolCalls?: ToolCall[];
  // 当工具卡片需要插入到文本中间时，记录首次工具启动时的文本分割位置
  toolInsertIndex?: number;
}
