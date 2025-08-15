// src/components/common/ScrollArea.tsx
// 自定义滚动区域，支持不同方向和滚动条样式
import React, { type ComponentProps } from 'react';
import { cn } from '@/lib/utils';

interface ScrollAreaProps extends ComponentProps<'div'> {
  orientation?: 'vertical' | 'horizontal' | 'both';
  maxHeight?: string; // 支持最大高度限制
}

export const ScrollArea: React.FC<ScrollAreaProps> = ({
  orientation = 'vertical',
  maxHeight,
  className,
  children,
  ...props
}) => {
  const overflowClasses = {
    vertical: 'overflow-y-auto overflow-x-hidden',
    horizontal: 'overflow-x-auto overflow-y-hidden',
    both: 'overflow-auto'
  } as const;

  return (
    <div
      className={cn(
        overflowClasses[orientation],
        className
      )}
      style={{
        maxHeight: maxHeight,
        ...props.style
      }}
      {...props}
    >
      {children}
    </div>
  );
};
