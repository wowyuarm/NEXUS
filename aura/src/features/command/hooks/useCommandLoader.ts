import { useEffect, useCallback } from 'react';
import { useCommandStore } from '../store/commandStore';
import { fetchCommands } from '../api';
import { normalizeCommand } from '../command.types';
import type { Command } from '../command.types';

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
    handler: 'websocket',  // Backend is the authoritative source for command metadata
    examples: ['/help']
  },
  {
    name: 'clear',
    description: 'Clear the chat messages from view (context history preserved)',
    usage: '/clear',
    handler: 'client',
    examples: ['/clear']
  },
  {
    name: 'identity',
    description: 'Identity verification - returns your verified public key',
    usage: '/identity',
    handler: 'websocket',
    requiresSignature: true,
    examples: ['/identity']
  }
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

  const loadCommands = useCallback(async () => {
    setLoading(true);
    
    try {
      // Fetch commands from REST API
      console.log('🔄 Loading commands from REST API...');
      const commands = await fetchCommands();
      
      // Normalize commands for backward compatibility
      const normalizedCommands = commands.map(normalizeCommand);
      
      setCommands(normalizedCommands);
      console.log(`✅ Successfully loaded ${normalizedCommands.length} commands from backend`);
      
    } catch (error) {
      console.warn('⚠️ Failed to load commands from backend, using fallback:', error);
      // Use fallback commands to ensure basic functionality
      setCommands(FALLBACK_COMMANDS);
    } finally {
      setLoading(false);
    }
  }, [setCommands, setLoading]);

  // Auto-load commands on mount
  useEffect(() => {
    if (autoLoad) {
      console.log('🚀 Auto-loading commands from REST API');
      loadCommands();
    }
  }, [autoLoad, loadCommands]);

  return {
    loadCommands,
    fallbackCommands: FALLBACK_COMMANDS
  };
};
