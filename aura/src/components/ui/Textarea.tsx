/**
 * Textarea Component - Unified Text Input Foundation
 * 
 * A silent, comfortable textarea that follows AURA's design principles:
 * - No visual focus rings (Anti-Ring Doctrine)
 * - Subtle hover feedback (4% opacity change)
 * - Consistent 400ms timing
 * - Grayscale moderation
 * 
 * Design Philosophy:
 * - Silent: No jarring focus rings or aggressive borders
 * - Comfortable: Smooth, predictable state transitions
 * - Intuitive: Familiar textarea behavior with refined aesthetics
 * 
 * @see .cursor/rules/frontend-design-principles.mdc
 */

import { forwardRef, type ComponentProps } from 'react';
import { cn } from '@/lib/utils';
import { TAILWIND_TRANSITION } from '@/lib/motion';

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
      // Unified timing
      TAILWIND_TRANSITION,
    );

    const variantStyles = {
      default: cn(
        // Standard textarea appearance
        'px-3 py-2 rounded-lg',
        'bg-background border border-border',
        // Hover feedback - subtle border emphasis (4% opacity principle)
        'hover:border-foreground/20',
        // Focus feedback - slightly more emphasis but still subtle
        'focus:border-foreground/30',
        // Error state
        error && 'border-red-500/50 focus:border-red-500/70',
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

