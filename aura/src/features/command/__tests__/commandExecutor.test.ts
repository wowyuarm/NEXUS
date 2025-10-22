import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { executeCommand } from '@/features/command/commandExecutor';
import type { Command } from '@/features/command/command.types';
import { useChatStore } from '@/features/chat/store/chatStore';
import { useThemeStore } from '@/stores/themeStore';

const THEME_COMMAND: Command = {
  name: 'theme',
  description: 'Toggle between light and dark themes (client-side).',
  usage: '/theme [light|dark|system]',
  handler: 'client',
  examples: ['/theme', '/theme light', '/theme dark'],
};

describe('commandExecutor – /theme command', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.className = 'dark';
    document.documentElement.dataset.theme = 'dark';

    useThemeStore.setState((state) => ({
      ...state,
      theme: 'dark',
      userPreference: 'dark',
      systemPreference: 'dark',
    }));

    useChatStore.setState((state) => ({
      ...state,
      messages: [],
    }));
  });

  afterEach(() => {
    useChatStore.setState((state) => ({
      ...state,
      messages: [],
    }));
  });

  it('toggles theme when no argument is provided', async () => {
    const result = await executeCommand(THEME_COMMAND, {
      rawInput: '/theme',
      args: [],
    });

    expect(result.status).toBe('success');
    expect(useThemeStore.getState().theme).toBe('light');

    const messages = useChatStore.getState().messages;
    expect(messages).toHaveLength(1);
    expect(messages[0].content).toEqual({
      command: '/theme',
      result: 'Theme toggled to light theme.',
    });
    expect(messages[0].metadata?.commandResult?.data).toEqual({
      theme: 'light',
      source: 'toggle',
    });
  });

  it('sets an explicit theme when argument is provided', async () => {
    // Start from light to ensure explicit set goes to dark
    useThemeStore.setState((state) => ({
      ...state,
      theme: 'light',
      userPreference: 'light',
      systemPreference: 'dark',
    }));
    document.documentElement.className = '';
    document.documentElement.dataset.theme = 'light';

    const result = await executeCommand(THEME_COMMAND, {
      rawInput: '/theme dark',
      args: ['dark'],
    });

    expect(result.status).toBe('success');
    expect(useThemeStore.getState().theme).toBe('dark');
    const lastMessage = useChatStore.getState().messages.at(-1);
    expect(lastMessage?.content).toEqual({
      command: '/theme dark',
      result: 'Theme set to dark theme.',
    });
  });

  it('follows system preference when using /theme system', async () => {
    useThemeStore.setState((state) => ({
      ...state,
      theme: 'dark',
      userPreference: 'dark',
      systemPreference: 'light',
    }));

    const result = await executeCommand(THEME_COMMAND, {
      rawInput: '/theme system',
      args: ['system'],
    });

    expect(result.status).toBe('success');
    expect(useThemeStore.getState().theme).toBe('light');
    const lastMessage = useChatStore.getState().messages.at(-1);
    expect(lastMessage?.content).toEqual({
      command: '/theme system',
      result: 'Following system preference (light theme).',
    });
  });

  it('returns error for unsupported arguments', async () => {
    const result = await executeCommand(THEME_COMMAND, {
      rawInput: '/theme blue',
      args: ['blue'],
    });

    expect(result.status).toBe('error');
    expect(useThemeStore.getState().theme).toBe('dark');
    const lastMessage = useChatStore.getState().messages.at(-1);
    expect(lastMessage?.metadata?.commandResult?.status).toBe('error');
    expect(lastMessage?.content).toEqual({
      command: '/theme blue',
      result: 'Unsupported theme option: blue. Use /theme [light|dark|system].',
    });
  });
});
