// src/components/common/StatusIndicator.tsx
// 通用状态指示器组件 - 合并加载、空状态和错误状态的展示
import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface StatusIndicatorProps {
  variant: 'loading' | 'empty' | 'error';
  message?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  size?: 'sm' | 'md' | 'lg'; // 仅对loading状态有效
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  variant,
  message,
  icon,
  action,
  className,
  size = 'md'
}) => {
  // 统一的动画配置，遵循AURA的时间物理
  const fadeInAnimation = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.4, ease: 'easeOut' }
  };

  // Loading状态的渲染
  if (variant === 'loading') {
    const sizeClasses = {
      sm: 'w-4 h-4',
      md: 'w-6 h-6',
      lg: 'w-8 h-8'
    };

    return (
      <motion.div
        {...fadeInAnimation}
        className={cn(
          'flex flex-col items-center justify-center gap-3 py-8',
          className
        )}
      >
        <motion.div
          className={cn(
            'border-2 border-border rounded-full relative',
            sizeClasses[size]
          )}
          animate={{ rotate: 360 }}
          transition={{
            duration: 1,
            repeat: Infinity,
            ease: 'linear'
          }}
        >
          <div className="absolute inset-0 border-2 border-transparent border-t-foreground rounded-full" />
        </motion.div>
        {message && (
          <div className="text-sm text-secondary-foreground">
            {message}
          </div>
        )}
      </motion.div>
    );
  }

  // Empty状态的渲染
  if (variant === 'empty') {
    return (
      <motion.div
        {...fadeInAnimation}
        className={cn(
          'flex flex-col items-center justify-center text-center py-12',
          className
        )}
      >
        {icon && (
          <div className="mb-4 text-muted-foreground">
            {icon}
          </div>
        )}
        
        <h3 className="text-base font-medium text-foreground mb-2">
          {message || "暂无内容"}
        </h3>
        
        {action && (
          <div className="mt-4">
            {action}
          </div>
        )}
      </motion.div>
    );
  }

  // Error状态的渲染
  if (variant === 'error') {
    return (
      <motion.div
        {...fadeInAnimation}
        className={cn(
          'flex flex-col items-center justify-center text-center py-12',
          className
        )}
      >
        <div className="mb-4 text-destructive text-2xl">
          {icon || '⚠'}
        </div>
        
        <h3 className="text-base font-medium text-destructive mb-2">
          {message || "出现错误"}
        </h3>
        
        {action && (
          <div className="mt-4">
            {action}
          </div>
        )}
      </motion.div>
    );
  }

  return null;
};
