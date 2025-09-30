import { useEffect, useCallback } from 'react';
import { useCommandStore } from '../store/commandStore';
import { websocketManager } from '@/services/websocket/manager';

interface Command {
  name: string;
  description: string;
  usage: string;
  execution_target: 'client' | 'server';
  examples: string[];
}

// Fallback commands for when backend is unavailable
const FALLBACK_COMMANDS: Command[] = [
  {
    name: 'ping',
    description: 'Check connection to the NEXUS core.',
    usage: '/ping',
    execution_target: 'server',
    examples: ['/ping']
  },
  {
    name: 'help',
    description: 'Display information about available commands.',
    usage: '/help',
    execution_target: 'client',
    examples: ['/help']
  },
  {
    name: 'clear',
    description: 'Clear the chat history',
    usage: '/clear',
    execution_target: 'client',
    examples: ['/clear']
  }
];

export interface UseCommandLoaderOptions {
  timeoutMs?: number;
  autoLoad?: boolean;
}

export const useCommandLoader = (options?: UseCommandLoaderOptions) => {
  const { setCommands, setLoading } = useCommandStore();
  const timeoutMs = options?.timeoutMs ?? 5000;
  const autoLoad = options?.autoLoad ?? true;

  const loadCommands = useCallback(async () => {
    setLoading(true);
    
    try {
      if (!websocketManager.connected) {
        throw new Error('WebSocket not connected');
      }

      const result = await new Promise<{ status: string; data?: { commands: Record<string, Command> } }>((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('Help command timeout'));
        }, timeoutMs);

        const handle = (payload: unknown) => {
          const looksLikeHelp = Boolean(
            payload && 
            typeof payload === 'object' && 
            'status' in payload && 
            'data' in payload && 
            payload.data &&
            typeof payload.data === 'object' &&
            'commands' in payload.data
          );
          if (looksLikeHelp) {
            clearTimeout(timeout);
            websocketManager.off('command_result', handle);
            resolve(payload as { status: string; data: { commands: Record<string, Command> } });
          }
        };

        websocketManager.on('command_result', handle);
        websocketManager.sendCommand('/help');
      });

      if (result?.status === 'success' && result?.data?.commands) {
        const commandsFromBackend: Command[] = Object.values(result.data.commands).map((cmd) => ({
          name: cmd.name,
          description: cmd.description,
          usage: cmd.usage,
          execution_target: cmd.execution_target,
          examples: cmd.examples || []
        }));

        // Override: help should execute on client in UI
        const overridden = commandsFromBackend.map(c =>
          c.name === 'help' ? { ...c, execution_target: 'client' as const } : c
        );

        // Ensure clear command exists (client-side)
        if (!overridden.some(c => c.name === 'clear')) {
          overridden.push({
            name: 'clear',
            description: 'Clear the chat history',
            usage: '/clear',
            execution_target: 'client',
            examples: ['/clear']
          });
        }

        setCommands(overridden);
        console.log('Successfully loaded commands from backend:', overridden);
      } else {
        throw new Error('Invalid response format from help command');
      }
    } catch (error) {
      console.warn('Failed to load commands from backend, using fallback:', error);
      // Use fallback commands to ensure basic functionality
      setCommands(FALLBACK_COMMANDS);
    } finally {
      setLoading(false);
    }
  }, [setCommands, setLoading, timeoutMs]);

  useEffect(() => {
    if (autoLoad) {
      loadCommands();
    }
  }, [autoLoad, loadCommands]);

  return {
    loadCommands,
    fallbackCommands: FALLBACK_COMMANDS
  };
};
