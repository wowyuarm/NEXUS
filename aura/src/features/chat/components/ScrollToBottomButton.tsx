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
          initial="hidden"
          animate="visible"
          exit="exit"
          variants={{
            hidden: { opacity: 0, y: 0 },
            visible: {
              opacity: 1,
              y: 0,
              transition: { duration: 0.24, ease: [0.16, 1, 0.3, 1] }
            },
            exit: {
              opacity: 0,
              y: 0,
              transition: { duration: 0.16, ease: 'easeOut' }
            }
          }}
          onClick={onClick}
          className={cn(
            // 基础样式 - 调整位置与输入框对齐
            // bottom-[6.5rem] 约等于输入框容器的高度 (p-6 + 输入框高度)
            'fixed bottom-[6.5rem] right-6 z-10',
            'w-10 h-10 rounded-full',
            // GPU 加速与渲染提示
            'transform-gpu will-change-transform [will-change:filter]',

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
          whileHover={{ scale: 1.06 }}
          whileTap={{ scale: 0.96 }}
        >
          <ChevronDown className="w-5 h-5" />
        </motion.button>
      )}
    </AnimatePresence>
  );
};
