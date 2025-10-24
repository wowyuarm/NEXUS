/**
 * Input Component
 * 
 * Single-line text/number input field with consistent styling.
 * Designed for short, predictable input scenarios.
 * 
 * Usage Scenarios:
 * - Form fields (name, email, password)
 * - Search boxes
 * - Number inputs (max_tokens, port numbers)
 * - Short text configuration (API keys, URLs)
 * 
 * When NOT to use:
 * - Multi-line text → Use Textarea instead
 * - Chat/comment input → Use AutoResizeTextarea instead
 * - Long text with variable length → Use Textarea or AutoResizeTextarea
 * 
 * Design:
 * - Fixed height (h-10)
 * - Grayscale styling with subtle hover/focus states
 * - Supports all native HTML input attributes
 * - Fully accessible with forwardRef support
 */

import { forwardRef } from 'react';
import type { InputHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Additional CSS classes */
  className?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-10 w-full rounded-lg border border-border bg-background/50 px-3 py-2 text-sm',
          'placeholder:text-muted-foreground/50',
          'focus:outline-none focus:ring-1 focus:ring-border focus:border-foreground/20',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'transition-colors duration-150',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';
