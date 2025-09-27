/**
 * Frontend Predefined Commands
 *
 * This file contains the hardcoded list of deterministic commands available in the system.
 * By predefining commands on the frontend, we ensure instant response and reliability
 * without the need for network requests to discover available commands.
 */

export interface Command {
  name: string;
  description: string;
}

export const COMMANDS: Command[] = [
  { name: 'ping', description: 'Check connection to the NEXUS core.' },
  { name: 'help', description: 'Display information about available commands.' },
  { name: 'identity', description: 'Manage your user identity.' }
];

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

/**
 * Execute help command locally (no backend communication needed)
 */
export const executeHelpCommand = (commands: Command[]): string => {
  const commandList = commands.map(cmd => `- **/${cmd.name}**: ${cmd.description}`).join('\n');
  return `Available commands:\n\n${commandList}`;
};