import { create } from 'zustand';
import type { Command } from '../command.types';

/**
 * Filter commands based on user input
 * Only shows commands that start with the input characters
 */
export const filterCommands = (query: string, commands: Command[]): Command[] => {
  if (!query) return commands;

  return commands.filter(command =>
    command.name.toLowerCase().startsWith(query.toLowerCase())
  );
};

interface CommandState {
  isPaletteOpen: boolean;
  query: string;
  availableCommands: Command[];
  isLoading: boolean;
  selectedCommandIndex: number;
}

interface CommandActions {
  openPalette: () => void;
  closePalette: () => void;
  setQuery: (query: string) => void;
  setCommands: (commands: Command[]) => void;
  setLoading: (loading: boolean) => void;
  selectNextCommand: () => void;
  selectPrevCommand: () => void;
  resetSelection: () => void;
}

export type CommandStore = CommandState & CommandActions;

export const useCommandStore = create<CommandStore>((set, get) => ({
  // Initial state
  isPaletteOpen: false,
  query: '',
  availableCommands: [],
  isLoading: false,
  selectedCommandIndex: 0,

  // Actions
  openPalette: () => set({ isPaletteOpen: true, query: '', selectedCommandIndex: 0 }),
  closePalette: () => set({ isPaletteOpen: false }),
  setQuery: (query: string) => set({ query: query, selectedCommandIndex: 0 }),
  setCommands: (commands: Command[]) => set({ availableCommands: commands }),
  setLoading: (loading: boolean) => set({ isLoading: loading }),

  selectNextCommand: () => {
    const { availableCommands, query, selectedCommandIndex } = get();
    const filtered = filterCommands(query, availableCommands);
    if (filtered.length === 0) {
      set({ selectedCommandIndex: -1 });
      return;
    }
    const newIndex = Math.min(selectedCommandIndex + 1, filtered.length - 1);
    set({ selectedCommandIndex: newIndex });
  },

  selectPrevCommand: () => {
    const { availableCommands, query, selectedCommandIndex } = get();
    const filtered = filterCommands(query, availableCommands);
    if (filtered.length === 0) {
      set({ selectedCommandIndex: -1 });
      return;
    }
    const newIndex = Math.max(selectedCommandIndex - 1, 0);
    set({ selectedCommandIndex: newIndex });
  },

  resetSelection: () => set({ selectedCommandIndex: -1 })
}));


