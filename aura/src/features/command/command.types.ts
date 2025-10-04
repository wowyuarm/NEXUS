/**
 * Command Type Definitions
 * 
 * Core types for the command system, defining the contract between
 * frontend and backend for command discovery and execution.
 */

/**
 * Command handler type determines where and how a command is executed.
 * 
 * - 'client': Executed entirely on the client side (e.g., /clear)
 * - 'websocket': Executed on server, communicated via WebSocket (e.g., /identity)
 * - 'rest': Executed on server, communicated via REST API (future use)
 */
export type CommandHandler = 'client' | 'websocket' | 'rest';

/**
 * REST-specific configuration for commands that use HTTP REST API
 */
export interface RestOptions {
  /** REST endpoint path (e.g., '/api/v1/execute') */
  endpoint: string;
  /** HTTP method to use */
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  /** Optional: Additional headers to send */
  headers?: Record<string, string>;
}

/**
 * Core Command interface - the contract between frontend and backend
 * 
 * This interface defines the structure of commands as they are:
 * 1. Discovered from the backend via REST API (/api/v1/commands)
 * 2. Stored in the frontend command registry
 * 3. Executed through the command executor
 */
export interface Command {
  /** Unique command name (without slash prefix) */
  name: string;
  
  /** Human-readable description of what the command does */
  description: string;
  
  /** Usage example showing how to invoke the command */
  usage: string;
  
  /** Determines how/where the command is executed */
  handler: CommandHandler;
  
  /** 
   * Legacy field for backward compatibility
   * Maps to handler: 'client' | 'server' -> 'client' | 'websocket'
   * @deprecated Use 'handler' instead
   */
  execution_target?: 'client' | 'server';
  
  /** REST configuration (required if handler is 'rest') */
  restOptions?: RestOptions;
  
  /** Example invocations of the command */
  examples: string[];
  
  /** Optional: Whether command requires signature authentication */
  requiresSignature?: boolean;
  
  /** Optional: Additional metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Command execution result returned by commandExecutor
 */
export interface CommandResult {
  status: 'success' | 'error' | 'pending';
  message: string;
  data?: Record<string, unknown>;
}

/**
 * Type guard to check if a command uses REST handler
 */
export function isRestCommand(command: Command): boolean {
  return command.handler === 'rest';
}

/**
 * Type guard to check if a command uses WebSocket handler
 */
export function isWebSocketCommand(command: Command): boolean {
  return command.handler === 'websocket' || command.execution_target === 'server';
}

/**
 * Type guard to check if a command uses client handler
 */
export function isClientCommand(command: Command): boolean {
  return command.handler === 'client' || command.execution_target === 'client';
}

/**
 * Normalize legacy command format to new format
 * Converts execution_target to handler for backward compatibility
 */
export function normalizeCommand(command: Command): Command {
  if (!command.handler && command.execution_target) {
    return {
      ...command,
      handler: command.execution_target === 'server' ? 'websocket' : 'client'
    };
  }
  return command;
}


