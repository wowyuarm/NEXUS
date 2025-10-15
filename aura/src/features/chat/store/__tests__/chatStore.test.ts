/**
 * Chat Store Unit Tests
 * 
 * Tests for the core state management logic in chatStore.ts
 * Following TDD principles and component-focused testing strategy
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useChatStore } from '@/features/chat/store/chatStore';
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
    sendMessage: vi.fn(),
    sendCommand: vi.fn(),
    on: vi.fn(),
    off: vi.fn()
  }
}));

describe('chatStore', () => {
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
    useChatStore.setState(initialState);
    vi.clearAllTimers();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('handleRunStarted', () => {
    it('should transition to thinking state and add AI message placeholder', () => {
      const payload: RunStartedPayload = {
        owner_key: 'test-session',
        user_input: 'test input'
      };

      const { handleRunStarted } = useChatStore.getState();
      handleRunStarted(payload);

      const state = useChatStore.getState();
      
      expect(state.currentRun.status).toBe('thinking');
      expect(state.currentRun.runId).toBeTruthy();
      expect(state.isInputDisabled).toBe(true);
      expect(state.lastError).toBeNull();
    });

    it('should rebound existing streaming AI messages to new runId', () => {
      // Setup: Add an existing streaming AI message without runId
      useChatStore.setState({
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
        owner_key: 'test-session',
        user_input: 'test input'
      };

      const { handleRunStarted } = useChatStore.getState();
      handleRunStarted(payload);

      const state = useChatStore.getState();
      const aiMessage = state.messages.find(msg => msg.role === 'AI');
      
      expect(aiMessage?.runId).toBe(state.currentRun.runId);
    });
  });

  describe('handleToolCallStarted', () => {
    it('should transition to tool_running state and add tool call to activeToolCalls', () => {
      // Setup: Start a run first
      const runPayload: RunStartedPayload = {
        owner_key: 'test-session',
        user_input: 'test input'
      };
      useChatStore.getState().handleRunStarted(runPayload);

      const toolPayload: ToolCallStartedPayload = {
        tool_name: 'test_tool',
        args: { param: 'value' }
      };

      const { handleToolCallStarted } = useChatStore.getState();
      handleToolCallStarted(toolPayload);

      const state = useChatStore.getState();
      
      expect(state.currentRun.status).toBe('tool_running');
      expect(state.currentRun.activeToolCalls).toHaveLength(1);
      expect(state.currentRun.activeToolCalls[0].toolName).toBe('test_tool');
      expect(state.currentRun.activeToolCalls[0].status).toBe('running');
      expect(state.currentRun.activeToolCalls[0].args).toEqual({ param: 'value' });
    });

    it('should add tool call to existing streaming AI message', () => {
      // Setup: Add streaming AI message
      const runId = 'test-run-id';
      useChatStore.setState({
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

      const { handleToolCallStarted } = useChatStore.getState();
      handleToolCallStarted(toolPayload);

      const state = useChatStore.getState();
      const aiMessage = state.messages.find(msg => msg.role === 'AI');
      
      expect(aiMessage?.toolCalls).toHaveLength(1);
      expect(aiMessage?.toolCalls?.[0].toolName).toBe('test_tool');
      expect(aiMessage?.toolCalls?.[0].insertIndex).toBe(9); // Length of 'some text'
    });

    it('should create new AI message placeholder when no existing message found', () => {
      // Setup: Start run without existing AI message
      useChatStore.setState({
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

      const { handleToolCallStarted } = useChatStore.getState();
      handleToolCallStarted(toolPayload);

      const state = useChatStore.getState();
      
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
      useChatStore.setState({
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

      const { handleToolCallFinished } = useChatStore.getState();
      handleToolCallFinished(finishPayload);

      const state = useChatStore.getState();
      
      expect(state.currentRun.activeToolCalls[0].status).toBe('completed');
      expect(state.currentRun.activeToolCalls[0].result).toBe('Tool completed successfully');
      expect(state.currentRun.activeToolCalls[0].endTime).toBeInstanceOf(Date);
      
      const aiMessage = state.messages.find(msg => msg.role === 'AI');
      expect(aiMessage?.toolCalls?.[0].status).toBe('completed');
    });

    it('should update tool call status to error on failure', () => {
      // Setup: Start run and tool call
      const runId = 'test-run-id';
      useChatStore.setState({
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

      const { handleToolCallFinished } = useChatStore.getState();
      handleToolCallFinished(finishPayload);

      const state = useChatStore.getState();
      
      expect(state.currentRun.activeToolCalls[0].status).toBe('error');
      expect(state.currentRun.activeToolCalls[0].result).toBe('Tool failed with error');
    });
  });

  describe('handleTextChunk', () => {
    it('should transition to streaming_text state and append content to AI message', () => {
      // Setup: Start run
      const runId = 'test-run-id';
      useChatStore.setState({
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

      const { handleTextChunk } = useChatStore.getState();
      handleTextChunk(chunkPayload);

      const state = useChatStore.getState();
      
      expect(state.currentRun.status).toBe('streaming_text');
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0].role).toBe('AI');
      expect(state.messages[0].content).toBe('Hello ');
      expect(state.messages[0].isStreaming).toBe(true);
    });

    it('should append to existing streaming AI message', () => {
      // Setup: Add existing streaming AI message
      const runId = 'test-run-id';
      useChatStore.setState({
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

      const { handleTextChunk } = useChatStore.getState();
      handleTextChunk(chunkPayload);

      const state = useChatStore.getState();
      const aiMessage = state.messages.find(msg => msg.role === 'AI');
      
      expect(aiMessage?.content).toBe('Hello world!');
    });
  });

  describe('handleRunFinished', () => {
    it('should disable input, mark messages as complete, and reset to idle after delay', () => {
      // Setup: Run with streaming message
      const runId = 'test-run-id';
      useChatStore.setState({
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

      const { handleRunFinished } = useChatStore.getState();
      handleRunFinished(finishPayload);

      let state = useChatStore.getState();
      
      // Immediately after handleRunFinished
      expect(state.isInputDisabled).toBe(false);
      expect(state.currentRun.status).toBe('completed');
      expect(state.currentRun.endTime).toBeInstanceOf(Date);
      
      const aiMessage = state.messages.find(msg => msg.role === 'AI');
      expect(aiMessage?.isStreaming).toBe(false);

      // After timeout
      vi.advanceTimersByTime(1000);
      
      state = useChatStore.getState();
      expect(state.currentRun.status).toBe('idle');
      expect(state.currentRun.runId).toBeNull();
      expect(state.currentRun.activeToolCalls).toHaveLength(0);
    });

    it('should handle error status', () => {
      // Setup: Run in progress
      const runId = 'test-run-id';
      useChatStore.setState({
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

      const { handleRunFinished } = useChatStore.getState();
      handleRunFinished(finishPayload);

      const state = useChatStore.getState();
      
      expect(state.currentRun.status).toBe('error');
      expect(state.isInputDisabled).toBe(false);
    });
  });

  describe('executeCommand', () => {
    it('should execute client-side command immediately (/clear)', async () => {
      // Setup: Add some messages
      useChatStore.setState({
        ...initialState,
        messages: [
          { id: '1', role: 'HUMAN', content: 'test', timestamp: new Date() },
          { id: '2', role: 'AI', content: 'response', timestamp: new Date() }
        ]
      });

      const commands = [
        { name: 'clear', handler: 'client' as const, description: 'Clear', usage: '/clear', examples: [] }
      ];

      const { executeCommand } = useChatStore.getState();
      const result = await executeCommand('/clear', commands);

      expect(result?.status).toBe('success');
      expect(useChatStore.getState().messages).toHaveLength(0);
    });



    it('should handle unknown client command gracefully', async () => {
      const commands = [
        { name: 'unknown', handler: 'client' as const, description: 'Unknown', usage: '/unknown', examples: [] }
      ];

      const { executeCommand } = useChatStore.getState();
      const result = await executeCommand('/unknown', commands);

      expect(result?.status).toBe('error');
      expect(result?.message).toContain('Unknown client command');
    });
  });

  describe('setVisitorMode', () => {
    it('should set visitor mode to true', () => {
      // Arrange: Initial state with visitor mode false
      useChatStore.setState({
        ...initialState,
        visitorMode: false
      });

      // Act: Set visitor mode to true
      const { setVisitorMode } = useChatStore.getState();
      setVisitorMode(true);

      // Assert: Visitor mode should be true
      const state = useChatStore.getState();
      expect(state.visitorMode).toBe(true);
    });

    it('should set visitor mode to false', () => {
      // Arrange: Initial state with visitor mode true
      useChatStore.setState({
        ...initialState,
        visitorMode: true
      });

      // Act: Set visitor mode to false
      const { setVisitorMode } = useChatStore.getState();
      setVisitorMode(false);

      // Assert: Visitor mode should be false
      const state = useChatStore.getState();
      expect(state.visitorMode).toBe(false);
    });

    it('should allow toggling visitor mode multiple times', () => {
      // Arrange: Start with false
      useChatStore.setState({
        ...initialState,
        visitorMode: false
      });

      const { setVisitorMode } = useChatStore.getState();

      // Act: Toggle multiple times
      setVisitorMode(true);
      expect(useChatStore.getState().visitorMode).toBe(true);

      setVisitorMode(false);
      expect(useChatStore.getState().visitorMode).toBe(false);

      setVisitorMode(true);
      expect(useChatStore.getState().visitorMode).toBe(true);
    });
  });

  describe('createSystemMessage', () => {
    it('should create a SYSTEM message with command and result', () => {
      // Arrange: Empty messages
      useChatStore.setState({
        ...initialState,
        messages: []
      });

      // Act: Create system message
      const { createSystemMessage } = useChatStore.getState();
      createSystemMessage('/identity', '新的主权身份已成功锚定。');

      // Assert: Should add SYSTEM message to messages array
      const state = useChatStore.getState();
      expect(state.messages).toHaveLength(1);
      
      const sysMsg = state.messages[0];
      expect(sysMsg.role).toBe('SYSTEM');
      expect(sysMsg.content).toEqual({
        command: '/identity',
        result: '新的主权身份已成功锚定。'
      });
      expect(sysMsg.metadata?.status).toBe('completed');
      expect(sysMsg.timestamp).toBeInstanceOf(Date);
      expect(sysMsg.id).toBeDefined();
    });

    it('should append to existing messages', () => {
      // Arrange: Existing messages
      useChatStore.setState({
        ...initialState,
        messages: [
          { id: '1', role: 'HUMAN', content: 'test', timestamp: new Date() },
          { id: '2', role: 'AI', content: 'response', timestamp: new Date() }
        ]
      });

      // Act: Create system message
      const { createSystemMessage } = useChatStore.getState();
      createSystemMessage('/clear', '聊天历史已清除');

      // Assert: Should append without removing existing messages
      const state = useChatStore.getState();
      expect(state.messages).toHaveLength(3);
      
      const sysMsg = state.messages[2];
      expect(sysMsg.role).toBe('SYSTEM');
      expect(sysMsg.content).toEqual({
        command: '/clear',
        result: '聊天历史已清除'
      });
    });

    it('should create multiple SYSTEM messages independently', () => {
      // Arrange: Empty messages
      useChatStore.setState({
        ...initialState,
        messages: []
      });

      // Act: Create multiple system messages
      const { createSystemMessage } = useChatStore.getState();
      createSystemMessage('/identity', '身份已创建');
      createSystemMessage('/config', '配置已更新');

      // Assert: Should have both messages with unique IDs
      const state = useChatStore.getState();
      expect(state.messages).toHaveLength(2);
      
      expect(state.messages[0].content).toEqual({
        command: '/identity',
        result: '身份已创建'
      });
      expect(state.messages[1].content).toEqual({
        command: '/config',
        result: '配置已更新'
      });
      
      // IDs should be unique
      expect(state.messages[0].id).not.toBe(state.messages[1].id);
    });

    it('should create message with structured content format', () => {
      // Arrange: Empty messages
      useChatStore.setState({
        ...initialState,
        messages: []
      });

      // Act: Create system message
      const { createSystemMessage } = useChatStore.getState();
      createSystemMessage('/identity', '身份导入成功');

      // Assert: Content should be structured (not string)
      const state = useChatStore.getState();
      const sysMsg = state.messages[0];
      
      expect(typeof sysMsg.content).toBe('object');
      expect(sysMsg.content).toHaveProperty('command');
      expect(sysMsg.content).toHaveProperty('result');
    });
  });
});
