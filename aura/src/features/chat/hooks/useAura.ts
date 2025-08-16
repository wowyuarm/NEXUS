/**
 * useAura Hook - The Neural Bridge
 * 
 * This hook serves as the "controller" layer that connects WebSocket communication,
 * Zustand state management, and UI components. It orchestrates the complete data flow
 * and provides a clean interface for React components.
 * 
 * Architecture:
 * - Subscribes to WebSocket events and routes them to store actions
 * - Manages connection lifecycle and error handling
 * - Exposes state and actions to UI components
 * - Handles initialization and cleanup
 */

import { useEffect, useCallback, useMemo } from 'react';
import { websocketManager } from '../../../services/websocket/manager';
import { useAuraStore } from '../store/auraStore';
import type {
  RunStartedPayload,
  ToolCallStartedPayload,
  ToolCallFinishedPayload,
  TextChunkPayload,
  RunFinishedPayload,
  ErrorPayload,
  WebSocketResponse
} from '../../../services/websocket/protocol';

// ===== Hook Return Type =====

export interface UseAuraReturn {
  // State
  messages: any[];
  currentRun: any;
  isConnected: boolean;
  isInputDisabled: boolean;
  lastError: string | null;
  
  // Actions
  sendMessage: (content: string) => void;
  clearMessages: () => void;
  clearError: () => void;
  
  // Connection Management
  connect: () => Promise<void>;
  disconnect: () => void;
  
  // Computed State
  isThinking: boolean;
  isToolRunning: boolean;
  isStreaming: boolean;
  hasActiveRun: boolean;
}

// ===== Main Hook Implementation =====

export function useAura(): UseAuraReturn {
  // ===== Store State & Actions =====
  
  const {
    messages,
    currentRun,
    isConnected,
    isInputDisabled,
    lastError,
    sendMessage,
    clearMessages,
    clearError,
    handleRunStarted,
    handleToolCallStarted,
    handleToolCallFinished,
    handleTextChunk,
    handleRunFinished,
    handleError,
    handleConnected,
    handleDisconnected
  } = useAuraStore();

  // ===== WebSocket Event Handlers =====

  const onRunStarted = useCallback((payload: RunStartedPayload) => {
    handleRunStarted(payload);
  }, [handleRunStarted]);

  const onToolCallStarted = useCallback((payload: ToolCallStartedPayload) => {
    handleToolCallStarted(payload);
  }, [handleToolCallStarted]);

  const onToolCallFinished = useCallback((payload: ToolCallFinishedPayload) => {
    handleToolCallFinished(payload);
  }, [handleToolCallFinished]);

  const onTextChunk = useCallback((payload: TextChunkPayload) => {
    handleTextChunk(payload);
  }, [handleTextChunk]);

  const onRunFinished = useCallback((payload: RunFinishedPayload) => {
    handleRunFinished(payload);
  }, [handleRunFinished]);

  const onError = useCallback((payload: ErrorPayload) => {
    handleError(payload);
  }, [handleError]);

  const onConnected = useCallback((data: { sessionId: string }) => {
    handleConnected(data.sessionId);
  }, [handleConnected]);

  const onDisconnected = useCallback(() => {
    handleDisconnected();
  }, [handleDisconnected]);

  const onWebSocketResponse = useCallback((response: WebSocketResponse) => {
    console.log('Received WebSocket response:', response);
    // Handle legacy response format if needed
  }, []);

  const onReconnectFailed = useCallback(() => {
    handleError({ message: 'Failed to reconnect to NEXUS after multiple attempts' });
  }, [handleError]);

  // ===== WebSocket Subscription Effect =====

  useEffect(() => {
    // Subscribe to all WebSocket events
    websocketManager.on('run_started', onRunStarted);
    websocketManager.on('tool_call_started', onToolCallStarted);
    websocketManager.on('tool_call_finished', onToolCallFinished);
    websocketManager.on('text_chunk', onTextChunk);
    websocketManager.on('run_finished', onRunFinished);
    websocketManager.on('error', onError);
    websocketManager.on('connected', onConnected);
    websocketManager.on('disconnected', onDisconnected);
    websocketManager.on('websocket_response', onWebSocketResponse);
    websocketManager.on('reconnect_failed', onReconnectFailed);

    // Cleanup subscriptions on unmount
    return () => {
      websocketManager.off('run_started', onRunStarted);
      websocketManager.off('tool_call_started', onToolCallStarted);
      websocketManager.off('tool_call_finished', onToolCallFinished);
      websocketManager.off('text_chunk', onTextChunk);
      websocketManager.off('run_finished', onRunFinished);
      websocketManager.off('error', onError);
      websocketManager.off('connected', onConnected);
      websocketManager.off('disconnected', onDisconnected);
      websocketManager.off('websocket_response', onWebSocketResponse);
      websocketManager.off('reconnect_failed', onReconnectFailed);
    };
  }, [
    onRunStarted,
    onToolCallStarted,
    onToolCallFinished,
    onTextChunk,
    onRunFinished,
    onError,
    onConnected,
    onDisconnected,
    onWebSocketResponse,
    onReconnectFailed
  ]);

  // ===== Connection Management =====

  const connect = useCallback(async () => {
    try {
      await websocketManager.connect();
    } catch (error) {
      console.error('Failed to connect to NEXUS:', error);
      handleError({ 
        message: 'Failed to connect to NEXUS. Please check your connection.' 
      });
    }
  }, [handleError]);

  const disconnect = useCallback(() => {
    websocketManager.disconnect();
  }, []);

  // ===== Auto-connect Effect =====

  useEffect(() => {
    // Auto-connect on mount
    connect();

    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // ===== Computed State =====

  const computedState = useMemo(() => ({
    isThinking: currentRun.status === 'thinking',
    isToolRunning: currentRun.status === 'tool_running',
    isStreaming: currentRun.status === 'streaming_text',
    hasActiveRun: currentRun.runId !== null
  }), [currentRun.status, currentRun.runId]);

  // ===== Return Hook Interface =====

  return {
    // State
    messages,
    currentRun,
    isConnected,
    isInputDisabled,
    lastError,
    
    // Actions
    sendMessage,
    clearMessages,
    clearError,
    
    // Connection Management
    connect,
    disconnect,
    
    // Computed State
    ...computedState
  };
}
