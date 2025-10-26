/**
 * Command Executor
 * 
 * Central command execution engine that intelligently routes commands
 * to the appropriate handler (client, websocket, or REST) based on
 * the command's handler type.
 * 
 * This module is the core of the new architecture, implementing the
 * separation of concerns between command execution and state management.
 */

import { v4 as uuidv4 } from 'uuid';
import type { Command, CommandResult, CommandExecutionOptions } from './command.types';
import { isClientCommand, isWebSocketCommand, isRestCommand, isGUICommand } from './command.types';
import { websocketManager } from '@/services/websocket/manager';
import { IdentityService } from '@/services/identity/identity';
import { useChatStore } from '@/features/chat/store/chatStore';
import { useCommandStore } from './store/commandStore';
import type { Message } from '@/features/chat/types';
import { useUIStore } from '@/stores/uiStore';
import { getNexusConfig } from '@/config/nexus';
import type { ModalType } from '@/stores/uiStore';
import { useThemeStore, type ThemePreference } from '@/stores/themeStore';

const THEME_OPTION_SYSTEM = 'system';

const getCommandText = (command: Command, options?: CommandExecutionOptions) =>
  options?.rawInput?.trim() && options.rawInput.trim().startsWith('/')
    ? options.rawInput.trim()
    : `/${command.name}`;

const appendSystemMessage = (
  commandText: string,
  result: string | Record<string, unknown>,
  status: 'success' | 'error',
  message: string,
  data?: Record<string, unknown>
) => {
  const systemMsg: Message = {
    id: uuidv4(),
    role: 'SYSTEM',
    content: {
      command: commandText,
      result,
    },
    timestamp: new Date(),
    metadata: {
      status: 'completed',
      commandResult: {
        status,
        message,
        data,
      },
    },
  };

  useChatStore.setState((state) => ({
    messages: [...state.messages, systemMsg],
  }));
};

const formatThemeResult = (theme: ThemePreference, source: 'toggle' | 'explicit' | 'system') => {
  const readable = theme === 'dark' ? 'dark theme' : 'light theme';
  if (source === 'system') {
    return `Following system preference (${readable}).`;
  }
  if (source === 'toggle') {
    return `Theme toggled to ${readable}.`;
  }
  return `Theme set to ${readable}.`;
};

/**
 * Execute a client-side command
 *
 * Handles commands that run entirely in the browser without
 * backend communication (e.g., /clear).
 */
async function executeClientCommand(
  command: Command,
  options?: CommandExecutionOptions
): Promise<CommandResult> {
  const chatStore = useChatStore.getState();

  switch (command.name) {
    case 'clear':
      chatStore.clearMessages();
      return {
        status: 'success',
        message: 'Chat history cleared',
      };

    case 'help': {
      const commandStore = useCommandStore.getState();
      const commands = commandStore.availableCommands;
      const commandText = getCommandText(command, options);

      const helpText = commands
        .map((cmd) => `**/${cmd.name}** - ${cmd.description}`)
        .join('\n\n');

      appendSystemMessage(commandText, helpText, 'success', 'Help displayed', {
        commandCount: commands.length,
      });

      return {
        status: 'success',
        message: 'Help displayed',
        data: {
          commands,
        },
      };
    }

    case 'theme': {
      const themeStore = useThemeStore.getState();
      const args = options?.args ?? [];
      const commandText = getCommandText(command, options);
      const firstArg = args[0]?.toLowerCase();

      let nextTheme: ThemePreference;
      let source: 'toggle' | 'explicit' | 'system';

      if (!firstArg) {
        nextTheme = themeStore.toggleTheme();
        source = 'toggle';
      } else if (firstArg === 'light' || firstArg === 'dark') {
        themeStore.setTheme(firstArg);
        nextTheme = firstArg;
        source = 'explicit';
      } else if (firstArg === THEME_OPTION_SYSTEM) {
        nextTheme = themeStore.resetToSystem();
        source = THEME_OPTION_SYSTEM;
      } else {
        const errorMessage = `Unsupported theme option: ${args[0]}. Use /theme [light|dark|system].`;
        appendSystemMessage(commandText, errorMessage, 'error', errorMessage);
        return {
          status: 'error',
          message: errorMessage,
        };
      }

      const resultText = formatThemeResult(nextTheme, source);
      appendSystemMessage(commandText, resultText, 'success', resultText, {
        theme: nextTheme,
        source,
      });

      return {
        status: 'success',
        message: resultText,
        data: {
          theme: nextTheme,
          source,
        },
      };
    }

    default:
      console.warn(`Unknown client command: ${command.name}`);
      return {
        status: 'error',
        message: `Unknown client command: ${command.name}`,
      };
  }
}

/**
 * Execute a WebSocket command
 *
 * Handles commands that require real-time server communication
 * via WebSocket (e.g., /identity).
 */
async function executeWebSocketCommand(
  command: Command,
  options?: CommandExecutionOptions
): Promise<CommandResult> {
  if (!websocketManager.connected) {
    const error = 'Cannot execute server command: not connected to NEXUS';
    console.error(error);
    return {
      status: 'error',
      message: error,
    };
  }

  const commandText = getCommandText(command, options);

  const requiresSignature = command.requiresSignature || command.name === 'identity';
  let auth: { publicKey: string; signature: string } | undefined;

  if (requiresSignature) {
    try {
      auth = await IdentityService.signCommand(commandText);
    } catch (error) {
      console.error('Failed to sign command:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to sign command';
      return {
        status: 'error',
        message: errorMessage,
      };
    }
  }

  const pendingMsg: Message = {
    id: uuidv4(),
    role: 'SYSTEM',
    content: { command: commandText },
    timestamp: new Date(),
    metadata: { status: 'pending' },
  };

  useChatStore.setState((state) => ({
    messages: [...state.messages, pendingMsg],
  }));

  websocketManager.sendCommand(commandText, auth);

  return {
    status: 'pending',
    message: 'Command sent to server',
  };
}

/**
 * Execute a REST command
 */
async function executeRestCommand(
  command: Command,
  options?: CommandExecutionOptions
): Promise<CommandResult> {
  if (!command.restOptions) {
    return {
      status: 'error',
      message: `REST command ${command.name} missing restOptions configuration`,
    };
  }

  try {
    const { endpoint, method, headers = {} } = command.restOptions;
    const baseURL = getNexusConfig().apiUrl;

    const response = await fetch(`${baseURL}${endpoint}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...headers,
      },
      body: method !== 'GET' ? JSON.stringify(options?.payload ?? {}) : undefined,
    });

    if (!response.ok) {
      throw new Error(`REST command failed: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      status: 'success',
      message: `Command ${command.name} executed successfully`,
      data,
    };
  } catch (error) {
    console.error(`REST command ${command.name} failed:`, error);
    return {
      status: 'error',
      message: error instanceof Error ? error.message : 'REST command failed',
    };
  }
}

/**
 * Main command executor
 */
export async function executeCommand(
  command: Command,
  options?: CommandExecutionOptions
): Promise<CommandResult> {
  try {
    if (isGUICommand(command)) {
      const modalType = command.name as Exclude<ModalType, null>;
      useUIStore.getState().openModal(modalType);
      return {
        status: 'success',
        message: `Opening ${command.name} panel`,
      };
    }

    if (isClientCommand(command)) {
      return await executeClientCommand(command, options);
    }

    if (isWebSocketCommand(command)) {
      return await executeWebSocketCommand(command, options);
    }

    if (isRestCommand(command)) {
      return await executeRestCommand(command, options);
    }

    return {
      status: 'error',
      message: `Unknown command handler type: ${command.handler}`,
    };
  } catch (error) {
    console.error(`Command execution error for ${command.name}:`, error);
    return {
      status: 'error',
      message: error instanceof Error ? error.message : 'Command execution failed',
    };
  }
}
