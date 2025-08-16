// src/components/ui/RoleSymbol.tsx
// 角色符号组件 - 使用纯文本几何符号表示不同角色
import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface RoleSymbolProps {
  role: 'HUMAN' | 'AI' | 'SYSTEM' | 'TOOL';
  isThinking?: boolean;
}

// 角色符号映射 - 独立一列显示，尺寸增大
export const RoleSymbol: React.FC<RoleSymbolProps> = ({ role, isThinking = false }) => {
  const symbols = {
    HUMAN: '▲', 
    AI: '●', 
    SYSTEM: '■', 
    TOOL: '◆'     
  };

  return (
    <motion.div
      className={cn(
        'flex items-center justify-center w-8 h-8',
        'text-secondary-foreground text-lg font-mono select-none',
        'flex-shrink-0', // 防止收缩
        isThinking && 'animate-pulse'
      )}
      animate={isThinking ? { opacity: [0.4, 1, 0.4] } : {}}
      transition={isThinking ? { duration: 2, repeat: Infinity, ease: 'easeInOut' } : {}}
    >
      {symbols[role]}
    </motion.div>
  );
};
