// src/components/ui/Button.tsx
// 通用按钮组件 - 支持多种变体和尺寸
import React, { type ComponentProps } from 'react';
import { cn } from '@/lib/utils';

interface ButtonProps extends ComponentProps<'button'> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
  iconOnly?: boolean;
  loading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  icon,
  iconOnly = false,
  loading = false,
  className,
  children,
  disabled,
  ...props
}) => {
  const isDisabled = disabled || loading;

  // 基础样式
  const baseStyles = [
    'inline-flex items-center justify-center',
    'font-medium transition-all duration-300',
    'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
    'disabled:cursor-not-allowed'
  ];

  // 变体样式
  const variantStyles = {
    primary: [
      'bg-foreground text-background',
      'shadow-lg shadow-black/30',
      'hover:scale-105 hover:shadow-xl hover:shadow-black/40',
      'disabled:bg-muted disabled:text-muted-foreground/50 disabled:shadow-sm disabled:shadow-black/10 disabled:hover:scale-100'
    ],
    secondary: [
      'bg-secondary text-secondary-foreground',
      'shadow-md shadow-black/20',
      'hover:bg-secondary/80',
      'disabled:bg-muted disabled:text-muted-foreground/50'
    ],
    ghost: [
      'bg-transparent text-foreground',
      'hover:bg-white/[.02]',
      'disabled:text-muted-foreground/50'
    ],
    outline: [
      'bg-transparent text-foreground border border-border',
      'hover:bg-white/[.02] hover:border-foreground/30',
      'disabled:text-muted-foreground/50 disabled:border-border/50'
    ]
  };

  // 尺寸样式
  const sizeStyles = {
    sm: iconOnly ? 'p-1.5 rounded-lg' : 'px-2.5 py-1.5 text-sm rounded-lg',
    md: iconOnly ? 'p-2 rounded-xl' : 'px-3 py-2 text-base rounded-xl',
    lg: iconOnly ? 'p-3 rounded-xl' : 'px-5 py-3 text-lg rounded-xl'
  };

  return (
    <button
      className={cn(
        baseStyles,
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      disabled={isDisabled}
      {...props}
    >
      {loading && (
        <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {icon && !loading && (
        <span className={cn(iconOnly ? '' : 'mr-2')}>
          {icon}
        </span>
      )}
      {!iconOnly && children}
    </button>
  );
};
