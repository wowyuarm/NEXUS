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
// These must match backend definitions exactly to maintain architectural integrity
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
    execution_target: 'server',  // Backend is the authoritative source for command metadata
    examples: ['/help']
  },
  {
    name: 'clear',
    description: 'Clear the chat messages from view (context history preserved)',
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
  const autoLoad = options?.autoLoad ?? true;

  const loadCommands = useCallback(async () => {
    setLoading(true);
    
    try {
      if (!websocketManager.connected) {
        throw new Error('WebSocket not connected');
      }

      // Use unified command execution entry point through chatStore
      // This ensures consistent behavior and allows users to see system initialization
      const { useChatStore } = await import('@/features/chat/store/chatStore');
      const { executeCommand } = useChatStore.getState();
      
      const result = await executeCommand('/help', FALLBACK_COMMANDS);

      if (result?.status === 'success' && result?.data?.commands) {
        // Trust backend completely - no overrides, no modifications
        const commandsFromBackend: Command[] = Object.values(result.data.commands as Record<string, Command>).map((cmd) => ({
          name: cmd.name,
          description: cmd.description,
          usage: cmd.usage,
          execution_target: cmd.execution_target,
          examples: cmd.examples || []
        }));

        setCommands(commandsFromBackend);
        console.log('Successfully loaded commands from backend:', commandsFromBackend);
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
  }, [setCommands, setLoading]);

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
