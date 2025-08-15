/**
 * AURA <-> NEXUS WebSocket Protocol
 * This file defines the strict contract for all real-time communication.
 */

// Base structure for all messages from NEXUS to AURA
export interface NexusEvent<T extends string, P> {
  event: T;
  run_id: string;
  payload: P;
}

// --- Event Payloads ---

export interface RunStartedPayload {}

export interface TextChunkPayload {
  chunk: string;
}

export interface ToolCallStartedPayload {
  tool_name: string;
  args: Record<string, any>;
}

export interface ToolCallFinishedPayload {
  tool_name: string;
  status: 'success' | 'error';
  result: any;
}

export interface RunFinishedPayload {
  status: 'completed' | 'failed' | 'timed_out';
  reason?: string;
}

export interface ErrorPayload {
  code?: number;
  message: string;
}

// --- Specific Event Types ---
export type RunStartedEvent = NexusEvent<'run_started', RunStartedPayload>;
export type TextChunkEvent = NexusEvent<'text_chunk', TextChunkPayload>;
export type ToolCallStartedEvent = NexusEvent<'tool_call_started', ToolCallStartedPayload>;
export type ToolCallFinishedEvent = NexusEvent<'tool_call_finished', ToolCallFinishedPayload>;
export type RunFinishedEvent = NexusEvent<'run_finished', RunFinishedPayload>;
export type ErrorEvent = NexusEvent<'error', ErrorPayload>;

// Union type of all possible events from NEXUS
export type NexusToAuraEvent =
  | RunStartedEvent
  | TextChunkEvent
  | ToolCallStartedEvent
  | ToolCallFinishedEvent
  | RunFinishedEvent
  | ErrorEvent;

// --- Type Guards ---
export function isRunStartedEvent(event: NexusToAuraEvent): event is RunStartedEvent {
  return event.event === 'run_started';
}

export function isTextChunkEvent(event: NexusToAuraEvent): event is TextChunkEvent {
  return event.event === 'text_chunk' && typeof (event as TextChunkEvent).payload?.chunk === 'string';
}

export function isToolCallStartedEvent(event: NexusToAuraEvent): event is ToolCallStartedEvent {
  return (
    event.event === 'tool_call_started' &&
    typeof (event as ToolCallStartedEvent).payload?.tool_name === 'string' &&
    typeof (event as ToolCallStartedEvent).payload?.args === 'object'
  );
}

export function isToolCallFinishedEvent(event: NexusToAuraEvent): event is ToolCallFinishedEvent {
  const payload = (event as ToolCallFinishedEvent).payload as ToolCallFinishedPayload;
  return (
    event.event === 'tool_call_finished' &&
    typeof payload?.tool_name === 'string' &&
    (payload?.status === 'success' || payload?.status === 'error')
  );
}

export function isRunFinishedEvent(event: NexusToAuraEvent): event is RunFinishedEvent {
  const payload = (event as RunFinishedEvent).payload as RunFinishedPayload;
  return (
    event.event === 'run_finished' &&
    (payload?.status === 'completed' || payload?.status === 'failed' || payload?.status === 'timed_out')
  );
}

export function isErrorEvent(event: NexusToAuraEvent): event is ErrorEvent {
  const payload = (event as ErrorEvent).payload as ErrorPayload;
  return event.event === 'error' && typeof payload?.message === 'string';
}

// --- Messages from AURA to NEXUS ---
export interface AuraToNexusMessage {
  content: string;
}
