import { useEffect } from 'react';
import { useThemeStore, type ThemePreference } from '@/stores/themeStore';

const mediaQuery = '(prefers-color-scheme: dark)';

export const useThemeManager = () => {
  const theme = useThemeStore((state) => state.theme);
  const syncSystemPreference = useThemeStore((state) => state.syncSystemPreference);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }

    const media = window.matchMedia(mediaQuery);
    const handleChange = (event: MediaQueryListEvent) => {
      const next: ThemePreference = event.matches ? 'dark' : 'light';
      syncSystemPreference(next);
    };

    if (typeof media.addEventListener === 'function') {
      media.addEventListener('change', handleChange);
    } else {
      // Safari < 14 fallback
      media.addListener(handleChange);
    }

    return () => {
      if (typeof media.removeEventListener === 'function') {
        media.removeEventListener('change', handleChange);
      } else {
        media.removeListener(handleChange);
      }
    };
  }, [syncSystemPreference]);

  return theme;
};
