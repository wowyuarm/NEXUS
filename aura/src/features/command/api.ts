/**
 * Command API Client
 * 
 * Handles REST API communication with NEXUS backend for command-related operations.
 * This module is responsible for fetching command definitions and metadata.
 */

import type { Command } from './command.types';

/**
 * Base API URL - configurable via environment variable
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * API Error class for structured error handling
 */
export class CommandAPIError extends Error {
  statusCode?: number;
  details?: unknown;

  constructor(
    message: string,
    statusCode?: number,
    details?: unknown
  ) {
    super(message);
    this.name = 'CommandAPIError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Fetch all available commands from the backend
 * 
 * Makes a GET request to /api/v1/commands to retrieve the list of
 * all registered commands with their metadata.
 * 
 * @returns Promise resolving to array of Command objects
 * @throws CommandAPIError if the request fails
 * 
 * @example
 * ```ts
 * const commands = await fetchCommands();
 * console.log(`Loaded ${commands.length} commands`);
 * ```
 */
export async function fetchCommands(): Promise<Command[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/commands`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new CommandAPIError(
        `Failed to fetch commands: ${response.statusText}`,
        response.status,
        errorText
      );
    }

    const commands: Command[] = await response.json();
    return commands;

  } catch (error) {
    if (error instanceof CommandAPIError) {
      throw error;
    }
    
    // Network or parsing errors
    throw new CommandAPIError(
      `Network error while fetching commands: ${error instanceof Error ? error.message : 'Unknown error'}`,
      undefined,
      error
    );
  }
}

/**
 * Fetch a specific command by name
 * 
 * @param commandName - Name of the command to fetch
 * @returns Promise resolving to Command object or null if not found
 * @throws CommandAPIError if the request fails
 * 
 * @example
 * ```ts
 * const helpCmd = await fetchCommand('help');
 * if (helpCmd) {
 *   console.log(helpCmd.description);
 * }
 * ```
 */
export async function fetchCommand(commandName: string): Promise<Command | null> {
  const commands = await fetchCommands();
  return commands.find(cmd => cmd.name === commandName) || null;
}

/**
 * Health check for the API
 * 
 * @returns Promise resolving to health status object
 */
export async function checkAPIHealth(): Promise<{ status: string; dependencies?: Record<string, string> }> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/health`);
    return await response.json();
  } catch (error) {
    throw new CommandAPIError(
      `Health check failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      undefined,
      error
    );
  }
}

