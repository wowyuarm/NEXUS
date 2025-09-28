/**
 * Tests for AURA store command functionality.
 *
 * Tests the command palette state management and command execution flow.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAuraStore } from '../auraStore';

// Mock the websocket manager
const mockSendCommand = vi.hoisted(() => vi.fn());
vi.mock('@/services/websocket/manager', () => ({
  websocketManager: {
    sendCommand: mockSendCommand,
    connected: true
  }
}));

describe('AURA Store Command Functionality', () => {
  beforeEach(() => {
    // Reset the store and mocks before each test
    // Note: availableCommands are predefined in the store and should not be reset
    useAuraStore.setState({
      messages: [],
      currentRun: {
        runId: null,
        status: 'idle',
        activeToolCalls: []
      },
      isConnected: true,
      publicKey: 'test-key',
      isInputDisabled: false,
      lastError: null,
      toolCallHistory: {},
      isCommandListOpen: false,
      commandQuery: ''
      // availableCommands is predefined and should not be reset
    });
    mockSendCommand.mockClear();
  });

  describe('Command Palette State Management', () => {
    it('should open command list', () => {
      const store = useAuraStore.getState();

      store.openCommandList();

      expect(useAuraStore.getState().isCommandListOpen).toBe(true);
    });

    it('should close command list', () => {
      const store = useAuraStore.getState();

      // First open it
      store.openCommandList();
      expect(useAuraStore.getState().isCommandListOpen).toBe(true);

      // Then close it
      store.closeCommandList();
      expect(useAuraStore.getState().isCommandListOpen).toBe(false);
    });

    it('should set command query', () => {
      const store = useAuraStore.getState();

      store.setCommandQuery('ping');

      expect(useAuraStore.getState().commandQuery).toBe('ping');
    });

    it('should have predefined commands', () => {
      // Commands are now predefined in the store
      const commands = useAuraStore.getState().availableCommands;

      expect(commands).toHaveLength(3);
      expect(commands.map(cmd => cmd.name)).toContain('ping');
      expect(commands.map(cmd => cmd.name)).toContain('help');
      expect(commands.map(cmd => cmd.name)).toContain('identity');
    });
  });

  describe('Command Execution', () => {
    it('should execute command and create pending message', () => {
      const store = useAuraStore.getState();

      store.executeCommand('/ping');

      // Verify command was sent via WebSocket
      expect(mockSendCommand).toHaveBeenCalledWith('/ping');

      // Verify command list was closed
      expect(useAuraStore.getState().isCommandListOpen).toBe(false);

      // Verify pending message was created
      const messages = useAuraStore.getState().messages;
      expect(messages).toHaveLength(1);
      expect(messages[0].role).toBe('SYSTEM');
      expect(messages[0].content).toBe('/ping');
      expect(messages[0].metadata?.status).toBe('pending');
    });

    it('should handle /help locally without sending over websocket', () => {
      const store = useAuraStore.getState();

      store.openCommandList();
      store.setCommandQuery('help');

      store.executeCommand('/help');

      // Should not send websocket command
      expect(mockSendCommand).not.toHaveBeenCalled();

      // Should close command list and reset query/index
      const state = useAuraStore.getState();
      expect(state.isCommandListOpen).toBe(false);
      expect(state.commandQuery).toBe('');
      expect(state.selectedCommandIndex).toBe(0);

      // Should add a completed SYSTEM message with help content
      const messages = state.messages;
      expect(messages).toHaveLength(1);
      expect(messages[0].role).toBe('SYSTEM');
      expect(messages[0].metadata?.status).toBe('completed');
      expect(messages[0].content).toContain('Available commands:');
      expect(messages[0].content).toContain('/help');
    });

    it('should handle command result and update message', () => {
      const store = useAuraStore.getState();

      // First execute a command to create a pending message
      store.executeCommand('/ping');

      const initialMessages = useAuraStore.getState().messages;
      expect(initialMessages).toHaveLength(1);

      // Now handle the command result
      const commandResult = {
        status: 'success' as const,
        message: 'pong',
        data: { latency_ms: 1 }
      };

      store.handleCommandResult({
        command: '/ping',
        result: commandResult
      });

      // Verify message was updated
      const updatedMessages = useAuraStore.getState().messages;
      expect(updatedMessages).toHaveLength(1);
      expect(updatedMessages[0].content).toBe('pong');
      expect(updatedMessages[0].metadata?.status).toBe('completed');
    });

    it('should handle command result for unknown command gracefully', () => {
      const store = useAuraStore.getState();

      // Handle result without a pending message
      const commandResult = {
        status: 'error' as const,
        message: 'Unknown command'
      };

      store.handleCommandResult({
        command: '/unknown',
        result: commandResult
      });

      // Should create a new error message
      const messages = useAuraStore.getState().messages;
      expect(messages).toHaveLength(1);
      expect(messages[0].role).toBe('SYSTEM');
      expect(messages[0].content).toBe('Unknown command');
      expect(messages[0].metadata?.status).toBe('completed');
    });
  });

  describe('Command Filtering', () => {
    it('should filter commands based on query', () => {
      const store = useAuraStore.getState();

      // Use the predefined commands from the store
      const commands = useAuraStore.getState().availableCommands;
      store.setCommandQuery('pi');

      // Test the filtering logic that matches the CommandList component
      const filteredCommands = commands.filter(cmd =>
        cmd.name.toLowerCase().startsWith('pi')
      );

      expect(filteredCommands).toHaveLength(1);
      expect(filteredCommands[0].name).toBe('ping');
    });
  });
});