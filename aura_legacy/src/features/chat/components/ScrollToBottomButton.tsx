// src/features/chat/components/ScrollToBottomButton.tsx
// 滚动到底部按钮组件 - 符合设计系统的浮动按钮
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ScrollToBottomButtonProps {
  /** 是否显示按钮 */
  show: boolean;
  /** 点击回调 */
  onClick: () => void;
  /** 自定义类名 */
  className?: string;
}

export const ScrollToBottomButton: React.FC<ScrollToBottomButtonProps> = ({
  show,
  onClick,
  className
}) => {
  return (
    <AnimatePresence>
      {show && (
        <motion.button
          initial={{ opacity: 0, y: 10, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.9 }}
          transition={{
            duration: 0.2,
            ease: [0.22, 1, 0.36, 1]
          }}
          onClick={onClick}
          className={cn(
            // 基础样式 - 调整位置与输入框对齐
            // bottom-[6.5rem] 约等于输入框容器的高度 (p-6 + 输入框高度)
            'fixed bottom-[6.5rem] right-6 z-10',
            'w-10 h-10 rounded-full',
            
            // 标准材质
            'bg-card/75 backdrop-blur-xl',
            'border border-border',
            'shadow-lg shadow-black/20',
            
            // 交互状态
            'hover:bg-white/[.02] active:scale-95',
            'transition-all duration-300 ease-in-out',
            
            // 内容居中
            'flex items-center justify-center',
            'text-secondary-foreground hover:text-foreground',
            
            className
          )}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <ChevronDown className="w-5 h-5" />
        </motion.button>
      )}
    </AnimatePresence>
  );
};
