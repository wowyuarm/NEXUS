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

import type { Command, CommandResult } from './command.types';
import { isClientCommand, isWebSocketCommand, isRestCommand } from './command.types';
import { websocketManager } from '@/services/websocket/manager';
import { IdentityService } from '@/services/identity/identity';
import { useChatStore } from '@/features/chat/store/chatStore';

/**
 * Execute a client-side command
 * 
 * Handles commands that run entirely in the browser without
 * backend communication (e.g., /clear).
 * 
 * @param command - Command definition
 * @param args - Optional command arguments
 * @returns Promise resolving to command result
 */
async function executeClientCommand(
  command: Command
  // args parameter reserved for future use
): Promise<CommandResult> {
  const chatStore = useChatStore.getState();
  
  switch (command.name) {
    case 'clear':
      chatStore.clearMessages();
      return {
        status: 'success',
        message: 'Chat history cleared'
      };
      
    case 'help': {
      // Client-side help rendering (if commands are already loaded)
      // This is handled specially in chatStore for now
      // Future: move help rendering logic here
      return {
        status: 'success',
        message: 'Help displayed',
        data: { handled: 'by_chat_store' }
      };
    }
      
    default:
      console.warn(`Unknown client command: ${command.name}`);
      return {
        status: 'error',
        message: `Unknown client command: ${command.name}`
      };
  }
}

/**
 * Execute a WebSocket command
 * 
 * Handles commands that require real-time server communication
 * via WebSocket (e.g., /identity, /help on first load).
 * 
 * @param command - Command definition
 * @param args - Optional command arguments
 * @returns Promise resolving to command result
 */
async function executeWebSocketCommand(
  command: Command
  // args parameter reserved for future use
): Promise<CommandResult> {
  if (!websocketManager.connected) {
    const error = 'Cannot execute server command: not connected to NEXUS';
    console.error(error);
    return {
      status: 'error',
      message: error
    };
  }

  const commandText = `/${command.name}`;

  // Check if command requires signature
  const requiresSignature = command.requiresSignature || command.name === 'identity';
  let auth: { publicKey: string; signature: string } | undefined;

  if (requiresSignature) {
    try {
      auth = await IdentityService.signCommand(commandText);
      console.log('✍️ Signed command:', command.name);
    } catch (error) {
      console.error('Failed to sign command:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to sign command';
      return {
        status: 'error',
        message: errorMessage
      };
    }
  }

  // Note: Command result handling will be done by WebSocket event handlers in chatStore

  // For help command (first load only), register listener BEFORE sending
  if (command.name === 'help') {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Help command timeout'));
      }, 5000);

      const handleCommandResult = (data: unknown) => {
        const isHelpResponse = Boolean(
          data && typeof data === 'object' && 'status' in data && 'data' in data && 
          data.data && typeof data.data === 'object' && 'commands' in data.data
        );
        if (isHelpResponse) {
          clearTimeout(timeout);
          websocketManager.off('command_result', handleCommandResult);
          resolve(data as CommandResult);
        }
      };

      websocketManager.on('command_result', handleCommandResult);
      websocketManager.sendCommand(commandText, auth);
    });
  }

  // Default: send command after pending message (with auth if signed)
  websocketManager.sendCommand(commandText, auth);
  return {
    status: 'pending',
    message: 'Command sent to server'
  };
}

/**
 * Execute a REST command
 * 
 * Handles commands that use HTTP REST API for communication.
 * This is for future stateless operations.
 * 
 * @param command - Command definition
 * @param args - Optional command arguments
 * @returns Promise resolving to command result
 */
async function executeRestCommand(
  command: Command,
  args?: Record<string, unknown>
): Promise<CommandResult> {
  if (!command.restOptions) {
    return {
      status: 'error',
      message: `REST command ${command.name} missing restOptions configuration`
    };
  }

  try {
    const { endpoint, method, headers = {} } = command.restOptions;
    const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    
    const response = await fetch(`${baseURL}${endpoint}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...headers
      },
      body: method !== 'GET' ? JSON.stringify(args) : undefined
    });

    if (!response.ok) {
      throw new Error(`REST command failed: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      status: 'success',
      message: `Command ${command.name} executed successfully`,
      data
    };

  } catch (error) {
    console.error(`REST command ${command.name} failed:`, error);
    return {
      status: 'error',
      message: error instanceof Error ? error.message : 'REST command failed'
    };
  }
}

/**
 * Main command executor
 * 
 * Routes commands to the appropriate handler based on their handler type.
 * This is the primary entry point for command execution in the application.
 * 
 * @param command - Command definition
 * @param args - Optional command arguments
 * @returns Promise resolving to command result
 * 
 * @example
 * ```ts
 * const result = await executeCommand(clearCommand);
 * if (result.status === 'success') {
 *   console.log('Command executed successfully');
 * }
 * ```
 */
export async function executeCommand(
  command: Command,
  args?: Record<string, unknown>
): Promise<CommandResult> {
  console.log(`[CommandExecutor] Executing command: ${command.name} (handler: ${command.handler})`);

  try {
    // Route to appropriate handler
    if (isClientCommand(command)) {
      return await executeClientCommand(command);
    } else if (isWebSocketCommand(command)) {
      return await executeWebSocketCommand(command);
    } else if (isRestCommand(command)) {
      return await executeRestCommand(command, args);
    } else {
      return {
        status: 'error',
        message: `Unknown command handler type: ${command.handler}`
      };
    }
  } catch (error) {
    console.error(`Command execution error for ${command.name}:`, error);
    return {
      status: 'error',
      message: error instanceof Error ? error.message : 'Command execution failed'
    };
  }
}

