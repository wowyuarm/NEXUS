import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useCommandLoader } from '../useCommandLoader';
import { useCommandStore } from '../../store/commandStore';
import type { Command } from '../../command.types';

// Mock the stores
vi.mock('../../store/commandStore');

// Mock the API module
vi.mock('../../api', () => ({
  fetchCommands: vi.fn(),
  CommandAPIError: class CommandAPIError extends Error {
    statusCode?: number;
    details?: unknown;
    constructor(message: string, statusCode?: number, details?: unknown) {
      super(message);
      this.name = 'CommandAPIError';
      this.statusCode = statusCode;
      this.details = details;
    }
  }
}));

describe('useCommandLoader', () => {
  const mockSetCommands = vi.fn();
  const mockSetLoading = vi.fn();
  let mockFetchCommands: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    vi.clearAllMocks();
    
    // Mock useCommandStore
    vi.mocked(useCommandStore).mockReturnValue({
      setCommands: mockSetCommands,
      setLoading: mockSetLoading
    } as ReturnType<typeof useCommandStore>);

    // Get the mocked fetchCommands
    const { fetchCommands } = await import('../../api');
    mockFetchCommands = vi.mocked(fetchCommands);
  });

  it('successfully loads commands from REST API', async () => {
    const mockCommands: Command[] = [
      {
        name: 'ping',
        description: 'Test connectivity',
        usage: '/ping',
        handler: 'server',
        examples: ['/ping']
      },
      {
        name: 'help',
        description: 'Display available commands',
        usage: '/help',
        handler: 'server',
        examples: ['/help']
      },
      {
        name: 'clear',
        description: 'Clear chat',
        usage: '/clear',
        handler: 'client',
        examples: ['/clear']
      }
    ];

    mockFetchCommands.mockResolvedValue(mockCommands);

    const { result } = renderHook(() => useCommandLoader());

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(true);
    });

    await waitFor(() => {
      expect(mockFetchCommands).toHaveBeenCalled();
    });

    // Commands should be set directly without normalization
    await waitFor(() => {
      expect(mockSetCommands).toHaveBeenCalledWith(mockCommands);
    });

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });

    // Verify fallback commands structure (identity removed from fallback)
    expect(result.current.fallbackCommands).toHaveLength(4);
    expect(result.current.fallbackCommands.map(c => c.name)).toEqual(['ping', 'help', 'clear', 'theme']);
    
    // Verify fallback commands use 'handler' field correctly
    result.current.fallbackCommands.forEach(cmd => {
      expect(cmd).toHaveProperty('handler');
      expect(['client', 'server']).toContain(cmd.handler);
    });
  });

  it('uses fallback commands when REST API fails', async () => {
    const { CommandAPIError } = await import('../../api');
    mockFetchCommands.mockRejectedValue(
      new CommandAPIError('Network error', undefined, 'Failed to fetch')
    );

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

  it('provides loadCommands function for manual reload', async () => {
    const mockCommands: Command[] = [
      {
        name: 'test',
        description: 'Test command',
        usage: '/test',
        handler: 'client',
        examples: ['/test']
      }
    ];

    mockFetchCommands.mockResolvedValue(mockCommands);

    // Use autoLoad: false to test manual loading only
    const { result } = renderHook(() => useCommandLoader({ autoLoad: false }));
    
    expect(typeof result.current.loadCommands).toBe('function');

    // Should NOT have auto-loaded
    expect(mockFetchCommands).not.toHaveBeenCalled();

    // Manual reload should work
    await result.current.loadCommands();

    // Should have called fetchCommands once (manual reload only)
    expect(mockFetchCommands).toHaveBeenCalledTimes(1);
    
    await waitFor(() => {
      expect(mockSetCommands).toHaveBeenCalledWith(mockCommands);
    });
  });
});
