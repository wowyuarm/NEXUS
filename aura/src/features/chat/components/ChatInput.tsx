// src/features/chat/components/ChatInput.tsx
import { ArrowUp } from 'lucide-react';
import { useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import { Button, AutoResizeTextarea, type AutoResizeTextareaRef } from '@/components/ui';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, disabled = false }) => {
  const [message, setMessage] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const textareaRef = useRef<AutoResizeTextareaRef>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled && !isComposing) {
      onSendMessage(message.trim());
      setMessage('');

      // 重置 textarea 高度
      textareaRef.current?.resetHeight();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const canSend = message.trim().length > 0 && !disabled;

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
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => setIsComposing(true)}
            onCompositionEnd={() => setIsComposing(false)}
            placeholder="继续探索..."
            disabled={disabled}
            maxHeightMultiplier={2}
            minRows={3}
            className="px-4 pr-12"
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