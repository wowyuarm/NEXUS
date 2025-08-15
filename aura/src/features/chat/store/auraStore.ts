// aura/src/features/chat/store/auraStore.ts
// AURA central Zustand store: single source of truth mirroring NEXUS UI events.

import { create } from 'zustand';
import type {
  RunStartedEvent,
  TextChunkEvent,
  ToolCallStartedEvent,
  ToolCallFinishedEvent,
  RunFinishedEvent,
  ErrorEvent,
} from '../../../services/websocket/protocol';
import type { WebSocketStatus } from '../../../services/websocket/manager';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  runId: string;
}

export interface ToolCall {
  id: string;
  toolName: string;
  args: Record<string, any>;
  status: 'pending' | 'success' | 'error';
  result?: any;
}

interface CurrentRunState {
  runId: string | null;
  status: 'idle' | 'thinking' | 'tool_running' | 'streaming_text';
  activeToolCalls: ToolCall[];
}

export interface AuraState {
  messages: Message[];
  connectionStatus: WebSocketStatus;
  currentRun: CurrentRunState;

  // Actions to mutate state; each corresponds to a backend event or connection change
  setConnectionStatus: (status: WebSocketStatus) => void;

  handleRunStarted: (event: RunStartedEvent) => void;
  handleTextChunk: (event: TextChunkEvent) => void;
  handleToolCallStarted: (event: ToolCallStartedEvent) => void;
  handleToolCallFinished: (event: ToolCallFinishedEvent) => void;
  handleRunFinished: (event: RunFinishedEvent) => void;
  handleError: (event: ErrorEvent) => void;

  resetRun: () => void;
}

export const useAuraStore = create<AuraState>((set) => ({
  messages: [],
  connectionStatus: 'disconnected',
  currentRun: {
    runId: null,
    status: 'idle',
    activeToolCalls: [],
  },

  setConnectionStatus: (status) => set({ connectionStatus: status }),

  handleRunStarted: (event) =>
    set((state) => ({
      currentRun: {
        runId: event.run_id,
        status: 'thinking',
        activeToolCalls: [],
      },
      // Optionally add a system message to indicate run started
      messages: state.messages,
    })),

  handleTextChunk: (event) =>
    set((state) => {
      const runId = event.run_id;
      const content = event.payload.chunk;
      // Append or merge into the last assistant message for streaming effect
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'assistant' && last.runId === runId) {
        last.content += content;
      } else {
        msgs.push({ id: `${runId}-assistant`, role: 'assistant', content, runId });
      }
      return {
        messages: msgs,
        currentRun: { ...state.currentRun, runId, status: 'streaming_text' },
      };
    }),

  handleToolCallStarted: (event) =>
    set((state) => ({
      currentRun: {
        runId: event.run_id,
        status: 'tool_running',
        activeToolCalls: [
          ...state.currentRun.activeToolCalls,
          {
            id: `${event.run_id}-${state.currentRun.activeToolCalls.length + 1}`,
            toolName: event.payload.tool_name,
            args: event.payload.args,
            status: 'pending',
          },
        ],
      },
    })),

  handleToolCallFinished: (event) =>
    set((state) => {
      const updated = state.currentRun.activeToolCalls.map((tc) =>
        tc.toolName === event.payload.tool_name && tc.status === 'pending'
          ? { ...tc, status: event.payload.status, result: event.payload.result }
          : tc
      );
      return {
        currentRun: {
          runId: event.run_id,
          status: state.currentRun.status === 'tool_running' ? 'thinking' : state.currentRun.status,
          activeToolCalls: updated,
        },
      };
    }),

  handleRunFinished: (event) =>
    set(() => ({
      currentRun: {
        runId: event.run_id,
        status: 'idle',
        activeToolCalls: [],
      },
    })),

  handleError: (event) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { id: `err-${Date.now()}`, role: 'system', content: event.payload.message, runId: event.run_id },
      ],
    })),

  resetRun: () =>
    set(() => ({
      currentRun: { runId: null, status: 'idle', activeToolCalls: [] },
    })),
}));
