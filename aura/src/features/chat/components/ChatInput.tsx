// src/features/chat/components/ChatInput.tsx
import { ArrowUp } from 'lucide-react';
import { useRef, useState, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Button, AutoResizeTextarea, type AutoResizeTextareaRef } from '@/components/ui';
import { useChatStore } from '@/features/chat/store/chatStore';
import type { Command } from '@/features/command/command.types';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  // Command props
  isPaletteOpen: boolean;
  query: string;
  availableCommands: Command[];
  selectedCommandIndex: number;
  onOpenPalette: () => void;
  onClosePalette: () => void;
  onSetQuery: (query: string) => void;
  onSetSelectedCommandIndex: (index: number) => void;
  onExecuteCommand: (command: string) => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled = false,
  // Command props
  isPaletteOpen,
  query,
  availableCommands,
  selectedCommandIndex,
  onOpenPalette,
  onClosePalette,
  onSetQuery,
  onSetSelectedCommandIndex,
  onExecuteCommand,
}) => {
  const visitorMode = useChatStore(s => s.visitorMode);
  const [message, setMessage] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const textareaRef = useRef<AutoResizeTextareaRef>(null);

  // Filter commands by current query for navigation and execution
  const filteredCommands = useMemo(() => {
    const queryLower = (query || '').toLowerCase();
    if (!queryLower) return availableCommands;
    return availableCommands.filter(cmd =>
      cmd.name.toLowerCase().startsWith(queryLower)
    );
  }, [availableCommands, query]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled && !isComposing) {
      // Check if this is a command (starts with /)
      if (message.trim().startsWith('/')) {
        onExecuteCommand(message.trim());
      } else {
        // In visitor mode, only allow /identity; the store/backend will gatekeep,
        // but we reflect same UX by encouraging identity setup when blocked.
        onSendMessage(message.trim());
      }
      setMessage('');

      // Reset textarea height
      textareaRef.current?.resetHeight();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isPaletteOpen) {
      switch (e.key) {
        case 'Escape':
          e.preventDefault();
          onClosePalette();
          break;
        case 'ArrowUp':
          e.preventDefault();
          if (filteredCommands.length > 0) {
            onSetSelectedCommandIndex(
              selectedCommandIndex > 0 ? selectedCommandIndex - 1 : filteredCommands.length - 1
            );
          }
          break;
        case 'ArrowDown':
          e.preventDefault();
          if (filteredCommands.length > 0) {
            onSetSelectedCommandIndex(
              selectedCommandIndex < filteredCommands.length - 1 ? selectedCommandIndex + 1 : 0
            );
          }
          break;
        case 'Enter':
          e.preventDefault();
          if (filteredCommands[selectedCommandIndex]) {
            onExecuteCommand(`/${filteredCommands[selectedCommandIndex].name}`);
            // After executing the command, clear the input and reset the height
            setMessage('');
            textareaRef.current?.resetHeight();
          }
          break;
        default:
          // Allow normal typing
          break;
      }
    } else if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setMessage(value);

    // Handle command list logic - only activate when / is the first character
    if (value.startsWith('/') && value.length === 1) {
      // Only open command list when / is the first and only character
      if (!isPaletteOpen) {
        onOpenPalette();
        onSetSelectedCommandIndex(0);
      }
      onSetQuery('');
    } else if (value.startsWith('/') && value.length > 1) {
      // Continue filtering commands as user types after /
      const queryStr = value.slice(1);
      onSetQuery(queryStr);
      // Smart selection: prefer exact match if present, otherwise first item
      const lower = queryStr.toLowerCase();
      const matching = availableCommands.filter(cmd => cmd.name.toLowerCase().startsWith(lower));
      if (matching.length === 0) {
        onSetSelectedCommandIndex(-1);
      } else {
        const exactIdx = matching.findIndex(cmd => cmd.name.toLowerCase() === lower);
        onSetSelectedCommandIndex(exactIdx >= 0 ? exactIdx : 0);
      }
    } else if (isPaletteOpen) {
      // Close command list if user deletes the / or types non-command text
      onClosePalette();
    }
  };

  const canSend = message.trim().length > 0 && !disabled;

  // Dynamic placeholder based on command mode
  const placeholder = isPaletteOpen ? '/' : (visitorMode ? '输入 /identity 以完成身份验证' : '继续探索...');

  return (
    <div className="w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="relative">
        <div className={cn(
          'relative rounded-2xl border border-border shadow-lg shadow-black/20',
          'bg-card/75 backdrop-blur-xl',
          'transition-colors duration-200',
          'hover:border-foreground/20'
        )}>
          <AutoResizeTextarea
            ref={textareaRef}
            value={message}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => setIsComposing(true)}
            onCompositionEnd={() => setIsComposing(false)}
            placeholder={placeholder}
            disabled={disabled}
            maxHeightMultiplier={2}
            minRows={3}
            className="px-4 pr-6"
          />
          <Button
            type="submit"
            variant="primary"
            size="md"
            icon={<ArrowUp size={18} />}
            iconOnly
            disabled={!canSend}
            className="absolute right-2 bottom-2"
          />
        </div>
      </form>
    </div>
  );
};