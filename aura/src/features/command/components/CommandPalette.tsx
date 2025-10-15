/**
 * CommandPalette Component
 *
 * A lightweight command palette that appears directly above the ChatInput
 * when the user starts typing a command. This is not a modal or popup,
 * but rather a natural extension of the ChatInput interface.
 *
 * Design Principles:
 * - Silent design: No unnecessary text or guidance
 * - Instant response: Uses predefined commands for immediate filtering
 * - Natural integration: Appears as part of the ChatInput flow
 * - Minimal footprint: Simple, focused interface
 * - Unified interaction: Uses Button component with variant='command'
 */

import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui';
import type { Command } from '../command.types';
import { FRAMER_TRANSITION } from '@/lib/motion';

interface CommandPaletteProps {
  isOpen: boolean;
  query: string;
  availableCommands: Command[];
  selectedIndex: number;
  onExecute: (command: string) => void;
  onSelectIndex: (index: number) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  query,
  availableCommands,
  selectedIndex,
  onExecute,
  onSelectIndex,
}) => {
  const listRef = useRef<HTMLDivElement>(null);

  // Filter commands to only show those starting with the query
  const filteredCommands = availableCommands.filter(command =>
    command.name.toLowerCase().startsWith(query.toLowerCase())
  );

  // Auto-scroll selected item into view
  useEffect(() => {
    if (listRef.current && selectedIndex >= 0) {
      const selectedItem = listRef.current.children[selectedIndex] as HTMLElement;
      if (selectedItem && 'scrollIntoView' in selectedItem && typeof selectedItem.scrollIntoView === 'function') {
        selectedItem.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex]);

  // Handle command execution
  const handleCommandClick = (command: Command) => {
    onExecute(`/${command.name}`);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 8 }}
        transition={FRAMER_TRANSITION}
        className="absolute bottom-full left-0 right-0 mb-2 z-40"
      >
        {/* Command Palette Container */}
        <div
          ref={listRef}
          className="bg-card border border-border rounded-lg shadow-lg shadow-black/20 overflow-hidden max-h-[30vh] overflow-y-auto"
        >
          {filteredCommands.length > 0 ? (
            filteredCommands.map((command, index) => (
              <motion.div
                key={command.name}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.02 }}
              >
                <Button
                  variant="command"
                  size="md"
                  fullWidth
                  className={cn(
                    "transition-colors outline-none",
                    selectedIndex === index && "bg-accent/30"
                  )}
                  onClick={() => handleCommandClick(command)}
                  onMouseEnter={() => onSelectIndex(index)}
                >
                  {/* Structured two-column layout */}
                  <div className="flex items-baseline gap-4">
                    {/* Left column: Command name - fixed min width, font-mono */}
                    <div className="min-w-[8rem] flex-shrink-0">
                      <span className="font-mono text-sm text-foreground">
                        /{command.name}
                      </span>
                    </div>
                    
                    {/* Right column: Command description - fills remaining space */}
                    <div className="flex-1 min-w-0">
                      <span className="text-sm text-secondary-foreground">
                        {command.description}
                      </span>
                    </div>
                  </div>
                </Button>
              </motion.div>
            ))
          ) : (
            // Silent empty state - no text, just empty space
            <div className="h-12" />
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

