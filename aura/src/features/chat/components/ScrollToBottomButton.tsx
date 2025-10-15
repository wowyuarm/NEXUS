// src/features/chat/components/ScrollToBottomButton.tsx
// 滚动到底部按钮组件 - 使用统一的 Button 组件
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui';
import { FRAMER_TRANSITION } from '@/lib/motion';

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
        <motion.div
          initial={{ opacity: 0, y: 0 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 0 }}
          transition={FRAMER_TRANSITION}
          className={cn(
            // 定位样式
            // bottom-[6.5rem] 约等于输入框容器的高度 (p-6 + 输入框高度)
            'fixed bottom-[6.5rem] right-6 z-10',
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
