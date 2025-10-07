import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fetchCommands, fetchCommand, CommandAPIError } from '../api';
import type { Command } from '../command.types';

// Mock global fetch
global.fetch = vi.fn();

describe('Command API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchCommands', () => {
    it('successfully fetches commands from REST API', async () => {
      const mockCommands: Command[] = [
        {
          name: 'ping',
          description: 'Test connectivity',
          usage: '/ping',
          handler: 'websocket',
          examples: ['/ping']
        },
        {
          name: 'help',
          description: 'Display available commands',
          usage: '/help',
          handler: 'websocket',
          examples: ['/help']
        },
        {
          name: 'clear',
          description: 'Clear chat',
          usage: '/clear',
          handler: 'client',
          examples: ['/clear']
        },
        {
          name: 'identity',
          description: 'Identity verification',
          usage: '/identity',
          handler: 'websocket',
          requiresSignature: true,
          examples: ['/identity']
        }
      ];

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => mockCommands,
        text: async () => JSON.stringify(mockCommands)
      } as Response);

      const result = await fetchCommands();
      
      expect(result).toEqual(mockCommands);
      expect(result).toHaveLength(4);
      const expectedUrl = `${window.location.origin}/api/v1/commands`;
      expect(global.fetch).toHaveBeenCalledWith(
        expectedUrl,
        expect.objectContaining({
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        })
      );
    });

    it('throws CommandAPIError on network error', async () => {
      const networkError = new Error('Network connection failed');
      (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(networkError);

      await expect(fetchCommands()).rejects.toThrow(CommandAPIError);
      
      try {
        await fetchCommands();
      } catch (error) {
        expect(error).toBeInstanceOf(CommandAPIError);
        expect((error as CommandAPIError).message).toContain('Network error');
        expect((error as CommandAPIError).statusCode).toBeUndefined();
      }
    });

    it('throws CommandAPIError on 404 response', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        text: async () => 'Endpoint not found'
      } as Response);

      await expect(fetchCommands()).rejects.toThrow(CommandAPIError);
      
      try {
        await fetchCommands();
      } catch (error) {
        expect(error).toBeInstanceOf(CommandAPIError);
        expect((error as CommandAPIError).statusCode).toBe(404);
        expect((error as CommandAPIError).message).toContain('Failed to fetch commands');
      }
    });

    it('throws CommandAPIError on 500 response', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        text: async () => 'Server error occurred'
      } as Response);

      await expect(fetchCommands()).rejects.toThrow(CommandAPIError);
      
      try {
        await fetchCommands();
      } catch (error) {
        expect(error).toBeInstanceOf(CommandAPIError);
        expect((error as CommandAPIError).statusCode).toBe(500);
      }
    });

    it('parses JSON correctly and returns Command[] type', async () => {
      const mockCommands: Command[] = [
        {
          name: 'test',
          description: 'Test command',
          usage: '/test',
          handler: 'client',
          examples: ['/test'],
          metadata: { category: 'testing' }
        }
      ];

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => mockCommands,
        text: async () => JSON.stringify(mockCommands)
      } as Response);

      const result = await fetchCommands();
      
      // Type assertions
      expect(Array.isArray(result)).toBe(true);
      expect(result[0]).toHaveProperty('name');
      expect(result[0]).toHaveProperty('handler');
      expect(result[0]).toHaveProperty('description');
      expect(result[0]).toHaveProperty('usage');
      expect(result[0]).toHaveProperty('examples');
      
      // Value assertions
      expect(result[0].name).toBe('test');
      expect(result[0].handler).toBe('client');
    });

    it('handles empty command list', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => [],
        text: async () => '[]'
      } as Response);

      const result = await fetchCommands();
      
      expect(result).toEqual([]);
      expect(result).toHaveLength(0);
    });
  });

  describe('fetchCommand', () => {
    it('fetches specific command by name', async () => {
      const mockCommands: Command[] = [
        {
          name: 'ping',
          description: 'Test connectivity',
          usage: '/ping',
          handler: 'websocket',
          examples: ['/ping']
        },
        {
          name: 'help',
          description: 'Display available commands',
          usage: '/help',
          handler: 'websocket',
          examples: ['/help']
        }
      ];

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => mockCommands,
        text: async () => JSON.stringify(mockCommands)
      } as Response);

      const result = await fetchCommand('ping');
      
      expect(result).not.toBeNull();
      expect(result?.name).toBe('ping');
    });

    it('returns null when command not found', async () => {
      const mockCommands: Command[] = [
        {
          name: 'ping',
          description: 'Test connectivity',
          usage: '/ping',
          handler: 'websocket',
          examples: ['/ping']
        }
      ];

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => mockCommands,
        text: async () => JSON.stringify(mockCommands)
      } as Response);

      const result = await fetchCommand('nonexistent');
      
      expect(result).toBeNull();
    });
  });

  describe('CommandAPIError', () => {
    it('constructs error with message only', () => {
      const error = new CommandAPIError('Test error');
      
      expect(error.message).toBe('Test error');
      expect(error.name).toBe('CommandAPIError');
      expect(error.statusCode).toBeUndefined();
      expect(error.details).toBeUndefined();
    });

    it('constructs error with status code and details', () => {
      const details = { reason: 'Server overload' };
      const error = new CommandAPIError('Server error', 503, details);
      
      expect(error.message).toBe('Server error');
      expect(error.statusCode).toBe(503);
      expect(error.details).toEqual(details);
    });
  });
});

