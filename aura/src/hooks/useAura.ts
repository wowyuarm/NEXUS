// aura/src/hooks/useAura.ts
// Single bridge between WebSocketManager (senses) and auraStore (mind).

import { useEffect, useMemo } from 'react';
import websocketManager from '../services/websocket/manager';
import type { NexusToAuraEvent } from '../services/websocket/protocol';
import { useAuraStore } from '../features/chat/store/auraStore';

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
    const onStatus = (status: any) => setConn(status);

    const onRunStarted = (e: NexusToAuraEvent) => useAuraStore.getState().handleRunStarted(e as any);
    const onTextChunk = (e: NexusToAuraEvent) => useAuraStore.getState().handleTextChunk(e as any);
    const onToolStart = (e: NexusToAuraEvent) => useAuraStore.getState().handleToolCallStarted(e as any);
    const onToolFinish = (e: NexusToAuraEvent) => useAuraStore.getState().handleToolCallFinished(e as any);
    const onRunFinished = (e: NexusToAuraEvent) => useAuraStore.getState().handleRunFinished(e as any);
    const onError = (e: NexusToAuraEvent) => useAuraStore.getState().handleError(e as any);

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
