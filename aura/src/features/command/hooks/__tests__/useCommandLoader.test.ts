import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useCommandLoader } from '../useCommandLoader';
import { useCommandStore } from '../../store/commandStore';
import { websocketManager } from '@/services/websocket/manager';

// Mock the stores and websocket manager
vi.mock('../../store/commandStore');
vi.mock('@/services/websocket/manager', () => ({
  websocketManager: {
    connected: true,
    sendCommand: vi.fn(),
    on: vi.fn(),
    off: vi.fn()
  }
}));

// Mock chatStore to control executeCommand behavior
vi.mock('@/features/chat/store/chatStore', () => ({
  useChatStore: {
    getState: vi.fn(() => ({
      executeCommand: vi.fn()
    }))
  }
}));

describe('useCommandLoader', () => {
  const mockSetCommands = vi.fn();
  const mockSetLoading = vi.fn();
  const mockExecuteCommand = vi.fn();

  beforeEach(async () => {
    vi.clearAllMocks();
    
    // Mock useCommandStore
    vi.mocked(useCommandStore).mockReturnValue({
      setCommands: mockSetCommands,
      setLoading: mockSetLoading
    } as ReturnType<typeof useCommandStore>);

    // Mock chatStore's executeCommand
    const { useChatStore } = await import('@/features/chat/store/chatStore');
    vi.mocked(useChatStore.getState).mockReturnValue({
      executeCommand: mockExecuteCommand
    } as unknown as ReturnType<typeof useChatStore.getState>);

    // Reset websocket connected state
    Object.defineProperty(websocketManager, 'connected', {
      value: true,
      writable: true,
      configurable: true
    });
  });

  it('successfully loads commands via chatStore.executeCommand', async () => {
    const mockCommandsResponse = {
      status: 'success',
      data: {
        commands: {
          ping: {
            name: 'ping',
            description: 'Test connectivity',
            usage: '/ping',
            execution_target: 'server',
            examples: ['/ping']
          },
          help: {
            name: 'help',
            description: 'Display available commands',
            usage: '/help',
            execution_target: 'server',
            examples: ['/help']
          },
          clear: {
            name: 'clear',
            description: 'Clear chat',
            usage: '/clear',
            execution_target: 'client',
            examples: ['/clear']
          }
        }
      }
    };

    mockExecuteCommand.mockResolvedValue(mockCommandsResponse);

    const { result } = renderHook(() => useCommandLoader());

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(true);
    });

    await waitFor(() => {
      expect(mockExecuteCommand).toHaveBeenCalledWith('/help', expect.any(Array));
    });

    await waitFor(() => {
      expect(mockSetCommands).toHaveBeenCalledWith([
        {
          name: 'ping',
          description: 'Test connectivity',
          usage: '/ping',
          execution_target: 'server',
          examples: ['/ping']
        },
        {
          name: 'help',
          description: 'Display available commands',
          usage: '/help',
          execution_target: 'server',  // Backend is the source of truth
          examples: ['/help']
        },
        {
          name: 'clear',
          description: 'Clear chat',
          usage: '/clear',
          execution_target: 'client',
          examples: ['/clear']
        }
      ]);
    });

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });

    expect(result.current.fallbackCommands).toHaveLength(3);
    expect(result.current.fallbackCommands.map(c => c.name)).toEqual(['ping', 'help', 'clear']);
    // Verify help has server execution_target in fallback
    expect(result.current.fallbackCommands.find(c => c.name === 'help')?.execution_target).toBe('server');
  });

  it('uses fallback commands when backend fails', async () => {
    Object.defineProperty(websocketManager, 'connected', {
      value: false,
      writable: true,
      configurable: true
    });

    const { result } = renderHook(() => useCommandLoader());

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(true);
    });

    await waitFor(() => {
      expect(mockSetCommands).toHaveBeenCalledWith(result.current.fallbackCommands);
    });

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it('uses fallback commands when response format is invalid', async () => {
    mockExecuteCommand.mockResolvedValue({ status: 'success' }); // Invalid: no data

    const { result } = renderHook(() => useCommandLoader());

    await waitFor(() => {
      expect(mockSetCommands).toHaveBeenCalledWith(result.current.fallbackCommands);
    });
  });

  it('provides loadCommands function for manual reload', async () => {
    mockExecuteCommand.mockResolvedValue({ 
      status: 'success', 
      data: { commands: {} } 
    });

    const { result } = renderHook(() => useCommandLoader());
    
    expect(typeof result.current.loadCommands).toBe('function');
    
    // Wait for initial load
    await waitFor(() => {
      expect(mockExecuteCommand).toHaveBeenCalledTimes(1);
    });

    // Manual reload should work the same way
    await result.current.loadCommands();

    // Should have called executeCommand twice (on mount and manual reload)
    expect(mockExecuteCommand).toHaveBeenCalledTimes(2);
    expect(mockExecuteCommand).toHaveBeenCalledWith('/help', expect.any(Array));
  });
});
