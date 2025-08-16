// src/components/common/Container.tsx
// 通用容器组件，支持不同宽度和居中
import React, { type ComponentProps } from 'react';
import { cn } from '@/lib/utils';

interface ContainerProps extends ComponentProps<'div'> {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  centered?: boolean;
  material?: boolean; // 是否应用标准材质
}

export const Container: React.FC<ContainerProps> = ({
  size = 'md',
  centered = true,
  material = false,
  className,
  children,
  ...props
}) => {
  const sizeClasses = {
    sm: 'max-w-lg',    // 512px
    md: 'max-w-2xl',   // 672px - 我们的标准宽度
    lg: 'max-w-4xl',   // 896px
    xl: 'max-w-6xl'    // 1152px
  };

  return (
    <div
      className={cn(
        'w-full',
        sizeClasses[size],
        centered && 'mx-auto',
        material && [
          'bg-card/75 backdrop-blur-xl',
          'border border-border',
          'shadow-lg shadow-black/20',
          'rounded-2xl p-6'
        ],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};
