// src/features/chat/components/ScrollToBottomButton.tsx
// 滚动到底部按钮组件 - 使用统一的 Button 组件
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui';
import { FRAMER, MOTION_EXIT } from '@/lib/motion';

interface ScrollToBottomButtonProps {
  /** 是否显示按钮 */
  show: boolean;
  /** 点击回调 */
  onClick: () => void;
  /** 自定义类名 */
  className?: string;
  /** 按钮位置：视口固定或输入框上方 */
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
