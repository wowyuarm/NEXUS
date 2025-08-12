// src/features/chat/store/chatStore.ts
import { create } from 'zustand';
import type { Message } from '../types';

interface ChatState {
  messages: Message[];
  isThinking: boolean;
  hasStarted: boolean;
  addMessage: (message: Message) => void;
  appendStreamChunk: (id: string, chunk: string) => void;
  setStreamFinished: (id: string) => void;
  setThinking: (isThinking: boolean) => void;
  setInitialMessages: (messages: Message[]) => void;
  setHasStarted: (hasStarted: boolean) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isThinking: false,
  hasStarted: false,

  setInitialMessages: (messages) => set({ messages }),

  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message],
  })),

  appendStreamChunk: (id, chunk) => set((state) => ({
    messages: state.messages.map(msg =>
      msg.id === id ? { ...msg, content: msg.content + chunk } : msg
    ),
  })),

  setStreamFinished: (id) => set((state) => ({
    messages: state.messages.map(msg =>
      msg.id === id ? {
        ...msg,
        metadata: {
          ...msg.metadata,
          streamEnded: true // 标记流结束，但保持isStreaming为true让打字机自然完成
        }
      } : msg
    ),
  })),

  setThinking: (isThinking) => set({ isThinking }),

  setHasStarted: (hasStarted) => set({ hasStarted }),
}));
