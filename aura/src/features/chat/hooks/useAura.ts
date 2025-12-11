/**
 * useAura Hook - The Neural Bridge
 * 
 * This hook serves as the "controller" layer that connects SSE/HTTP communication,
 * Zustand state management, and UI components. It orchestrates the complete data flow
 * and provides a clean interface for React components.
 * 
 * Architecture:
 * - Subscribes to SSE stream events and routes them to store actions
 * - Manages connection lifecycle and error handling
 * - Exposes state and actions to UI components
 * - Handles initialization and cleanup
 */

import { useEffect, useCallback, useMemo } from 'react';
import { streamManager } from '../../../services/stream/manager';
import { useChatStore } from '../store/chatStore';
import { useCommandStore } from '@/features/command/store/commandStore';
import { useCommandLoader } from '@/features/command/hooks/useCommandLoader';
import type { Command } from '@/features/command/command.types';
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
} from '../../../services/stream/protocol';

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
  isPaletteOpen: boolean;
  query: string;
  selectedCommandIndex: number;
  availableCommands: Command[];

  // Actions
  sendMessage: (content: string) => void;
  clearMessages: () => void;
  clearError: () => void;

  // Command Actions
  openPalette: () => void;
  closePalette: () => void;
  setQuery: (query: string) => void;
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
    isPaletteOpen,
    query,
    selectedCommandIndex,
    availableCommands,
    openPalette,
    closePalette,
    setQuery,
    setLoading,
    resetSelection
  } = useCommandStore();

  // Load commands from backend REST API (no longer depends on WebSocket connection)
  useCommandLoader();  

  // ===== SSE Event Handlers =====

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

  const onConnectionState = useCallback((payload: { visitor: boolean }) => {
    useChatStore.getState().handleConnectionState(!!payload.visitor);
  }, []);

  const onDisconnected = useCallback(() => {
    handleDisconnected();
  }, [handleDisconnected]);



  const onReconnectFailed = useCallback(() => {
    handleError({ message: 'Failed to reconnect to NEXUS after multiple attempts' });
  }, [handleError]);

  // ===== SSE Subscription Effect =====

  useEffect(() => {
    // Subscribe to all SSE events
    streamManager.on('run_started', onRunStarted);
    streamManager.on('tool_call_started', onToolCallStarted);
    streamManager.on('tool_call_finished', onToolCallFinished);
    streamManager.on('text_chunk', onTextChunk);
    streamManager.on('run_finished', onRunFinished);
    streamManager.on('error', onError);
    streamManager.on('command_result', onCommandResult);
    streamManager.on('connected', onConnected);
    streamManager.on('connection_state', onConnectionState);
    streamManager.on('disconnected', onDisconnected);

    streamManager.on('reconnect_failed', onReconnectFailed);

    // Cleanup subscriptions on unmount
    return () => {
      streamManager.off('run_started', onRunStarted);
      streamManager.off('tool_call_started', onToolCallStarted);
      streamManager.off('tool_call_finished', onToolCallFinished);
      streamManager.off('text_chunk', onTextChunk);
      streamManager.off('run_finished', onRunFinished);
      streamManager.off('error', onError);
      streamManager.off('command_result', onCommandResult);
      streamManager.off('connected', onConnected);
      streamManager.off('connection_state', onConnectionState);
      streamManager.off('disconnected', onDisconnected);

      streamManager.off('reconnect_failed', onReconnectFailed);
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
    onConnectionState,
    onDisconnected,

    onReconnectFailed
  ]);

  // ===== Connection Management =====

  const connect = useCallback(async () => {
    try {
      await streamManager.connect();
    } catch (error) {
      console.error('Failed to connect to NEXUS:', error);
      handleError({ 
        message: 'Failed to connect to NEXUS. Please check your connection.' 
      });
    }
  }, [handleError]);

  const disconnect = useCallback(() => {
    streamManager.disconnect();
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
    isPaletteOpen,
    query,
    selectedCommandIndex,
    availableCommands,

    // Actions
    sendMessage,
    clearMessages,
    clearError,

    // Command Actions
    openPalette,
    closePalette,
    setQuery,
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
        closePalette();
        setQuery('');
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
