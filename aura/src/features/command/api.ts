/**
 * Command API Client
 * 
 * Handles REST API communication with NEXUS backend for command-related operations.
 * This module is responsible for fetching command definitions and metadata.
 */

import type { Command } from './command.types';
import { getNexusConfig } from '../../config/nexus';

/**
 * Base API URL - from centralized configuration
 */
const API_BASE_URL = getNexusConfig().apiUrl;

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
    const response = await fetch(`${API_BASE_URL}/commands`, {
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
    const response = await fetch(`${API_BASE_URL}/health`);
    return await response.json();
  } catch (error) {
    throw new CommandAPIError(
      `Health check failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      undefined,
      error
    );
  }
}

/**
 * Configuration API Response Interface
 */
export interface ConfigResponse {
  effective_config: Record<string, unknown>;
  effective_prompts: Record<string, unknown>;
  user_overrides: {
    config_overrides: Record<string, unknown>;
    prompt_overrides: Record<string, unknown>;
  };
  editable_fields: string[];
  field_options: Record<string, unknown>;
}

/**
 * Fetch user configuration with UI metadata
 * 
 * Makes a GET request to /api/v1/config with Bearer token authentication.
 * Returns the effective configuration merged with user overrides, plus
 * UI metadata for dynamic form rendering.
 * 
 * @returns Promise resolving to ConfigResponse object
 * @throws CommandAPIError if the request fails or auth token is missing
 * 
 * @example
 * ```ts
 * const config = await fetchConfig();
 * console.log(config.effective_config.model); // "gemini-2.5-flash"
 * console.log(config.editable_fields); // ["config.model", "config.temperature", ...]
 * ```
 */
export async function fetchConfig(): Promise<ConfigResponse> {
  try {
    // Get identity from IdentityService
    const { IdentityService } = await import('@/services/identity/identity');
    const identity = await IdentityService.getIdentity();
    
    if (!identity || !identity.publicKey) {
      throw new CommandAPIError(
        'Authentication required: No identity found',
        401
      );
    }

    const response = await fetch(`${API_BASE_URL}/config`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${identity.publicKey}`,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new CommandAPIError(
        `Failed to fetch config: ${response.statusText}`,
        response.status,
        errorText
      );
    }

    const config: ConfigResponse = await response.json();
    return config;

  } catch (error) {
    if (error instanceof CommandAPIError) {
      throw error;
    }
    
    throw new CommandAPIError(
      `Network error while fetching config: ${error instanceof Error ? error.message : 'Unknown error'}`,
      undefined,
      error
    );
  }
}

/**
 * Save user configuration overrides
 * 
 * Makes a POST request to /api/v1/config with signature verification.
 * Only the provided overrides are updated; other fields remain unchanged.
 * 
 * @param overrides - Configuration fields to update (e.g., {model: "deepseek-chat", temperature: 0.9})
 * @param auth - Authentication object with publicKey and signature
 * @returns Promise resolving to success status
 * @throws CommandAPIError if the request fails
 * 
 * @example
 * ```ts
 * const auth = await IdentityService.signCommand('/config');
 * const result = await saveConfig({ model: "deepseek-chat" }, auth);
 * console.log(result.message); // "Configuration updated successfully"
 * ```
 */
export async function saveConfig(
  overrides: Record<string, unknown>,
  auth: { publicKey: string; signature: string }
): Promise<{ status: string; message: string }> {
  try {
    // Use publicKey from auth object (must match the signer)
    // This ensures Bearer token and signature use the same identity
    if (!auth || !auth.publicKey) {
      throw new CommandAPIError(
        'Authentication required: Missing auth object',
        401
      );
    }

    const response = await fetch(`${API_BASE_URL}/config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${auth.publicKey}`,
      },
      body: JSON.stringify({
        overrides,
        auth,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new CommandAPIError(
        `Failed to save config: ${response.statusText}`,
        response.status,
        errorText
      );
    }

    const result = await response.json();
    return result;

  } catch (error) {
    if (error instanceof CommandAPIError) {
      throw error;
    }
    
    throw new CommandAPIError(
      `Network error while saving config: ${error instanceof Error ? error.message : 'Unknown error'}`,
      undefined,
      error
    );
  }
}

