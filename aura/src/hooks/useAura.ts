// aura/src/hooks/useAura.ts
// Single bridge between WebSocketManager (senses) and auraStore (mind).

import { useEffect, useMemo } from 'react';
import websocketManager from '../services/websocket/manager';
import type { RunStartedEvent, TextChunkEvent, ToolCallStartedEvent, ToolCallFinishedEvent, RunFinishedEvent, ErrorEvent } from '../services/websocket/protocol';
import { useAuraStore } from '../features/chat/store/auraStore';
import type { WebSocketStatus } from '../services/websocket/manager';

export function useAura() {
  const messages = useAuraStore((s) => s.messages);
  const connectionStatus = useAuraStore((s) => s.connectionStatus);
  const currentRun = useAuraStore((s) => s.currentRun);

  useEffect(() => {
    // Connect on mount if not connected
    if (websocketManager.getStatus() === 'disconnected') {
      websocketManager.connect();
    }

    const setConn = useAuraStore.getState().setConnectionStatus;
    const onStatus = (status: unknown) => setConn(status as WebSocketStatus);

    const onRunStarted = (e: unknown) => useAuraStore.getState().handleRunStarted(e as RunStartedEvent);
    const onTextChunk = (e: unknown) => useAuraStore.getState().handleTextChunk(e as TextChunkEvent);
    const onToolStart = (e: unknown) => useAuraStore.getState().handleToolCallStarted(e as ToolCallStartedEvent);
    const onToolFinish = (e: unknown) => useAuraStore.getState().handleToolCallFinished(e as ToolCallFinishedEvent);
    const onRunFinished = (e: unknown) => useAuraStore.getState().handleRunFinished(e as RunFinishedEvent);
    const onError = (e: unknown) => useAuraStore.getState().handleError(e as ErrorEvent);

    websocketManager.emitter.on('status', onStatus);
    websocketManager.emitter.on('run_started', onRunStarted);
    websocketManager.emitter.on('text_chunk', onTextChunk);
    websocketManager.emitter.on('tool_call_started', onToolStart);
    websocketManager.emitter.on('tool_call_finished', onToolFinish);
    websocketManager.emitter.on('run_finished', onRunFinished);
    websocketManager.emitter.on('error', onError);

    return () => {
      websocketManager.emitter.off('status', onStatus);
      websocketManager.emitter.off('run_started', onRunStarted);
      websocketManager.emitter.off('text_chunk', onTextChunk);
      websocketManager.emitter.off('tool_call_started', onToolStart);
      websocketManager.emitter.off('tool_call_finished', onToolFinish);
      websocketManager.emitter.off('run_finished', onRunFinished);
      websocketManager.emitter.off('error', onError);
    };
  }, []);

  const sendMessage = (content: string) => {
    websocketManager.sendMessage({ content });
  };

  return useMemo(() => ({ messages, connectionStatus, currentRun, sendMessage }), [
    messages,
    connectionStatus,
    currentRun,
  ]);
}
