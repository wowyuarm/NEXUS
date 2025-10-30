// src/features/chat/components/ScrollToBottomButton.tsx
// Scroll to bottom button component - uses unified Button component
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui';
import { FRAMER, MOTION_EXIT } from '@/lib/motion';

interface ScrollToBottomButtonProps {
  /** Whether to show the button */
  show: boolean;
  /** Click callback */
  onClick: () => void;
  /** Custom class name */
  className?: string;
  /** Button position: viewport fixed or above input box */
  placement?: 'viewport' | 'above-input';
}

export const ScrollToBottomButton: React.FC<ScrollToBottomButtonProps> = ({
  show,
  onClick,
  className,
  placement = 'viewport'
}) => {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 0 }}
          animate={{ 
            opacity: 1, 
            y: 0,
            transition: FRAMER.transition
          }}
          exit={{ 
            opacity: 0, 
            y: 0,
            transition: { duration: MOTION_EXIT.transition, ease: MOTION_EXIT.ease }
          }}
          className={cn(
            placement === 'viewport'
              ? 'fixed bottom-[6.5rem] right-6 z-10'
              : 'absolute bottom-full right-0 mb-2 z-10',
            className
          )}
        >
          <Button
            variant="icon"
            size="md"
            icon={<ChevronDown className="w-5 h-5" />}
            iconOnly
            onClick={onClick}
            aria-label="滚动到底部"
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
};
