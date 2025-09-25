/**
 * AURA Store Unit Tests
 * 
 * Tests for the core state management logic in auraStore.ts
 * Following TDD principles and component-focused testing strategy
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useAuraStore } from '@/features/chat/store/auraStore';
import type { 
  RunStartedPayload, 
  ToolCallStartedPayload, 
  ToolCallFinishedPayload, 
  TextChunkPayload, 
  RunFinishedPayload 
} from '@/services/websocket/protocol';

// Mock websocket manager to avoid actual connections
vi.mock('@/services/websocket/manager', () => ({
  websocketManager: {
    connected: true,
    sendMessage: vi.fn()
  }
}));

describe('auraStore', () => {
  const initialState = {
    messages: [],
    currentRun: {
      runId: null,
      status: 'idle' as const,
      activeToolCalls: []
    },
    isConnected: false,
    publicKey: null,
    isInputDisabled: false,
    lastError: null,
    toolCallHistory: {}
  };

  beforeEach(() => {
    // Reset store to initial state before each test
    useAuraStore.setState(initialState);
    vi.clearAllTimers();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('handleRunStarted', () => {
    it('should transition to thinking state and add AI message placeholder', () => {
      const payload: RunStartedPayload = {
        session_id: 'test-session',
        user_input: 'test input'
      };

      const { handleRunStarted } = useAuraStore.getState();
      handleRunStarted(payload);

      const state = useAuraStore.getState();
      
      expect(state.currentRun.status).toBe('thinking');
      expect(state.currentRun.runId).toBeTruthy();
      expect(state.isInputDisabled).toBe(true);
      expect(state.lastError).toBeNull();
    });

    it('should rebound existing streaming AI messages to new runId', () => {
      // Setup: Add an existing streaming AI message without runId
      useAuraStore.setState({
        ...initialState,
        messages: [{
          id: 'existing-msg',
          role: 'AI' as const,
          content: 'partial content',
          timestamp: new Date(),
          isStreaming: true
        }]
      });

      const payload: RunStartedPayload = {
        session_id: 'test-session',
        user_input: 'test input'
      };

      const { handleRunStarted } = useAuraStore.getState();
      handleRunStarted(payload);

      const state = useAuraStore.getState();
      const aiMessage = state.messages.find(msg => msg.role === 'AI');
      
      expect(aiMessage?.runId).toBe(state.currentRun.runId);
    });
  });

  describe('handleToolCallStarted', () => {
    it('should transition to tool_running state and add tool call to activeToolCalls', () => {
      // Setup: Start a run first
      const runPayload: RunStartedPayload = {
        session_id: 'test-session',
        user_input: 'test input'
      };
      useAuraStore.getState().handleRunStarted(runPayload);

      const toolPayload: ToolCallStartedPayload = {
        tool_name: 'test_tool',
        args: { param: 'value' }
      };

      const { handleToolCallStarted } = useAuraStore.getState();
      handleToolCallStarted(toolPayload);

      const state = useAuraStore.getState();
      
      expect(state.currentRun.status).toBe('tool_running');
      expect(state.currentRun.activeToolCalls).toHaveLength(1);
      expect(state.currentRun.activeToolCalls[0].toolName).toBe('test_tool');
      expect(state.currentRun.activeToolCalls[0].status).toBe('running');
      expect(state.currentRun.activeToolCalls[0].args).toEqual({ param: 'value' });
    });

    it('should add tool call to existing streaming AI message', () => {
      // Setup: Add streaming AI message
      const runId = 'test-run-id';
      useAuraStore.setState({
        ...initialState,
        currentRun: {
          runId,
          status: 'thinking',
          activeToolCalls: []
        },
        messages: [{
          id: 'ai-msg',
          role: 'AI' as const,
          content: 'some text',
          timestamp: new Date(),
          runId,
          isStreaming: true
        }]
      });

      const toolPayload: ToolCallStartedPayload = {
        tool_name: 'test_tool',
        args: { param: 'value' }
      };

      const { handleToolCallStarted } = useAuraStore.getState();
      handleToolCallStarted(toolPayload);

      const state = useAuraStore.getState();
      const aiMessage = state.messages.find(msg => msg.role === 'AI');
      
      expect(aiMessage?.toolCalls).toHaveLength(1);
      expect(aiMessage?.toolCalls?.[0].toolName).toBe('test_tool');
      expect(aiMessage?.toolCalls?.[0].insertIndex).toBe(9); // Length of 'some text'
    });

    it('should create new AI message placeholder when no existing message found', () => {
      // Setup: Start run without existing AI message
      useAuraStore.setState({
        ...initialState,
        currentRun: {
          runId: 'test-run-id',
          status: 'thinking',
          activeToolCalls: []
        }
      });

      const toolPayload: ToolCallStartedPayload = {
        tool_name: 'test_tool',
        args: { param: 'value' }
      };

      const { handleToolCallStarted } = useAuraStore.getState();
      handleToolCallStarted(toolPayload);

      const state = useAuraStore.getState();
      
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0].role).toBe('AI');
      expect(state.messages[0].content).toBe('');
      expect(state.messages[0].isStreaming).toBe(true);
      expect(state.messages[0].toolCalls).toHaveLength(1);
    });
  });

  describe('handleToolCallFinished', () => {
    it('should update tool call status to completed', () => {
      // Setup: Start run and tool call
      const runId = 'test-run-id';
      useAuraStore.setState({
        ...initialState,
        currentRun: {
          runId,
          status: 'tool_running',
          activeToolCalls: [{
            id: 'tool-1',
            toolName: 'test_tool',
            args: { param: 'value' },
            status: 'running',
            startTime: new Date()
          }]
        },
        messages: [{
          id: 'ai-msg',
          role: 'AI' as const,
          content: '',
          timestamp: new Date(),
          runId,
          isStreaming: true,
          toolCalls: [{
            id: 'tool-1',
            toolName: 'test_tool',
            args: { param: 'value' },
            status: 'running',
            startTime: new Date()
          }]
        }]
      });

      const finishPayload: ToolCallFinishedPayload = {
        tool_name: 'test_tool',
        status: 'success',
        result: 'Tool completed successfully'
      };

      const { handleToolCallFinished } = useAuraStore.getState();
      handleToolCallFinished(finishPayload);

      const state = useAuraStore.getState();
      
      expect(state.currentRun.activeToolCalls[0].status).toBe('completed');
      expect(state.currentRun.activeToolCalls[0].result).toBe('Tool completed successfully');
      expect(state.currentRun.activeToolCalls[0].endTime).toBeInstanceOf(Date);
      
      const aiMessage = state.messages.find(msg => msg.role === 'AI');
      expect(aiMessage?.toolCalls?.[0].status).toBe('completed');
    });

    it('should update tool call status to error on failure', () => {
      // Setup: Start run and tool call
      const runId = 'test-run-id';
      useAuraStore.setState({
        ...initialState,
        currentRun: {
          runId,
          status: 'tool_running',
          activeToolCalls: [{
            id: 'tool-1',
            toolName: 'test_tool',
            args: { param: 'value' },
            status: 'running',
            startTime: new Date()
          }]
        }
      });

      const finishPayload: ToolCallFinishedPayload = {
        tool_name: 'test_tool',
        status: 'error',
        result: 'Tool failed with error'
      };

      const { handleToolCallFinished } = useAuraStore.getState();
      handleToolCallFinished(finishPayload);

      const state = useAuraStore.getState();
      
      expect(state.currentRun.activeToolCalls[0].status).toBe('error');
      expect(state.currentRun.activeToolCalls[0].result).toBe('Tool failed with error');
    });
  });

  describe('handleTextChunk', () => {
    it('should transition to streaming_text state and append content to AI message', () => {
      // Setup: Start run
      const runId = 'test-run-id';
      useAuraStore.setState({
        ...initialState,
        currentRun: {
          runId,
          status: 'thinking',
          activeToolCalls: []
        }
      });

      const chunkPayload: TextChunkPayload = {
        chunk: 'Hello '
      };

      const { handleTextChunk } = useAuraStore.getState();
      handleTextChunk(chunkPayload);

      const state = useAuraStore.getState();
      
      expect(state.currentRun.status).toBe('streaming_text');
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0].role).toBe('AI');
      expect(state.messages[0].content).toBe('Hello ');
      expect(state.messages[0].isStreaming).toBe(true);
    });

    it('should append to existing streaming AI message', () => {
      // Setup: Add existing streaming AI message
      const runId = 'test-run-id';
      useAuraStore.setState({
        ...initialState,
        currentRun: {
          runId,
          status: 'streaming_text',
          activeToolCalls: []
        },
        messages: [{
          id: 'ai-msg',
          role: 'AI' as const,
          content: 'Hello ',
          timestamp: new Date(),
          runId,
          isStreaming: true
        }]
      });

      const chunkPayload: TextChunkPayload = {
        chunk: 'world!'
      };

      const { handleTextChunk } = useAuraStore.getState();
      handleTextChunk(chunkPayload);

      const state = useAuraStore.getState();
      const aiMessage = state.messages.find(msg => msg.role === 'AI');
      
      expect(aiMessage?.content).toBe('Hello world!');
    });
  });

  describe('handleRunFinished', () => {
    it('should disable input, mark messages as complete, and reset to idle after delay', () => {
      // Setup: Run with streaming message
      const runId = 'test-run-id';
      useAuraStore.setState({
        ...initialState,
        currentRun: {
          runId,
          status: 'streaming_text',
          activeToolCalls: []
        },
        isInputDisabled: true,
        messages: [{
          id: 'ai-msg',
          role: 'AI' as const,
          content: 'Complete response',
          timestamp: new Date(),
          runId,
          isStreaming: true
        }]
      });

      const finishPayload: RunFinishedPayload = {
        status: 'completed'
      };

      const { handleRunFinished } = useAuraStore.getState();
      handleRunFinished(finishPayload);

      let state = useAuraStore.getState();
      
      // Immediately after handleRunFinished
      expect(state.isInputDisabled).toBe(false);
      expect(state.currentRun.status).toBe('completed');
      expect(state.currentRun.endTime).toBeInstanceOf(Date);
      
      const aiMessage = state.messages.find(msg => msg.role === 'AI');
      expect(aiMessage?.isStreaming).toBe(false);

      // After timeout
      vi.advanceTimersByTime(1000);
      
      state = useAuraStore.getState();
      expect(state.currentRun.status).toBe('idle');
      expect(state.currentRun.runId).toBeNull();
      expect(state.currentRun.activeToolCalls).toHaveLength(0);
    });

    it('should handle error status', () => {
      // Setup: Run in progress
      const runId = 'test-run-id';
      useAuraStore.setState({
        ...initialState,
        currentRun: {
          runId,
          status: 'streaming_text',
          activeToolCalls: []
        },
        isInputDisabled: true
      });

      const finishPayload: RunFinishedPayload = {
        status: 'error'
      };

      const { handleRunFinished } = useAuraStore.getState();
      handleRunFinished(finishPayload);

      const state = useAuraStore.getState();
      
      expect(state.currentRun.status).toBe('error');
      expect(state.isInputDisabled).toBe(false);
    });
  });
});
