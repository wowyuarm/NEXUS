import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useCommandLoader } from '../useCommandLoader';
import { useCommandStore } from '../../store/commandStore';
import { websocketManager } from '@/services/websocket/manager';

// Mock the stores and websocket manager
vi.mock('../../store/commandStore');
vi.mock('@/services/websocket/manager', () => {
  const handlers: Record<string, Array<(payload: any) => void>> = {};
  return {
    websocketManager: {
      connected: true,
      on: vi.fn((event: string, cb: (payload: any) => void) => {
        if (!handlers[event]) handlers[event] = [];
        handlers[event].push(cb);
      }),
      off: vi.fn((event: string, cb: (payload: any) => void) => {
        if (handlers[event]) {
          handlers[event] = handlers[event].filter((fn) => fn !== cb);
        }
      }),
      sendCommand: vi.fn(),
      __emit: (event: string, payload: any) => {
        (handlers[event] || []).forEach((fn) => fn(payload));
      }
    }
  };
});

describe('useCommandLoader', () => {
  const mockSetCommands = vi.fn();
  const mockSetLoading = vi.fn();
  // Access mocked websocket manager
  const mockedWs = websocketManager as unknown as {
    connected: boolean;
    on: ReturnType<typeof vi.fn>;
    off: ReturnType<typeof vi.fn>;
    sendCommand: ReturnType<typeof vi.fn>;
    __emit: (event: string, payload: any) => void;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock useCommandStore
    (useCommandStore as any).mockReturnValue({
      setCommands: mockSetCommands,
      setLoading: mockSetLoading
    });

    // Reset websocket mock state
    mockedWs.connected = true;
    mockedWs.on.mockClear();
    mockedWs.off.mockClear();
    mockedWs.sendCommand.mockClear();
  });

  it('successfully loads commands from backend', async () => {
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

    const { result } = renderHook(() => useCommandLoader({ timeoutMs: 200 }));

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(true);
    });

    await waitFor(() => {
      expect(mockedWs.sendCommand).toHaveBeenCalledWith('/help');
    });

    // Simulate server help response
    (mockedWs as any).__emit('command_result', mockCommandsResponse);

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
  });

  it('uses fallback commands when backend fails', async () => {
    mockedWs.connected = false; // trigger immediate fallback without sending

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
    const { result } = renderHook(() => useCommandLoader({ timeoutMs: 200 }));

    // Emit invalid response: should fall back
    (mockedWs as any).__emit('command_result', { status: 'success' });

    await waitFor(() => {
      expect(mockSetCommands).toHaveBeenCalledWith(result.current.fallbackCommands);
    });
  });

  it('provides loadCommands function for manual reload', async () => {
    const { result } = renderHook(() => useCommandLoader({ timeoutMs: 200 }));
    
    expect(typeof result.current.loadCommands).toBe('function');
    
    // Manual reload should work the same way
    await result.current.loadCommands();

    // Should have sent /help twice (on mount and manual reload)
    expect(mockedWs.sendCommand).toHaveBeenCalledTimes(2);

    // Emit help response to resolve promises
    (mockedWs as any).__emit('command_result', { status: 'success', data: { commands: {} } });
  });
});
