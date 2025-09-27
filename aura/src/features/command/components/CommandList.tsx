/**
 * CommandList Component
 *
 * A lightweight command list that appears directly above the ChatInput
 * when the user starts typing a command. This is not a modal or popup,
 * but rather a natural extension of the ChatInput interface.
 *
 * Design Principles:
 * - Silent design: No unnecessary text or guidance
 * - Instant response: Uses predefined commands for immediate filtering
 * - Natural integration: Appears as part of the ChatInput flow
 * - Minimal footprint: Simple, focused interface
 */

import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { Command } from '../commands';

interface CommandListProps {
  isOpen: boolean;
  query: string;
  availableCommands: Command[];
  selectedIndex: number;
  onClose: () => void;
  onExecute: (command: string) => void;
  onSelectIndex: (index: number) => void;
}

export const CommandList: React.FC<CommandListProps> = ({
  isOpen,
  query,
  availableCommands,
  selectedIndex,
  onClose,
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
      if (selectedItem) {
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
        initial={{ opacity: 0, y: -10, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -10, scale: 0.95 }}
        transition={{ duration: 0.15, ease: 'easeOut' }}
        className="absolute bottom-full left-0 right-0 mb-2 z-40"
      >
        {/* Command List Container */}
        <div
          ref={listRef}
          className="bg-card border border-border rounded-lg shadow-lg shadow-black/20 overflow-hidden max-h-48 overflow-y-auto"
        >
          {filteredCommands.length > 0 ? (
            filteredCommands.map((command, index) => (
              <motion.button
                key={command.name}
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.03 }}
                className={cn(
                  "w-full p-3 text-left border-b border-border last:border-b-0 transition-colors",
                  "hover:bg-accent/50 focus:bg-accent/50 outline-none",
                  selectedIndex === index && "bg-accent/30"
                )}
                onClick={() => handleCommandClick(command)}
                onMouseEnter={() => onSelectIndex(index)}
              >
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
                    <span className="text-primary font-medium text-xs">
                      {command.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-foreground text-sm">
                      /{command.name}
                    </div>
                    <div className="text-xs text-muted-foreground truncate">
                      {command.description}
                    </div>
                  </div>
                </div>
              </motion.button>
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