// src/components/common/LoadingState.tsx 
// 统一的加载状态组件，支持不同尺寸
import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface LoadingStateProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ 
  message = "加载中...",
  size = 'md',
  className 
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6', 
    lg: 'w-8 h-8'
  };

  return (
    <div className={cn(
      'flex flex-col items-center justify-center gap-3',
      className
    )}>
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
    </div>
  );
};
