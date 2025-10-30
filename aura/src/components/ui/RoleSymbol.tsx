// src/components/ui/RoleSymbol.tsx
// Role symbol component - uses plain text geometric symbols to represent different roles
import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface RoleSymbolProps {
  role: 'HUMAN' | 'AI' | 'SYSTEM' | 'TOOL';
  isThinking?: boolean;
  status?: 'pending' | 'completed';
}

// Role symbol mapping - displayed in separate column with increased size
export const RoleSymbol: React.FC<RoleSymbolProps> = ({ role, isThinking = false, status }) => {
  const symbols = {
    HUMAN: '▲',
    AI: '●',
    SYSTEM: '■',
    TOOL: '◆'
  };

  // Determine animation based on isThinking or status
  const shouldPulse = isThinking || status === 'pending';

  return (
    <motion.div
      initial={false}
      className={cn(
        'flex items-center justify-center',
        // Mobile: 32x32px, 18px font (larger for vertical layout, no horizontal space constraint)
        'w-8 h-8 text-[18px]',
        // Desktop (≥768px): 40x40px, 22px font (prominent but not overwhelming)
        'md:w-10 md:h-10 md:text-[22px]',
        'text-secondary-foreground leading-none font-mono select-none',
        'flex-shrink-0' // Prevent shrinking
      )}
      animate={shouldPulse ? { opacity: [0.4, 1, 0.4] } : { opacity: 1 }}
      transition={
        shouldPulse
          ? { duration: 2, repeat: Infinity, ease: 'easeInOut' }
          : { duration: 0.2, ease: 'easeOut' }
      }
    >
      {symbols[role]}
    </motion.div>
  );
};
