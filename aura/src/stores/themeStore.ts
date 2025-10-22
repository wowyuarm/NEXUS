import { create } from 'zustand';

export type ThemePreference = 'light' | 'dark';

interface ThemeState {
  /** Currently applied theme after resolving user/system preference */
  theme: ThemePreference;
  /** Explicit user override persisted locally */
  userPreference: ThemePreference | null;
  /** Latest system color scheme preference */
  systemPreference: ThemePreference;
}

interface ThemeActions {
  /** Persistently set theme and override system preference */
  setTheme: (theme: ThemePreference) => void;
  /** Toggle between light/dark and persist the choice */
  toggleTheme: () => ThemePreference;
  /** Clear user override and follow system preference */
  resetToSystem: () => ThemePreference;
  /** Sync system preference change (no override if userPreference is set) */
  syncSystemPreference: (theme: ThemePreference) => void;
}

export type ThemeStore = ThemeState & ThemeActions;

const STORAGE_KEY = 'yx-nexus-theme';
const THEME_DATA_ATTR = 'theme';

type ThemeStateSnapshot = Pick<ThemeState, 'theme' | 'userPreference' | 'systemPreference'>;

const isBrowser = typeof window !== 'undefined' && typeof document !== 'undefined';

const applyThemeClass = (theme: ThemePreference) => {
  if (!isBrowser) return;
  const root = document.documentElement;
  root.classList.toggle('dark', theme === 'dark');
  root.dataset[THEME_DATA_ATTR] = theme;
};

const readStoredPreference = (): ThemePreference | null => {
  if (!isBrowser) return null;
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value === 'light' || value === 'dark' ? value : null;
  } catch (error) {
    console.warn('Failed to read stored theme preference:', error);
    return null;
  }
};

const detectSystemPreference = (): ThemePreference => {
  if (!isBrowser || typeof window.matchMedia !== 'function') {
    return 'dark';
  }
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  return media.matches ? 'dark' : 'light';
};

const persistUserPreference = (value: ThemePreference | null) => {
  if (!isBrowser) return;
  try {
    if (value) {
      window.localStorage.setItem(STORAGE_KEY, value);
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  } catch (error) {
    console.warn('Failed to persist theme preference:', error);
  }
};

const resolveInitialState = (): ThemeStateSnapshot => {
  const stored = readStoredPreference();
  const system = detectSystemPreference();
  const theme = stored ?? system;

  if (isBrowser) {
    applyThemeClass(theme);
  }

  return {
    theme,
    userPreference: stored,
    systemPreference: system,
  };
};

const initialState = resolveInitialState();

export const useThemeStore = create<ThemeStore>((set, get) => ({
  ...initialState,

  setTheme: (theme) => {
    applyThemeClass(theme);
    persistUserPreference(theme);
    set({ theme, userPreference: theme });
  },

  toggleTheme: () => {
    const next = get().theme === 'dark' ? 'light' : 'dark';
    applyThemeClass(next);
    persistUserPreference(next);
    set({ theme: next, userPreference: next });
    return next;
  },

  resetToSystem: () => {
    const system = get().systemPreference ?? detectSystemPreference();
    applyThemeClass(system);
    persistUserPreference(null);
    set({ theme: system, userPreference: null });
    return system;
  },

  syncSystemPreference: (theme) => {
    set((state) => {
      if (state.systemPreference === theme) {
        return state;
      }

      if (state.userPreference) {
        return {
          ...state,
          systemPreference: theme,
        };
      }

      applyThemeClass(theme);
      return {
        ...state,
        systemPreference: theme,
        theme,
      };
    });
  },
}));

/**
 * Ensure the theme store module is retained after tree shaking and
 * that the current theme is applied before the first paint.
 */
export const ensureThemeOnLoad = () => {
  return useThemeStore.getState().theme;
};

export const THEME_STORAGE_KEY = STORAGE_KEY;
