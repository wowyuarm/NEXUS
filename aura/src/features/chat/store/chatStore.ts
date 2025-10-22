import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import { websocketManager } from '@/services/websocket/manager';
import type { Command, CommandExecutionOptions } from '@/features/command/command.types';
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
  // Visitor restriction mode: only /identity is allowed in command palette
  visitorMode: boolean;
}

export interface ChatActions {
  handleRunStarted: (payload: RunStartedPayload) => void;
  handleToolCallStarted: (payload: ToolCallStartedPayload) => void;
  handleToolCallFinished: (payload: ToolCallFinishedPayload) => void;
  handleTextChunk: (payload: TextChunkPayload) => void;
  handleRunFinished: (payload: RunFinishedPayload) => void;
  handleError: (payload: ErrorPayload) => void;
  handleCommandResult: (payload: CommandResultPayload) => void;
  // Connection state event: toggle visitor mode silently
  handleConnectionState: (visitor: boolean) => void;

  handleConnected: (publicKey: string) => void;
  handleDisconnected: () => void;

  sendMessage: (content: string) => void;
  clearMessages: () => void;
  clearError: () => void;

  executeCommand: (command: string, availableCommands?: Command[]) => Promise<{ status: string; message: string; data?: Record<string, unknown> } | undefined>;
  
  // New actions for identity panel
  setVisitorMode: (isVisitor: boolean) => void;
  createSystemMessage: (command: string, result: string) => void;
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
  visitorMode: false,

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
            const currentLength = typeof msg.content === 'string' ? msg.content.length : 0;
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
      const isSystem = payload.role === 'SYSTEM';

      // Visitor guidance: render as a standalone SYSTEM message and mark run finished state
      if (isSystem) {
        const sysMsg: Message = {
          id: uuidv4(),
          role: 'SYSTEM',
          content: payload.chunk,
          timestamp: new Date(),
          runId: currentRun.runId || undefined,
        };
        return {
          messages: [...state.messages, sysMsg],
          currentRun: {
            ...state.currentRun,
            status: payload.is_final ? 'completed' : state.currentRun.status
          },
          // Enter visitor restricted mode until identity is verified
          visitorMode: true
        };
      }

      // Default AI streaming behavior
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
    // Support both payload shapes:
    // 1) Wrapped: { command: string, result: { status, message, data? } }
    // 2) Raw:     { status, message, data? }
    type WrappedPayload = { command: string; result: { status: 'success' | 'error'; message: string; data?: Record<string, unknown> } };
    type RawPayload = { status: 'success' | 'error'; message: string; data?: Record<string, unknown> };
    
    const payloadAsRecord = payload as unknown as Record<string, unknown>;
    const isWrapped = 'result' in payloadAsRecord && typeof payloadAsRecord.result === 'object' && 'command' in payloadAsRecord;
    const resultObj = (isWrapped ? (payload as WrappedPayload).result : payload) as RawPayload;
    const commandText: string | undefined = isWrapped ? (payload as WrappedPayload).command : undefined;

    set((state) => {
      // Try to locate the pending system message for this command.
      let messageIndex = -1;
      if (commandText) {
        messageIndex = state.messages.findIndex(
          (msg) => {
            if (msg.role === 'SYSTEM' && msg.metadata?.status === 'pending') {
              // Support both old string format and new structured format
              const msgCommand = typeof msg.content === 'string' 
                ? msg.content 
                : msg.content.command;
              return msgCommand === commandText;
            }
            return false;
          }
        );
      }
      // Fallback: pick the most recent pending SYSTEM message
      if (messageIndex < 0) {
        for (let i = state.messages.length - 1; i >= 0; i--) {
          const msg = state.messages[i];
          if (msg.role === 'SYSTEM' && msg.metadata?.status === 'pending') {
            messageIndex = i;
            break;
          }
        }
      }

      if (messageIndex >= 0) {
        const updatedMessages = [...state.messages];
        const existingMsg = updatedMessages[messageIndex];
        const existingCommand = typeof existingMsg.content === 'string'
          ? existingMsg.content
          : existingMsg.content.command;
        
        // Update with structured content
        // Priority: message (user-friendly text) > data (structured object) > fallback
        updatedMessages[messageIndex] = {
          ...existingMsg,
          content: {
            command: existingCommand,
            result: resultObj.message || resultObj.data || 'Command completed'
          },
          metadata: {
            ...existingMsg.metadata,
            status: 'completed',
            commandResult: resultObj
          }
        };
        // If identity succeeded, exit visitor mode
        const exitVisitor = commandText === '/identity' && resultObj.status === 'success';
        return { 
          messages: updatedMessages,
          visitorMode: exitVisitor ? false : state.visitorMode
        };
      }

      // If no pending message found, append a new SYSTEM message with structured content
      // Priority: message (user-friendly text) > data (structured object) > fallback
      const newMessage: Message = {
        id: uuidv4(),
        role: 'SYSTEM',
        content: {
          command: commandText || 'unknown',
          result: resultObj.message || resultObj.data || 'Command completed'
        },
        timestamp: new Date(),
        metadata: { status: 'completed', commandResult: resultObj }
      };
      const exitVisitor = commandText === '/identity' && resultObj.status === 'success';
      return { 
        messages: [...state.messages, newMessage],
        visitorMode: exitVisitor ? false : state.visitorMode
      };
    });
  },

  handleConnected: (publicKey: string) => {
    set({
      isConnected: true,
      publicKey,
      lastError: null
    });
  },

  handleConnectionState: (visitor: boolean) => {
    set({ visitorMode: visitor });
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

  executeCommand: async (commandInput: string, availableCommands?: Command[]) => {
    const rawInput = commandInput.trim();
    if (!rawInput) {
      return { status: 'error', message: 'Command cannot be empty' };
    }

    const withoutSlash = rawInput.startsWith('/') ? rawInput.slice(1) : rawInput;
    const tokens = withoutSlash.split(/\s+/).filter(Boolean);
    const commandNameToken = tokens.shift();

    if (!commandNameToken) {
      return { status: 'error', message: 'Command name is missing' };
    }

    const commandName = commandNameToken.toLowerCase();
    const commandDef = availableCommands?.find((cmd) => cmd.name.toLowerCase() === commandName);

    if (!commandDef) {
      return { status: 'error', message: `Unknown command: ${commandName}` };
    }

    const options: CommandExecutionOptions = {
      rawInput,
      args: tokens,
    };

    const { executeCommand: execute } = await import('@/features/command/commandExecutor');
    return await execute(commandDef, options);
  },

  setVisitorMode: (isVisitor: boolean) => {
    set({ visitorMode: isVisitor });
  },

  createSystemMessage: (command: string, result: string) => {
    const sysMsg: Message = {
      id: uuidv4(),
      role: 'SYSTEM',
      content: { command, result },
      timestamp: new Date(),
      metadata: { status: 'completed' }
    };
    
    set((state) => ({
      messages: [...state.messages, sysMsg]
    }));
  }
}));


