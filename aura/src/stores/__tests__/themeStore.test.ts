import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useThemeStore, THEME_STORAGE_KEY } from '@/stores/themeStore';

describe('themeStore', () => {
  const root = document.documentElement;

  beforeEach(() => {
    localStorage.clear();
    root.className = '';
    delete root.dataset.theme;
    useThemeStore.setState((state) => ({
      ...state,
      theme: 'dark',
      userPreference: 'dark',
      systemPreference: 'dark',
    }));
    root.classList.add('dark');
    root.dataset.theme = 'dark';
  });

  afterEach(() => {
    useThemeStore.setState((state) => ({
      ...state,
      theme: 'dark',
      userPreference: 'dark',
      systemPreference: 'dark',
    }));
    root.className = '';
    delete root.dataset.theme;
  });

  it('sets theme explicitly and persists preference', () => {
    useThemeStore.getState().setTheme('light');

    expect(useThemeStore.getState().theme).toBe('light');
    expect(useThemeStore.getState().userPreference).toBe('light');
    expect(root.classList.contains('dark')).toBe(false);
    expect(root.dataset.theme).toBe('light');
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('light');
  });

  it('toggles theme and returns next value', () => {
    const next = useThemeStore.getState().toggleTheme();

    expect(next).toBe('light');
    expect(useThemeStore.getState().theme).toBe('light');
    expect(root.classList.contains('dark')).toBe(false);
  });

  it('resets to system preference when clearing override', () => {
    useThemeStore.setState((state) => ({
      ...state,
      systemPreference: 'light',
    }));
    const result = useThemeStore.getState().resetToSystem();

    expect(result).toBe('light');
    expect(useThemeStore.getState().theme).toBe('light');
    expect(useThemeStore.getState().userPreference).toBeNull();
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
  });

  it('syncs system preference without overriding explicit choice', () => {
    useThemeStore.getState().syncSystemPreference('light');

    expect(useThemeStore.getState().systemPreference).toBe('light');
    expect(useThemeStore.getState().theme).toBe('dark');
    expect(root.classList.contains('dark')).toBe(true);
  });

  it('syncs system preference when no user override is present', () => {
    useThemeStore.setState((state) => ({
      ...state,
      theme: 'light',
      userPreference: null,
      systemPreference: 'light',
    }));
    root.classList.remove('dark');
    root.dataset.theme = 'light';

    useThemeStore.getState().syncSystemPreference('dark');

    expect(useThemeStore.getState().theme).toBe('dark');
    expect(useThemeStore.getState().systemPreference).toBe('dark');
    expect(root.classList.contains('dark')).toBe(true);
  });
});
