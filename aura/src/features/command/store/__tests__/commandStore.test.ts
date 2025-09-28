import { describe, it, expect, beforeEach } from 'vitest';
import { useCommandStore } from '@/features/command/store/commandStore';

describe('commandStore', () => {
  beforeEach(() => {
    useCommandStore.setState({
      isCommandListOpen: false,
      commandQuery: '',
      isLoading: false,
      availableCommands: [
        { name: 'ping', description: 'Check connection to the NEXUS core.' },
        { name: 'help', description: 'Display information about available commands.' },
        { name: 'identity', description: 'Manage your user identity.' }
      ],
      selectedCommandIndex: 0
    });
  });

  describe('Palette state', () => {
    it('opens and closes palette', () => {
      const store = useCommandStore.getState();
      store.openCommandList();
      expect(useCommandStore.getState().isCommandListOpen).toBe(true);
      store.closeCommandList();
      expect(useCommandStore.getState().isCommandListOpen).toBe(false);
    });

    it('sets command query and resets selection', () => {
      const store = useCommandStore.getState();
      store.setCommandQuery('pi');
      const state = useCommandStore.getState();
      expect(state.commandQuery).toBe('pi');
      expect(state.selectedCommandIndex).toBe(0);
    });
  });

  describe('Available commands', () => {
    it('has predefined commands', () => {
      const names = useCommandStore.getState().availableCommands.map(c => c.name);
      expect(names).toEqual(['ping', 'help', 'identity']);
    });

    it('can override commands', () => {
      useCommandStore.getState().setCommands([{ name: 'x', description: 'y' }]);
      const names = useCommandStore.getState().availableCommands.map(c => c.name);
      expect(names).toEqual(['x']);
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
      store.setCommandQuery('h'); // only 'help'
      // Next should clamp to 0; Prev should clamp to 0
      store.selectNextCommand();
      expect(useCommandStore.getState().selectedCommandIndex).toBe(0);
      store.selectPrevCommand();
      expect(useCommandStore.getState().selectedCommandIndex).toBe(0);
    });

    it('sets selection to -1 when no commands match', () => {
      const store = useCommandStore.getState();
      store.setCommandQuery('xyz');
      store.selectNextCommand();
      expect(useCommandStore.getState().selectedCommandIndex).toBe(-1);
      store.resetSelection();
      expect(useCommandStore.getState().selectedCommandIndex).toBe(-1);
    });
  });
});


