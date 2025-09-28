// src/features/chat/components/ChatInput.tsx
import { ArrowUp } from 'lucide-react';
import { useRef, useState, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Button, AutoResizeTextarea, type AutoResizeTextareaRef } from '@/components/ui';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  // Command props
  isCommandListOpen: boolean;
  commandQuery: string;
  availableCommands: Array<{ name: string; description: string }>;
  selectedCommandIndex: number;
  onOpenCommandList: () => void;
  onCloseCommandList: () => void;
  onSetCommandQuery: (query: string) => void;
  onSetSelectedCommandIndex: (index: number) => void;
  onExecuteCommand: (command: string) => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled = false,
  // Command props
  isCommandListOpen,
  commandQuery,
  availableCommands,
  selectedCommandIndex,
  onOpenCommandList,
  onCloseCommandList,
  onSetCommandQuery,
  onSetSelectedCommandIndex,
  onExecuteCommand,
}) => {
  const [message, setMessage] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const textareaRef = useRef<AutoResizeTextareaRef>(null);

  // Filter commands by current query for navigation and execution
  const filteredCommands = useMemo(() => {
    const query = (commandQuery || '').toLowerCase();
    if (!query) return availableCommands;
    return availableCommands.filter(cmd =>
      cmd.name.toLowerCase().startsWith(query)
    );
  }, [availableCommands, commandQuery]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled && !isComposing) {
      // Check if this is a command (starts with /)
      if (message.trim().startsWith('/')) {
        onExecuteCommand(message.trim());
      } else {
        onSendMessage(message.trim());
      }
      setMessage('');

      // 重置 textarea 高度
      textareaRef.current?.resetHeight();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isCommandListOpen) {
      switch (e.key) {
        case 'Escape':
          e.preventDefault();
          onCloseCommandList();
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
      if (!isCommandListOpen) {
        onOpenCommandList();
        onSetSelectedCommandIndex(0);
      }
      onSetCommandQuery('');
    } else if (value.startsWith('/') && value.length > 1) {
      // Continue filtering commands as user types after /
      const query = value.slice(1);
      onSetCommandQuery(query);
      // Smart selection: prefer exact match if present, otherwise first item
      const lower = query.toLowerCase();
      const matching = availableCommands.filter(cmd => cmd.name.toLowerCase().startsWith(lower));
      if (matching.length === 0) {
        onSetSelectedCommandIndex(-1);
      } else {
        const exactIdx = matching.findIndex(cmd => cmd.name.toLowerCase() === lower);
        onSetSelectedCommandIndex(exactIdx >= 0 ? exactIdx : 0);
      }
    } else if (isCommandListOpen) {
      // Close command list if user deletes the / or types non-command text
      onCloseCommandList();
    }
  };

  const canSend = message.trim().length > 0 && !disabled;

  // Dynamic placeholder based on command mode
  const placeholder = isCommandListOpen ? '/' : '继续探索...';

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