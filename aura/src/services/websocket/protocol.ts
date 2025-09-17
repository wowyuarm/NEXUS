/**
 * NEXUS WebSocket Protocol Types for AURA
 * 
 * This module defines TypeScript types for the standardized WebSocket protocol
 * used for communication between AURA frontend and NEXUS V0.2 backend.
 * 
 * Protocol Structure (from NEXUS backend):
 * {
 *   "event": "event_type_string",
 *   "run_id": "unique_run_identifier", 
 *   "payload": { ... }
 * }
 * 
 * Event Flow:
 * run_started → tool_call_started → tool_call_finished → text_chunk → run_finished
 */

// ===== Base Event Structure =====

export interface BaseNexusEvent<T extends string, P = unknown> {
  event: T;
  run_id: string;
  payload: P;
}

// ===== Event Payload Types =====

export interface RunStartedPayload {
  session_id: string;
  user_input: string;
}

export interface ToolCallStartedPayload {
  tool_name: string;
  args: Record<string, unknown>;
}

export interface ToolCallFinishedPayload {
  tool_name: string;
  status: 'success' | 'error';
  result: string;
}

export interface TextChunkPayload {
  chunk: string;
}

export interface RunFinishedPayload {
  status: 'completed' | 'error';
  final_content?: string;
}

export interface ErrorPayload {
  message: string;
  details?: string;
}

// ===== Specific Event Types =====

export type RunStartedEvent = BaseNexusEvent<'run_started', RunStartedPayload>;
export type ToolCallStartedEvent = BaseNexusEvent<'tool_call_started', ToolCallStartedPayload>;
export type ToolCallFinishedEvent = BaseNexusEvent<'tool_call_finished', ToolCallFinishedPayload>;
export type TextChunkEvent = BaseNexusEvent<'text_chunk', TextChunkPayload>;
export type RunFinishedEvent = BaseNexusEvent<'run_finished', RunFinishedPayload>;
export type ErrorEvent = BaseNexusEvent<'error', ErrorPayload>;

// ===== Union Type for All Events =====

export type NexusEvent =
  | RunStartedEvent
  | ToolCallStartedEvent
  | ToolCallFinishedEvent
  | TextChunkEvent
  | RunFinishedEvent
  | ErrorEvent;

// ===== Event Type String Union =====

export type EventType = NexusEvent['event'];

// ===== Type Guard Functions =====

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

// ===== Protocol Validation =====

export function validateNexusEvent(data: unknown): data is NexusEvent {
  if (!data || typeof data !== 'object') {
    return false;
  }

  const obj = data as Record<string, unknown>;

  // Check required fields
  if (typeof obj.event !== 'string' || typeof obj.run_id !== 'string') {
    return false;
  }

  // Check if payload exists
  if (!obj.payload || typeof obj.payload !== 'object') {
    return false;
  }

  // Check if event type is valid
  const validEventTypes: EventType[] = [
    'run_started',
    'tool_call_started', 
    'tool_call_finished',
    'text_chunk',
    'run_finished',
    'error'
  ];

  return validEventTypes.includes(obj.event as EventType);
}

// ===== Protocol Message Parsing =====

export function parseNexusEvent(messageStr: string): NexusEvent | null {
  try {
    const data = JSON.parse(messageStr);
    
    if (validateNexusEvent(data)) {
      return data as NexusEvent;
    }
    
    return null;
  } catch (error) {
    console.error('Failed to parse NEXUS event:', error);
    return null;
  }
}

// ===== Client Message Types =====

export interface ClientMessage {
  type: 'user_message';
  payload: {
    content: string;
    session_id: string;
    client_timestamp: string;
    client_timestamp_utc: string;
    client_timezone_offset: number;
  };
}

export function createClientMessage(input: string, sessionId: string, timestamp?: string): ClientMessage {
  const clientTimestamp = timestamp || new Date().toISOString();
  const clientTimezoneOffset = new Date().getTimezoneOffset();
  return {
    type: 'user_message',
    payload: {
      content: input,
      session_id: sessionId,
      client_timestamp: clientTimestamp,
      client_timestamp_utc: clientTimestamp,
      client_timezone_offset: clientTimezoneOffset
    }
  };
}


