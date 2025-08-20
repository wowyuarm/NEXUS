/**
 * AURA Zustand Store - The Single Source of Truth
 *
 * This store precisely mirrors the NEXUS backend state and provides
 * atomic actions for updating the UI state based on WebSocket events.
 *
 * Architecture:
 * - State reflects NEXUS Run lifecycle and status
 * - Actions correspond 1:1 with NEXUS UI events
 * - Maintains message history and persistent tool call history
 * - Tool calls are organized by runId for proper UI rendering
 * - Provides clean interface for UI components
 *
 * Key Features:
 * - Real-time streaming text chunk handling
 * - Persistent tool call history that survives run completion
 * - Atomic state updates for consistent UI behavior
 */

import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import { websocketManager } from '../../../services/websocket/manager';
import type { Message, ToolCall } from '../types';
import type {
  RunStartedPayload,
  ToolCallStartedPayload,
  ToolCallFinishedPayload,
  TextChunkPayload,
  RunFinishedPayload,
  ErrorPayload
} from '../../../services/websocket/protocol';

// ===== Core Data Types =====

export type RunStatus = 'idle' | 'thinking' | 'tool_running' | 'streaming_text' | 'completed' | 'error';

export interface CurrentRun {
  runId: string | null;
  status: RunStatus;
  startTime?: Date;
  endTime?: Date;
  // 当前运行的工具调用 - 独立管理，不与消息关联
  activeToolCalls: ToolCall[];
}

// ===== Store State Interface =====

export interface AuraState {
  // Message History
  messages: Message[];

  // Current Run State
  currentRun: CurrentRun;

  // Connection State
  isConnected: boolean;
  sessionId: string | null;

  // UI State
  isInputDisabled: boolean;
  lastError: string | null;

  // Tool Call History - organized by runId
  toolCallHistory: Record<string, ToolCall[]>;
}

// ===== Store Actions Interface =====

export interface AuraActions {
  // WebSocket Event Handlers
  handleRunStarted: (payload: RunStartedPayload) => void;
  handleToolCallStarted: (payload: ToolCallStartedPayload) => void;
  handleToolCallFinished: (payload: ToolCallFinishedPayload) => void;
  handleTextChunk: (payload: TextChunkPayload) => void;
  handleRunFinished: (payload: RunFinishedPayload) => void;
  handleError: (payload: ErrorPayload) => void;
  
  // Connection Handlers
  handleConnected: (sessionId: string) => void;
  handleDisconnected: () => void;
  
  // User Actions
  sendMessage: (content: string) => void;
  clearMessages: () => void;
  clearError: () => void;
}

// ===== Store Implementation =====

export type AuraStore = AuraState & AuraActions;

// ===== Helper Functions =====

const updateToolCallStatus = (
  toolCall: ToolCall,
  toolName: string,
  status: 'success' | 'error',
  result: string
): ToolCall => {
  if (toolCall.toolName === toolName) {
    return {
      ...toolCall,
      status: (status === 'success' ? 'completed' : 'error') as 'completed' | 'error',
      result,
      endTime: new Date()
    };
  }
  return toolCall;
};

export const useAuraStore = create<AuraStore>((set, get) => ({
  // ===== Initial State =====
  messages: [],
  currentRun: {
    runId: null,
    status: 'idle',
    activeToolCalls: []
  },
  isConnected: false,
  sessionId: null,
  isInputDisabled: false,
  lastError: null,
  toolCallHistory: {},

  // ===== WebSocket Event Handlers =====

  handleRunStarted: (_payload: RunStartedPayload) => {
    // Note: payload contains session_id and user_input from backend,
    // but we generate client-side run ID for UI state management
    const runId = uuidv4(); // Generate client-side run ID
    const now = new Date();

    set((state) => {
      // Bind any existing streaming AI placeholder (created before run_started)
      // to this new runId to prevent multiple bubbles.
      const reboundMessages = state.messages.map((msg) => {
        if (msg.role === 'AI' && msg.isStreaming && !msg.runId) {
          return { ...msg, runId };
        }
        return msg;
      });

      return {
        ...state,
        messages: reboundMessages,
        currentRun: {
          runId,
          status: 'thinking',
          startTime: now,
          activeToolCalls: []
        },
        isInputDisabled: true,
        lastError: null
      };
    });
  },

  handleToolCallStarted: (payload: ToolCallStartedPayload) => {
    const { currentRun } = get();
    const toolCall: ToolCall = {
      id: uuidv4(),
      toolName: payload.tool_name,
      args: payload.args,
      status: 'running',
      startTime: new Date()
    };

    set((state) => {
      // Find the latest streaming AI message regardless of runId to ensure a single bubble
      let streamingAIMessageIndex = state.messages
        .map((msg, idx) => ({ msg, idx }))
        .filter(({ msg }) => msg.role === 'AI' && msg.isStreaming)
        .map(({ idx }) => idx)
        .pop() ?? -1;

      if (streamingAIMessageIndex < 0) {
        // Fallback by runId
        streamingAIMessageIndex = state.messages.findIndex(
          msg => msg.role === 'AI' && msg.runId === currentRun.runId && msg.isStreaming
        );
      }

      if (streamingAIMessageIndex >= 0) {
        // Add tool call to the existing streaming AI message and record insertion index
        const messagesWithToolCall = state.messages.map((msg, index) => {
          if (index === streamingAIMessageIndex) {
            const currentLength = msg.content.length;
            const tcWithIndex: ToolCall = { ...toolCall, insertIndex: currentLength };
            return {
              ...msg,
              runId: msg.runId || currentRun.runId || msg.runId,
              toolCalls: [...(msg.toolCalls || []), tcWithIndex],
              // Keep a legacy split index for backward compatibility with older renderers
              toolInsertIndex: (msg as Message).toolInsertIndex ?? currentLength,
            } as Message;
          }
          return msg;
        });

        const runId = currentRun.runId || 'unknown';
        const existingToolCalls = state.toolCallHistory[runId] || [];

        return {
          ...state,
          messages: messagesWithToolCall,
          currentRun: {
            ...state.currentRun,
            status: 'tool_running',
            activeToolCalls: [...state.currentRun.activeToolCalls, toolCall]
          },
          toolCallHistory: {
            ...state.toolCallHistory,
            [runId]: [...existingToolCalls, toolCall]
          }
        };
      } else {
        // No existing AI message found: create a new AI message placeholder to hold the tool call
        // This ensures that subsequent text chunks will find this message and append to it
        const aiMessage: Message = {
          id: uuidv4(),
          role: 'AI',
          content: '', // Empty content initially, will be filled by text chunks
          timestamp: new Date(),
          runId: currentRun.runId || undefined,
          isStreaming: true,
          toolCalls: [{ ...toolCall, insertIndex: 0 }], // Add the tool call to the new message
          toolInsertIndex: 0,
        };

        const runId = currentRun.runId || 'unknown';
        const existingToolCalls = state.toolCallHistory[runId] || [];

        return {
          ...state,
          messages: [...state.messages, aiMessage], // Add the new AI message
          currentRun: {
            ...state.currentRun,
            status: 'tool_running',
            activeToolCalls: [...state.currentRun.activeToolCalls, toolCall]
          },
          toolCallHistory: {
            ...state.toolCallHistory,
            [runId]: [...existingToolCalls, toolCall]
          }
        };
      }
    });
  },

  handleToolCallFinished: (payload: ToolCallFinishedPayload) => {
    const { currentRun } = get();

    set((state) => {
      // Find the AI message for this run and update its tool calls
      const aiMessageIndex = state.messages.findIndex(
        msg => msg.role === 'AI' && msg.runId === currentRun.runId
      );

      let messagesWithUpdatedToolCalls = state.messages;
      if (aiMessageIndex >= 0) {
        messagesWithUpdatedToolCalls = state.messages.map((msg, index) =>
          index === aiMessageIndex
            ? {
                ...msg,
                toolCalls: (msg.toolCalls || []).map(tool =>
                  tool.status === 'running' && tool.toolName === payload.tool_name
                    ? updateToolCallStatus(tool, payload.tool_name, payload.status, payload.result)
                    : tool
                )
              }
            : msg
        );
      }

      // Also update activeToolCalls and toolCallHistory for backward compatibility
      const runId = currentRun.runId || 'unknown';
      const updatedActiveToolCalls = state.currentRun.activeToolCalls.map(tool =>
        updateToolCallStatus(tool, payload.tool_name, payload.status, payload.result)
      );

      const updatedHistoryToolCalls = (state.toolCallHistory[runId] || []).map(tool =>
        updateToolCallStatus(tool, payload.tool_name, payload.status, payload.result)
      );

      return {
        ...state,
        messages: messagesWithUpdatedToolCalls,
        currentRun: {
          ...state.currentRun,
          activeToolCalls: updatedActiveToolCalls
        },
        toolCallHistory: {
          ...state.toolCallHistory,
          [runId]: updatedHistoryToolCalls
        }
      };
    });
  },

  handleTextChunk: (payload: TextChunkPayload) => {
    const { currentRun } = get();

    set((state) => {
      // Prefer the latest streaming AI message regardless of runId to avoid splitting
      let existingMessageIndex = state.messages
        .map((msg, idx) => ({ msg, idx }))
        .filter(({ msg }) => msg.role === 'AI' && msg.isStreaming)
        .map(({ idx }) => idx)
        .pop() ?? -1;

      if (existingMessageIndex < 0) {
        // Fallback: try to find by current runId if any
        existingMessageIndex = state.messages.findIndex(
          msg => msg.runId === currentRun.runId && msg.role === 'AI' && msg.isStreaming
        );
      }

      let updatedMessages: Message[];
      let newStatus: RunStatus = 'streaming_text';

      if (existingMessageIndex >= 0) {
        // Update existing streaming message placeholder
        updatedMessages = state.messages.map((msg, index) =>
          index === existingMessageIndex
            ? { ...msg, runId: msg.runId || currentRun.runId || msg.runId, content: msg.content + payload.chunk }
            : msg
        );
      } else {
        // First text chunk: create new AI message placeholder
        const aiMessage: Message = {
          id: uuidv4(),
          role: 'AI',
          content: payload.chunk,
          timestamp: new Date(),
          runId: currentRun.runId || undefined,
          isStreaming: true
        };
        updatedMessages = [...state.messages, aiMessage];

        // Transition from thinking to streaming_text
        newStatus = 'streaming_text';
      }

      return {
        messages: updatedMessages,
        currentRun: {
          ...state.currentRun,
          status: newStatus
        }
      };
    });
  },

  handleRunFinished: (payload: RunFinishedPayload) => {
    set((state) => {
      // Mark the streaming message as complete
      const updatedMessages = state.messages.map(msg =>
        msg.runId === state.currentRun.runId && msg.isStreaming
          ? { ...msg, isStreaming: false }
          : msg
      );

      return {
        messages: updatedMessages,
        currentRun: {
          ...state.currentRun,
          status: payload.status === 'completed' ? 'completed' : 'error',
          endTime: new Date()
        },
        isInputDisabled: false
      };
    });

    // Reset to idle after a brief delay
    setTimeout(() => {
      set(() => ({
        currentRun: {
          runId: null,
          status: 'idle',
          activeToolCalls: [] // Clear active tool calls since they're now in history
        }
      }));
    }, 1000);


  },

  handleError: (payload: ErrorPayload) => {
    set((state) => ({
      currentRun: {
        ...state.currentRun,
        status: 'error'
      },
      lastError: payload.message,
      isInputDisabled: false
    }));

    console.error('NEXUS error:', payload);
  },

  // ===== Connection Handlers =====

  handleConnected: (sessionId: string) => {
    set({
      isConnected: true,
      sessionId,
      lastError: null
    });

  },

  handleDisconnected: () => {
    set({
      isConnected: false,
      isInputDisabled: false,
      currentRun: {
        runId: null,
        status: 'idle',
        activeToolCalls: []
      }
    });

  },

  // ===== User Actions =====

  sendMessage: (content: string) => {
    if (!websocketManager.connected) {
      console.error('Cannot send message: not connected to NEXUS');
      return;
    }

    // Add user message to history immediately
    const userMessage: Message = {
      id: uuidv4(),
      role: 'HUMAN',
      content,
      timestamp: new Date()
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
      lastError: null
    }));

    // Send to backend
    websocketManager.sendMessage(content);

  },

  clearMessages: () => {
    set({ messages: [] });
  },

  clearError: () => {
    set({ lastError: null });
  }
}));
