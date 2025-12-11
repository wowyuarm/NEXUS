/**
 * NEXUS SSE Protocol Types for AURA
 * 
 * This module defines the protocol types for SSE communication.
 * These types define the structure of events sent from NEXUS backend to AURA frontend.
 */

// ===== Base Event Structure =====

export interface BaseNexusEvent<T extends string = string, P = unknown> {
  event: T;
  run_id: string;
  payload: P;
}

// ===== Payload Types =====

export interface RunStartedPayload {
  owner_key: string;
  user_input: string;
}

export interface ToolCallStartedPayload {
  tool_name: string;
  tool_call_id?: string;
  args: Record<string, unknown>;
}

export interface ToolCallFinishedPayload {
  tool_name: string;
  tool_call_id?: string;
  status: 'success' | 'error';
  result: string;
}

export interface TextChunkPayload {
  chunk: string;
  role?: string;
  is_final?: boolean;
}

export interface RunFinishedPayload {
  status: 'completed' | 'error';
  final_content?: string;
}

export interface ErrorPayload {
  message: string;
  details?: string;
}

export interface CommandResultPayload {
  command: string;
  result: {
    status: 'success' | 'error';
    message: string;
    data?: Record<string, unknown>;
  };
}

export interface ConnectionStatePayload {
  visitor: boolean;
}

// ===== Event Types =====

export type RunStartedEvent = BaseNexusEvent<'run_started', RunStartedPayload>;
export type ToolCallStartedEvent = BaseNexusEvent<'tool_call_started', ToolCallStartedPayload>;
export type ToolCallFinishedEvent = BaseNexusEvent<'tool_call_finished', ToolCallFinishedPayload>;
export type TextChunkEvent = BaseNexusEvent<'text_chunk', TextChunkPayload>;
export type RunFinishedEvent = BaseNexusEvent<'run_finished', RunFinishedPayload>;
export type ErrorEvent = BaseNexusEvent<'error', ErrorPayload>;
export type CommandResultEvent = BaseNexusEvent<'command_result', CommandResultPayload>;

export type NexusEvent =
  | RunStartedEvent
  | ToolCallStartedEvent
  | ToolCallFinishedEvent
  | TextChunkEvent
  | RunFinishedEvent
  | ErrorEvent
  | CommandResultEvent
  | BaseNexusEvent<'connection_state', ConnectionStatePayload>;

export type EventType = NexusEvent['event'];

// ===== Type Guards =====

export function isRunStartedEvent(event: NexusEvent): event is RunStartedEvent {
  return event.event === 'run_started';
}

export function isToolCallStartedEvent(event: NexusEvent): event is ToolCallStartedEvent {
  return event.event === 'tool_call_started';
}

export function isToolCallFinishedEvent(event: NexusEvent): event is ToolCallFinishedEvent {
  return event.event === 'tool_call_finished';
}

export function isTextChunkEvent(event: NexusEvent): event is TextChunkEvent {
  return event.event === 'text_chunk';
}

export function isRunFinishedEvent(event: NexusEvent): event is RunFinishedEvent {
  return event.event === 'run_finished';
}

export function isErrorEvent(event: NexusEvent): event is ErrorEvent {
  return event.event === 'error';
}

export function isCommandResultEvent(event: NexusEvent): event is CommandResultEvent {
  return event.event === 'command_result';
}

export function validateNexusEvent(data: unknown): data is NexusEvent {
  if (typeof data !== 'object' || data === null) return false;
  const obj = data as Record<string, unknown>;
  return typeof obj.event === 'string' && typeof obj.run_id === 'string' && typeof obj.payload === 'object';
}

export function parseNexusEvent(json: string): NexusEvent | null {
  try {
    const data = JSON.parse(json);
    if (validateNexusEvent(data)) return data;
    return null;
  } catch {
    return null;
  }
}

// ===== SSE-specific types =====

/**
 * Chat request payload for POST /chat
 */
export interface ChatRequest {
  content: string;
  client_timestamp_utc?: string;
  client_timezone_offset?: number;
}

/**
 * Command execution request for POST /commands/execute
 */
export interface CommandExecuteRequest {
  command: string;
  args?: string[];
  auth?: {
    publicKey: string;
    signature: string;
  };
}

/**
 * Command execution response
 */
export interface CommandExecuteResponse {
  status: 'success' | 'error';
  message: string;
  data?: Record<string, unknown>;
}
