/**
 * AURA Zustand Store - The Single Source of Truth
 * 
 * This store precisely mirrors the NEXUS backend state and provides
 * atomic actions for updating the UI state based on WebSocket events.
 * 
 * Architecture:
 * - State reflects NEXUS Run lifecycle and status
 * - Actions correspond 1:1 with NEXUS UI events
 * - Maintains message history and active tool calls
 * - Provides clean interface for UI components
 */

import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import { websocketManager } from '../../../services/websocket/manager';
import type {
  RunStartedPayload,
  ToolCallStartedPayload,
  ToolCallFinishedPayload,
  TextChunkPayload,
  RunFinishedPayload,
  ErrorPayload
} from '../../../services/websocket/protocol';

// ===== Core Data Types =====

export interface Message {
  id: string;
  role: 'HUMAN' | 'AI' | 'SYSTEM' | 'TOOL';
  content: string;
  timestamp: Date;
  runId?: string;
  isStreaming?: boolean;
}

export interface ToolCall {
  id: string;
  toolName: string;
  args: Record<string, any>;
  status: 'running' | 'completed' | 'error';
  result?: string;
  startTime: Date;
  endTime?: Date;
}

export type RunStatus = 'idle' | 'thinking' | 'tool_running' | 'streaming_text' | 'completed' | 'error';

export interface CurrentRun {
  runId: string | null;
  status: RunStatus;
  activeToolCalls: ToolCall[];
  startTime?: Date;
  endTime?: Date;
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

  // ===== WebSocket Event Handlers =====

  handleRunStarted: (payload: RunStartedPayload) => {
    const runId = uuidv4(); // Generate client-side run ID
    const now = new Date();

    set(() => ({
      currentRun: {
        runId,
        status: 'thinking',
        activeToolCalls: [],
        startTime: now
      },
      isInputDisabled: true,
      lastError: null
    }));

    console.log('Run started:', { runId, payload });
  },

  handleToolCallStarted: (payload: ToolCallStartedPayload) => {
    const toolCall: ToolCall = {
      id: uuidv4(),
      toolName: payload.tool_name,
      args: payload.args,
      status: 'running',
      startTime: new Date()
    };

    set((state) => ({
      currentRun: {
        ...state.currentRun,
        status: 'tool_running',
        activeToolCalls: [...state.currentRun.activeToolCalls, toolCall]
      }
    }));

    console.log('Tool call started:', toolCall);
  },

  handleToolCallFinished: (payload: ToolCallFinishedPayload) => {
    set((state) => ({
      currentRun: {
        ...state.currentRun,
        activeToolCalls: state.currentRun.activeToolCalls.map(tool =>
          tool.toolName === payload.tool_name
            ? {
                ...tool,
                status: payload.status === 'success' ? 'completed' : 'error',
                result: payload.result,
                endTime: new Date()
              }
            : tool
        )
      }
    }));

    console.log('Tool call finished:', payload);
  },

  handleTextChunk: (payload: TextChunkPayload) => {
    const { currentRun } = get();
    
    set((state) => {
      // Find or create the AI message for this run
      const existingMessageIndex = state.messages.findIndex(
        msg => msg.runId === currentRun.runId && msg.role === 'AI' && msg.isStreaming
      );

      let updatedMessages: Message[];

      if (existingMessageIndex >= 0) {
        // Update existing streaming message
        updatedMessages = state.messages.map((msg, index) =>
          index === existingMessageIndex
            ? { ...msg, content: msg.content + payload.chunk }
            : msg
        );
      } else {
        // Create new AI message
        const aiMessage: Message = {
          id: uuidv4(),
          role: 'AI',
          content: payload.chunk,
          timestamp: new Date(),
          runId: currentRun.runId || undefined,
          isStreaming: true
        };
        updatedMessages = [...state.messages, aiMessage];
      }

      return {
        messages: updatedMessages,
        currentRun: {
          ...state.currentRun,
          status: 'streaming_text'
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
          activeToolCalls: []
        }
      }));
    }, 1000);

    console.log('Run finished:', payload);
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
    console.log('Connected to NEXUS:', sessionId);
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
    console.log('Disconnected from NEXUS');
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
    console.log('Sent message:', content);
  },

  clearMessages: () => {
    set({ messages: [] });
  },

  clearError: () => {
    set({ lastError: null });
  }
}));
