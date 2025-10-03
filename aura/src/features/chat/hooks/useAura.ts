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
import { useChatStore } from '../store/chatStore';
import { useCommandStore } from '@/features/command/store/commandStore';
import { useCommandLoader } from '@/features/command/hooks/useCommandLoader';
import type { Message } from '../types';
import type { CurrentRun } from '../store/chatStore';
import type {
  RunStartedPayload,
  ToolCallStartedPayload,
  ToolCallFinishedPayload,
  TextChunkPayload,
  RunFinishedPayload,
  ErrorPayload,
  CommandResultPayload
} from '../../../services/websocket/protocol';

// ===== Hook Return Type =====

export interface UseAuraReturn {
  // State
  messages: Message[];
  currentRun: CurrentRun;
  isConnected: boolean;
  isInputDisabled: boolean;
  lastError: string | null;
  toolCallHistory: Record<string, import('../types').ToolCall[]>;

  // Command State
  isCommandListOpen: boolean;
  commandQuery: string;
  selectedCommandIndex: number;
  availableCommands: Array<{ name: string; description: string; execution_target: 'client' | 'server'; usage: string; examples: string[] }>;

  // Actions
  sendMessage: (content: string) => void;
  clearMessages: () => void;
  clearError: () => void;

  // Command Actions
  openCommandList: () => void;
  closeCommandList: () => void;
  setCommandQuery: (query: string) => void;
  setSelectedCommandIndex: (index: number) => void;
  executeCommand: (command: string) => Promise<void>;

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
    toolCallHistory,
    sendMessage,
    clearMessages,
    clearError,
    handleRunStarted,
    handleToolCallStarted,
    handleToolCallFinished,
    handleTextChunk,
    handleRunFinished,
    handleError,
    handleCommandResult,
    handleConnected,
    handleDisconnected
  } = useChatStore();

  const {
    isCommandListOpen,
    commandQuery,
    selectedCommandIndex,
    availableCommands,
    openCommandList,
    closeCommandList,
    setCommandQuery,
    setLoading,
    resetSelection
  } = useCommandStore();

  // Load commands dynamically from backend after WebSocket connects
  useCommandLoader({ isConnected });

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

  const onCommandResult = useCallback((payload: CommandResultPayload) => {
    handleCommandResult(payload);
  }, [handleCommandResult]);

  const onConnected = useCallback((data: { publicKey: string }) => {
    handleConnected(data.publicKey);
  }, [handleConnected]);

  const onDisconnected = useCallback(() => {
    handleDisconnected();
  }, [handleDisconnected]);



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
    websocketManager.on('command_result', onCommandResult);
    websocketManager.on('connected', onConnected);
    websocketManager.on('disconnected', onDisconnected);

    websocketManager.on('reconnect_failed', onReconnectFailed);

    // Cleanup subscriptions on unmount
    return () => {
      websocketManager.off('run_started', onRunStarted);
      websocketManager.off('tool_call_started', onToolCallStarted);
      websocketManager.off('tool_call_finished', onToolCallFinished);
      websocketManager.off('text_chunk', onTextChunk);
      websocketManager.off('run_finished', onRunFinished);
      websocketManager.off('error', onError);
      websocketManager.off('command_result', onCommandResult);
      websocketManager.off('connected', onConnected);
      websocketManager.off('disconnected', onDisconnected);

      websocketManager.off('reconnect_failed', onReconnectFailed);
    };
  }, [
    onRunStarted,
    onToolCallStarted,
    onToolCallFinished,
    onTextChunk,
    onRunFinished,
    onError,
    onCommandResult,
    onConnected,
    onDisconnected,

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
    toolCallHistory,

    // Command State
    isCommandListOpen,
    commandQuery,
    selectedCommandIndex,
    availableCommands,

    // Actions
    sendMessage,
    clearMessages,
    clearError,

    // Command Actions
    openCommandList,
    closeCommandList,
    setCommandQuery,
    setSelectedCommandIndex: (index: number) => {
      // keep compatibility with existing UI passing absolute index
      // selection logic is managed in commandStore's selectNext/Prev when used by keyboard
      resetSelection();
      // then re-apply explicit index if valid within filtered list
      // we do not compute here to keep UI behavior simple
      useCommandStore.setState({ selectedCommandIndex: index });
    },
    executeCommand: async (command: string) => {
      try {
        setLoading(true);
        // Delegate to chat store for execution side-effects with available commands
        await useChatStore.getState().executeCommand(command, availableCommands);
        // After execution, close palette and reset query/selection to keep UI consistent
        closeCommandList();
        setCommandQuery('');
        useCommandStore.setState({ selectedCommandIndex: 0 });
      } catch (error) {
        console.error('Command execution failed:', error);
        handleError({ message: `Command execution failed: ${error}` });
      } finally {
        setLoading(false);
      }
    },

    // Connection Management
    connect,
    disconnect,

    // Computed State
    ...computedState
  };
}
