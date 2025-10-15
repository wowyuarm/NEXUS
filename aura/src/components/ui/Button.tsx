// src/components/ui/Button.tsx
// Universal button component with unified 0.4s transitions
// 
// All state changes (hover, tap, disabled) use consistent 0.4s timing
// for a smooth, silent, and comfortable interaction experience
import React from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { cn } from '@/lib/utils';

// TODO: Future enhancements
// - Add `asChild` prop for polymorphic button (use as Link, etc.)
// - Add `variant="danger"` for destructive actions
// - Strengthen type safety: require aria-label when iconOnly is true

interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'children'> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline' | 'icon' | 'command';
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
  iconOnly?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
  children?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  icon,
  iconOnly = false,
  loading = false,
  fullWidth = false,
  className,
  children,
  disabled,
  ...props
}) => {
  const isDisabled = disabled || loading;

  // ============================================================================
  // Style System
  // ============================================================================
  
  // Base styles - Framer Motion handles all animations
  // command variant uses baseline alignment for two-column layout
  const baseStyles = [
    'inline-flex',
    variant === 'command' ? 'items-baseline justify-start' : 'items-center justify-center',
    'font-medium',
    // Remove any browser focus/active rings entirely
    'outline-none focus:outline-none focus-visible:outline-none active:outline-none',
    'ring-0 focus:ring-0 focus-visible:ring-0 active:ring-0',
    'appearance-none',
    'disabled:cursor-not-allowed',
    // Add CSS transition for background/border/shadow changes (0.4s unified)
    'transition-all duration-[400ms] ease-out',
    fullWidth && 'w-full'
  ];

  // Variant styles - all hover effects transition smoothly with 0.4s
  const variantStyles = {
    primary: [
      'bg-foreground text-background',
      'shadow-md shadow-black/20',
      'disabled:bg-muted disabled:text-muted-foreground/50 disabled:shadow-sm disabled:shadow-black/10'
    ],
    secondary: [
      'bg-secondary text-secondary-foreground',
      'shadow-sm shadow-black/15',
      'hover:bg-secondary/70',
      'disabled:bg-muted disabled:text-muted-foreground/50'
    ],
    ghost: [
      'bg-transparent text-foreground',
      'hover:bg-white/[.02]',
      'disabled:text-muted-foreground/50'
    ],
    outline: [
      'bg-transparent text-foreground border border-border',
      'hover:bg-white/[.02] hover:border-foreground/20',
      'disabled:text-muted-foreground/50 disabled:border-border/50'
    ],
    icon: [
      // Circular icon buttons (e.g., ScrollToBottomButton)
      'bg-card/75 backdrop-blur-xl',
      'border border-border',
      'shadow-md shadow-black/20',
      'text-secondary-foreground hover:text-foreground',
      'hover:bg-white/[.02]',
      'disabled:text-muted-foreground/50'
    ],
    command: [
      // Command palette items (CommandPalette)
      'bg-transparent text-foreground',
      'border-b border-border last:border-b-0',
      'hover:bg-accent/30',
      'disabled:text-muted-foreground/50',
      'text-left'
    ]
  };

  // Size styles
  // icon variant: always circular, always iconOnly
  // command variant: fixed padding, no border radius
  const sizeStyles = {
    sm: variant === 'icon' ? 'w-8 h-8 rounded-full' : 
        variant === 'command' ? 'px-4 py-2.5 text-sm' :
        (iconOnly ? 'p-1.5 rounded-lg' : 'px-2.5 py-1.5 text-sm rounded-lg'),
    md: variant === 'icon' ? 'w-10 h-10 rounded-full' : 
        variant === 'command' ? 'px-4 py-3 text-base' :
        (iconOnly ? 'p-2 rounded-xl' : 'px-3 py-2 text-base rounded-xl'),
    lg: variant === 'icon' ? 'w-12 h-12 rounded-full' : 
        variant === 'command' ? 'px-4 py-3.5 text-lg' :
        (iconOnly ? 'p-3 rounded-xl' : 'px-5 py-3 text-lg rounded-xl')
  };

  // ============================================================================
  // Animation System - Unified 0.4s transitions
  // ============================================================================

  // Hover animation - opacity only (avoid text shift), 0.4s unified
  const hoverAnimation = !isDisabled ? {
    opacity: 0.96,
    transition: {
      duration: 0.4,
      ease: 'easeOut' as const
    }
  } : {};

  // Tap animation - opacity only (avoid text shift), 0.4s unified
  const tapAnimation = !isDisabled ? {
    opacity: 0.9,
    transition: {
      duration: 0.4,
      ease: 'easeOut' as const
    }
  } : {};

  // ============================================================================
  // Content Rendering
  // ============================================================================

  // Loading Spinner component
  const LoadingSpinner = () => (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ duration: 0.4 }}
      className={cn(
        'h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent',
        !iconOnly && 'mr-2'
      )}
    />
  );

  // Icon rendering logic
  // iconOnly mode: spinner replaces icon to avoid layout shift
  // Normal mode: spinner on left, icon hidden
  const renderIcon = () => {
    if (loading) {
      // In iconOnly mode, spinner directly replaces icon
      if (iconOnly) {
        return <LoadingSpinner />;
      }
      // In normal mode, spinner on the left
      return <LoadingSpinner />;
    }

    if (icon) {
      return (
        <motion.span
          initial={{ opacity: 1 }}
          animate={{ opacity: loading ? 0 : 1 }}
          transition={{ duration: 0.4 }}
          className={cn(iconOnly ? '' : 'mr-2')}
        >
          {icon}
        </motion.span>
      );
    }

    return null;
  };

  // Text content rendering
  // Keep placeholder when loading to prevent width change
  const renderContent = () => {
    if (iconOnly) return null;
    
    return (
      <motion.span
        animate={{ opacity: loading ? 0.5 : 1 }}
        transition={{ duration: 0.4 }}
      >
        {children}
      </motion.span>
    );
  };

  return (
    <motion.button
      className={cn(
        baseStyles,
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      disabled={isDisabled}
      // State transition (enabled <-> disabled) with unified 0.4s timing
      animate={{ opacity: isDisabled ? 0.6 : 1 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      whileHover={hoverAnimation}
      whileTap={tapAnimation}
      {...props}
    >
      {/* command variant: render children directly without standard icon + text layout */}
      {variant === 'command' ? (
        children
      ) : (
        <>
          {renderIcon()}
          {renderContent()}
        </>
      )}
    </motion.button>
  );
};
