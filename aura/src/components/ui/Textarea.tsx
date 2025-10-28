/**
 * Textarea Component - Multi-line Text Input
 * 
 * Fixed-height multi-line text input for predictable layouts.
 * Designed for scenarios where content length is known or constrained.
 * 
 * Usage Scenarios:
 * - Mnemonic phrase input (12/24 words, fixed 4 rows)
 * - Comment boxes with character limits
 * - Description fields in forms
 * - Bio/profile text (fixed visible area)
 * - Any multi-line input where height should NOT auto-expand
 * 
 * When NOT to use:
 * - Single-line input → Use Input instead
 * - Chat/dynamic input → Use AutoResizeTextarea instead
 * - Input that needs to grow with content → Use AutoResizeTextarea instead
 * 
 * Design Philosophy:
 * - Silent: No jarring focus rings or aggressive borders
 * - Comfortable: Smooth, predictable state transitions
 * - Intuitive: Familiar textarea behavior with refined aesthetics
 * - Predictable: Fixed height prevents layout shifts
 * 
 * Features:
 * - Two variants: 'default' (bordered) and 'transparent' (borderless)
 * - Configurable minimum rows (default: 3)
 * - Grayscale styling with subtle hover/focus states
 * - Follows AURA's Anti-Ring Doctrine (no visual focus rings)
 * 
 * @see .cursor/rules/frontend-design-principles.mdc
 */

import { forwardRef, type ComponentProps } from 'react';
import { cn } from '@/lib/utils';
import { TAILWIND } from '@/lib/motion';

export interface TextareaProps extends Omit<ComponentProps<'textarea'>, 'rows'> {
  /**
   * Visual variant of the textarea
   * - 'default': Standard textarea with background, border, and padding
   * - 'transparent': Borderless, transparent textarea (for ChatInput-like contexts)
   */
  variant?: 'default' | 'transparent';
  
  /**
   * Minimum number of visible rows
   * @default 3
   */
  minRows?: number;
  
  /**
   * Error state styling
   */
  error?: boolean;
}

/**
 * Base Textarea Component
 * 
 * Provides consistent styling and interaction patterns for all text input areas.
 * Use this instead of raw <textarea> elements to maintain design consistency.
 */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ variant = 'default', minRows = 3, error = false, className, ...props }, ref) => {
    const baseStyles = cn(
      // Base styles - common to all variants
      'w-full resize-none',
      'text-base leading-relaxed',
      'text-foreground placeholder:text-secondary-foreground',
      // Silent focus - no ring, no outline
      'outline-none focus:ring-0',
      // Unified timing - micro-feedback for interactive elements
      TAILWIND.micro,
    );

    const variantStyles = {
      default: cn(
        // Standard textarea appearance
        'px-3 py-2 rounded-lg',
        'bg-background border border-border',
        // Hover feedback - subtle border emphasis using theme-aware color
        'hover:border-border-hover',
        // Focus feedback - slightly more emphasis but still subtle
        'focus:border-foreground/30',
        // Error state
        error && 'border-foreground/40 focus:border-foreground/50',
      ),
      transparent: cn(
        // Transparent variant for embedded contexts (like ChatInput)
        'bg-transparent border-none',
        'px-0 py-3',
      ),
    };

    return (
      <textarea
        ref={ref}
        rows={minRows}
        className={cn(baseStyles, variantStyles[variant], className)}
        {...props}
      />
    );
  }
);

Textarea.displayName = 'Textarea';
