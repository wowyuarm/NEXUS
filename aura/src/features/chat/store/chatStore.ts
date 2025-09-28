import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import { websocketManager } from '@/services/websocket/manager';
import { executeHelpCommand, COMMANDS } from '@/features/command/commands';
import type { Message, ToolCall } from '../types';
import type {
  RunStartedPayload,
  ToolCallStartedPayload,
  ToolCallFinishedPayload,
  TextChunkPayload,
  RunFinishedPayload,
  ErrorPayload,
  CommandResultPayload
} from '@/services/websocket/protocol';

export type RunStatus = 'idle' | 'thinking' | 'tool_running' | 'streaming_text' | 'completed' | 'error';

export interface CurrentRun {
  runId: string | null;
  status: RunStatus;
  startTime?: Date;
  endTime?: Date;
  activeToolCalls: ToolCall[];
}

export interface ChatState {
  messages: Message[];
  currentRun: CurrentRun;
  isConnected: boolean;
  publicKey: string | null;
  isInputDisabled: boolean;
  lastError: string | null;
  toolCallHistory: Record<string, ToolCall[]>;
}

export interface ChatActions {
  handleRunStarted: (payload: RunStartedPayload) => void;
  handleToolCallStarted: (payload: ToolCallStartedPayload) => void;
  handleToolCallFinished: (payload: ToolCallFinishedPayload) => void;
  handleTextChunk: (payload: TextChunkPayload) => void;
  handleRunFinished: (payload: RunFinishedPayload) => void;
  handleError: (payload: ErrorPayload) => void;
  handleCommandResult: (payload: CommandResultPayload) => void;

  handleConnected: (publicKey: string) => void;
  handleDisconnected: () => void;

  sendMessage: (content: string) => void;
  clearMessages: () => void;
  clearError: () => void;

  executeCommand: (command: string) => void;
}

export type ChatStore = ChatState & ChatActions;

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

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  currentRun: {
    runId: null,
    status: 'idle',
    activeToolCalls: []
  },
  isConnected: false,
  publicKey: null,
  isInputDisabled: false,
  lastError: null,
  toolCallHistory: {},

  handleRunStarted: () => {
    const runId = uuidv4();
    const now = new Date();

    set((state) => {
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
      let streamingAIMessageIndex = state.messages
        .map((msg, idx) => ({ msg, idx }))
        .filter(({ msg }) => msg.role === 'AI' && msg.isStreaming)
        .map(({ idx }) => idx)
        .pop() ?? -1;

      if (streamingAIMessageIndex < 0) {
        streamingAIMessageIndex = state.messages.findIndex(
          msg => msg.role === 'AI' && msg.runId === currentRun.runId && msg.isStreaming
        );
      }

      if (streamingAIMessageIndex >= 0) {
        const messagesWithToolCall = state.messages.map((msg, index) => {
          if (index === streamingAIMessageIndex) {
            const currentLength = msg.content.length;
            const tcWithIndex: ToolCall = { ...toolCall, insertIndex: currentLength };
            return {
              ...msg,
              runId: msg.runId || currentRun.runId || msg.runId,
              toolCalls: [...(msg.toolCalls || []), tcWithIndex],
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
        const aiMessage: Message = {
          id: uuidv4(),
          role: 'AI',
          content: '',
          timestamp: new Date(),
          runId: currentRun.runId || undefined,
          isStreaming: true,
          toolCalls: [{ ...toolCall, insertIndex: 0 }],
          toolInsertIndex: 0,
        };

        const runId = currentRun.runId || 'unknown';
        const existingToolCalls = state.toolCallHistory[runId] || [];

        return {
          ...state,
          messages: [...state.messages, aiMessage],
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
      let existingMessageIndex = state.messages
        .map((msg, idx) => ({ msg, idx }))
        .filter(({ msg }) => msg.role === 'AI' && msg.isStreaming)
        .map(({ idx }) => idx)
        .pop() ?? -1;

      if (existingMessageIndex < 0) {
        existingMessageIndex = state.messages.findIndex(
          msg => msg.runId === currentRun.runId && msg.role === 'AI' && msg.isStreaming
        );
      }

      let updatedMessages: Message[];
      let newStatus: RunStatus = 'streaming_text';

      if (existingMessageIndex >= 0) {
        updatedMessages = state.messages.map((msg, index) =>
          index === existingMessageIndex
            ? { ...msg, runId: msg.runId || currentRun.runId || msg.runId, content: msg.content + payload.chunk }
            : msg
        );
      } else {
        const aiMessage: Message = {
          id: uuidv4(),
          role: 'AI',
          content: payload.chunk,
          timestamp: new Date(),
          runId: currentRun.runId || undefined,
          isStreaming: true
        };
        updatedMessages = [...state.messages, aiMessage];
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

    setTimeout(() => {
      set(() => ({
        currentRun: {
          runId: null,
          status: 'idle',
          activeToolCalls: []
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

  handleCommandResult: (payload: CommandResultPayload) => {
    const { command, result } = payload;

    set((state) => {
      const messageIndex = state.messages.findIndex(
        msg => msg.role === 'SYSTEM' && msg.content === command && msg.metadata?.status === 'pending'
      );

      if (messageIndex >= 0) {
        const updatedMessages = [...state.messages];
        updatedMessages[messageIndex] = {
          ...updatedMessages[messageIndex],
          content: result.message || 'Command completed',
          metadata: {
            ...updatedMessages[messageIndex].metadata,
            status: 'completed',
            commandResult: result
          }
        };
        return { messages: updatedMessages };
      } else {
        const newMessage: Message = {
          id: uuidv4(),
          role: 'SYSTEM',
          content: result.message || 'Command completed',
          timestamp: new Date(),
          metadata: { status: 'completed', commandResult: result }
        };
        return { messages: [...state.messages, newMessage] };
      }
    });
  },

  handleConnected: (publicKey: string) => {
    set({
      isConnected: true,
      publicKey,
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

  sendMessage: (content: string) => {
    if (!websocketManager.connected) {
      console.error('Cannot send message: not connected to NEXUS');
      return;
    }

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

    websocketManager.sendMessage(content);
  },

  clearMessages: () => {
    set({ messages: [] });
  },

  clearError: () => {
    set({ lastError: null });
  },

  executeCommand: (command: string) => {
    if (!websocketManager.connected) {
      console.error('Cannot execute command: not connected to NEXUS');
      return;
    }

    if (command === '/help') {
      const helpContent = executeHelpCommand(COMMANDS);
      const helpMessage: Message = {
        id: uuidv4(),
        role: 'SYSTEM',
        content: helpContent,
        timestamp: new Date(),
        metadata: { status: 'completed' }
      };

      set((state) => ({
        messages: [...state.messages, helpMessage]
      }));
      return;
    }

    const pendingMessage: Message = {
      id: uuidv4(),
      role: 'SYSTEM',
      content: command,
      timestamp: new Date(),
      metadata: { status: 'pending' }
    };

    set((state) => ({
      messages: [...state.messages, pendingMessage]
    }));

    websocketManager.sendCommand(command);
  }
}));


