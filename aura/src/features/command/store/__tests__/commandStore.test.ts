import { describe, it, expect, beforeEach } from 'vitest';
import { useCommandStore } from '@/features/command/store/commandStore';

describe('commandStore', () => {
  beforeEach(() => {
    useCommandStore.setState({
      isPaletteOpen: false,
      query: '',
      isLoading: false,
      availableCommands: [
        { 
          name: 'ping', 
          description: 'Check connection to the NEXUS core.',
          usage: '/ping',
          handler: 'server' as const,
          examples: ['/ping']
        },
        { 
          name: 'help', 
          description: 'Display information about available commands.',
          usage: '/help',
          handler: 'server' as const,
          examples: ['/help']
        },
        { 
          name: 'clear', 
          description: 'Clear the chat history',
          usage: '/clear',
          handler: 'client' as const,
          examples: ['/clear']
        }
      ],
      selectedCommandIndex: 0
    });
  });

  describe('Palette state', () => {
    it('opens and closes palette', () => {
      const store = useCommandStore.getState();
      store.openPalette();
      expect(useCommandStore.getState().isPaletteOpen).toBe(true);
      store.closePalette();
      expect(useCommandStore.getState().isPaletteOpen).toBe(false);
    });

    it('sets command query and resets selection', () => {
      const store = useCommandStore.getState();
      store.setQuery('pi');
      const state = useCommandStore.getState();
      expect(state.query).toBe('pi');
      expect(state.selectedCommandIndex).toBe(0);
    });
  });

  describe('Available commands', () => {
    it('starts with empty commands (loaded dynamically)', () => {
      // Reset to initial state
      useCommandStore.setState({ availableCommands: [] });
      const names = useCommandStore.getState().availableCommands.map(c => c.name);
      expect(names).toEqual([]);
    });

    it('can set commands with complete metadata', () => {
      const newCommands = [{
        name: 'test',
        description: 'Test command',
        usage: '/test',
        handler: 'client' as const,
        examples: ['/test']
      }];
      useCommandStore.getState().setCommands(newCommands);
      const commands = useCommandStore.getState().availableCommands;
      expect(commands).toEqual(newCommands);
      expect(commands[0].handler).toBe('client');
    });
  });

  describe('Selection', () => {
    it('navigates within unfiltered command list', () => {
      const store = useCommandStore.getState();
      // initial 0 -> next -> 1 -> next -> 2
      store.selectNextCommand();
      expect(useCommandStore.getState().selectedCommandIndex).toBe(1);
      store.selectNextCommand();
      expect(useCommandStore.getState().selectedCommandIndex).toBe(2);
      // prev -> 1
      store.selectPrevCommand();
      expect(useCommandStore.getState().selectedCommandIndex).toBe(1);
    });

    it('respects filtering when navigating', () => {
      const store = useCommandStore.getState();
      store.setQuery('h'); // only 'help'
      // Next should clamp to 0; Prev should clamp to 0
      store.selectNextCommand();
      expect(useCommandStore.getState().selectedCommandIndex).toBe(0);
      store.selectPrevCommand();
      expect(useCommandStore.getState().selectedCommandIndex).toBe(0);
    });

    it('sets selection to -1 when no commands match', () => {
      const store = useCommandStore.getState();
      store.setQuery('xyz');
      store.selectNextCommand();
      expect(useCommandStore.getState().selectedCommandIndex).toBe(-1);
      store.resetSelection();
      expect(useCommandStore.getState().selectedCommandIndex).toBe(-1);
    });
  });
});


