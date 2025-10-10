import { useEffect, useCallback } from 'react';
import { useCommandStore } from '../store/commandStore';
import { fetchCommands } from '../api';
import type { Command } from '../command.types';
import { useChatStore } from '@/features/chat/store/chatStore';

// Fallback commands for when backend is unavailable
// These must match backend definitions exactly to maintain architectural integrity
const FALLBACK_COMMANDS: Command[] = [
  {
    name: 'ping',
    description: 'Check connection to the NEXUS core.',
    usage: '/ping',
    handler: 'websocket',
    examples: ['/ping']
  },
  {
    name: 'help',
    description: 'Display information about available commands.',
    usage: '/help',
    handler: 'client',
    examples: ['/help']
  },
  {
    name: 'clear',
    description: 'Clear the chat messages from view (context history preserved)',
    usage: '/clear',
    handler: 'client',
    examples: ['/clear']
  },
  // Intentionally omit 'identity' from fallback: requires backend + signature
];

export interface UseCommandLoaderOptions {
  autoLoad?: boolean;
}

/**
 * Hook for loading commands from the backend via REST API
 * 
 * This hook fetches command definitions from /api/v1/commands and
 * stores them in the command store. It provides fallback commands
 * if the backend is unavailable.
 * 
 * @param options - Configuration options
 * @returns Object with loadCommands function and fallback commands
 */
export const useCommandLoader = (options?: UseCommandLoaderOptions) => {
  const { setCommands, setLoading } = useCommandStore();
  const autoLoad = options?.autoLoad ?? true;
  const visitorMode = useChatStore(s => s.visitorMode);

  const loadCommands = useCallback(async () => {
    setLoading(true);
    
    try {
      // Fetch commands from REST API
      console.log('🔄 Loading commands from REST API...');
      const commands = await fetchCommands();
      // Restrict commands in visitor mode to only /identity
      const filtered = visitorMode ? commands.filter((c: Command) => c.name === 'identity') : commands;
      setCommands(filtered);
      console.log(`✅ Successfully loaded ${commands.length} commands from backend`);
      
    } catch (error) {
      console.warn('⚠️ Failed to load commands from backend, using fallback:', error);
      // Use fallback commands to ensure basic functionality
      const filteredFallback = visitorMode ? FALLBACK_COMMANDS.filter(c => c.name === 'identity') : FALLBACK_COMMANDS;
      setCommands(filteredFallback);
    } finally {
      setLoading(false);
    }
  }, [setCommands, setLoading, visitorMode]);

  // Auto-load commands on mount
  useEffect(() => {
    if (autoLoad) {
      console.log('🚀 Auto-loading commands from REST API');
      loadCommands();
    }
  }, [autoLoad, loadCommands, visitorMode]);

  return {
    loadCommands,
    fallbackCommands: FALLBACK_COMMANDS
  };
};
