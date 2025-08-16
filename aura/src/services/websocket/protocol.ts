// src/services/websocket/protocol.ts

/**
 * WebSocket Protocol Types for Xi ContextOS
 * 
 * This module defines TypeScript types for the standardized WebSocket protocol
 * used for communication between the Xi frontend and backend systems.
 * 
 * Protocol Structure:
 * {
 *   "type": "event_type_string",
 *   "payload": { ... },
 *   "metadata": {
 *     "message_id": "unique_message_id_for_this_response_stream",
 *     "timestamp": "iso_8601_timestamp"
 *   }
 * }
 * 
 * Event Flow:
 * stream_start → tool_call → text_chunk(s) → stream_end
 */

// 定义基础消息结构
export interface ProtocolMessage<T extends string, P> {
  type: T;
  payload: P;
  metadata: {
    message_id: string;
    timestamp: string;
  };
}

// 定义各种事件的Payload类型
export interface StreamStartPayload {
  session_id: string;
  input_message_id: string;
}

export interface ToolCallPayload {
  tool_name: string;
  arguments: Record<string, any>;
}

export interface ToolExecutionStartPayload {
  tool_name: string;
  arguments: Record<string, any>;
}

export interface ToolExecutionResultPayload {
  tool_name: string;
  status: 'success' | 'error';
  result?: string;
  error?: string;
  execution_time: number;
}

export interface TextChunkPayload {
  chunk: string;
}

export interface StreamEndPayload {
  final_content?: string;
}

export interface ErrorPayload {
  code?: number;
  message: string;
}

// V0.2预留：后台任务事件类型
export interface BackgroundTaskStartedPayload {
  task_id: string;
  task_type: string;
  description: string;
}

export interface BackgroundTaskProgressPayload {
  task_id: string;
  progress: number; // 0.0-1.0
  message: string;
}

export interface BackgroundTaskCompletedPayload {
  task_id: string;
  result: Record<string, any>;
}

// 定义具体的事件类型
export type StreamStartEvent = ProtocolMessage<'stream_start', StreamStartPayload>;
export type ToolCallEvent = ProtocolMessage<'tool_call', ToolCallPayload>;
export type ToolExecutionStartEvent = ProtocolMessage<'tool_execution_start', ToolExecutionStartPayload>;
export type ToolExecutionResultEvent = ProtocolMessage<'tool_execution_result', ToolExecutionResultPayload>;
export type TextChunkEvent = ProtocolMessage<'text_chunk', TextChunkPayload>;
export type StreamEndEvent = ProtocolMessage<'stream_end', StreamEndPayload>;
export type ErrorEvent = ProtocolMessage<'error', ErrorPayload>;

// V0.2预留：后台任务事件类型
export type BackgroundTaskStartedEvent = ProtocolMessage<'background_task_started', BackgroundTaskStartedPayload>;
export type BackgroundTaskProgressEvent = ProtocolMessage<'background_task_progress', BackgroundTaskProgressPayload>;
export type BackgroundTaskCompletedEvent = ProtocolMessage<'background_task_completed', BackgroundTaskCompletedPayload>;

// 所有可能的事件联合类型
export type XiSystemEvent =
  | StreamStartEvent
  | ToolCallEvent
  | ToolExecutionStartEvent
  | ToolExecutionResultEvent
  | TextChunkEvent
  | StreamEndEvent
  | ErrorEvent
  | BackgroundTaskStartedEvent
  | BackgroundTaskProgressEvent
  | BackgroundTaskCompletedEvent;

// 事件类型字符串联合类型（用于类型守卫）
export type EventType = XiSystemEvent['type'];

// 类型守卫函数
export function isStreamStartEvent(event: XiSystemEvent): event is StreamStartEvent {
  return event.type === 'stream_start';
}

export function isToolCallEvent(event: XiSystemEvent): event is ToolCallEvent {
  return event.type === 'tool_call';
}

export function isToolExecutionStartEvent(event: XiSystemEvent): event is ToolExecutionStartEvent {
  return event.type === 'tool_execution_start';
}

export function isToolExecutionResultEvent(event: XiSystemEvent): event is ToolExecutionResultEvent {
  return event.type === 'tool_execution_result';
}

export function isTextChunkEvent(event: XiSystemEvent): event is TextChunkEvent {
  return event.type === 'text_chunk';
}

export function isStreamEndEvent(event: XiSystemEvent): event is StreamEndEvent {
  return event.type === 'stream_end';
}

export function isErrorEvent(event: XiSystemEvent): event is ErrorEvent {
  return event.type === 'error';
}

export function isBackgroundTaskStartedEvent(event: XiSystemEvent): event is BackgroundTaskStartedEvent {
  return event.type === 'background_task_started';
}

export function isBackgroundTaskProgressEvent(event: XiSystemEvent): event is BackgroundTaskProgressEvent {
  return event.type === 'background_task_progress';
}

export function isBackgroundTaskCompletedEvent(event: XiSystemEvent): event is BackgroundTaskCompletedEvent {
  return event.type === 'background_task_completed';
}

// 协议消息验证函数
export function validateProtocolMessage(data: any): data is XiSystemEvent {
  if (!data || typeof data !== 'object') {
    return false;
  }

  // 检查必需字段
  if (!data.type || typeof data.type !== 'string') {
    return false;
  }

  if (!data.payload || typeof data.payload !== 'object') {
    return false;
  }

  if (!data.metadata || typeof data.metadata !== 'object') {
    return false;
  }

  if (!data.metadata.message_id || typeof data.metadata.message_id !== 'string') {
    return false;
  }

  if (!data.metadata.timestamp || typeof data.metadata.timestamp !== 'string') {
    return false;
  }

  // 检查事件类型是否有效
  const validEventTypes: EventType[] = [
    'stream_start',
    'tool_call',
    'tool_execution_start',
    'tool_execution_result',
    'text_chunk',
    'stream_end',
    'error',
    'background_task_started',
    'background_task_progress',
    'background_task_completed'
  ];

  return validEventTypes.includes(data.type as EventType);
}

// 协议消息解析函数
export function parseProtocolMessage(messageStr: string): XiSystemEvent | null {
  try {
    const data = JSON.parse(messageStr);
    
    if (validateProtocolMessage(data)) {
      return data as XiSystemEvent;
    }
    
    return null;
  } catch (error) {
    console.error('Failed to parse protocol message:', error);
    return null;
  }
}

// 用于发送给后端的消息类型
export interface ClientMessage {
  yu_input: string;
  session_id?: string;
}

// WebSocket连接状态类型
export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

// WebSocket管理器配置类型
export interface WebSocketManagerConfig {
  url: string;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number; // 毫秒
  reconnectBackoffBase?: number; // 毫秒
  enableHeartbeat?: boolean;
  enableAutoReconnect?: boolean;
}

// 连接状态变化事件类型
export interface ConnectionStatusChangeEvent {
  status: WebSocketStatus;
  timestamp: string;
  reconnectAttempts?: number;
  error?: string;
}
