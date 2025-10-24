/**
 * AutoResizeTextarea Component - Dynamic Height Text Input
 * 
 * Self-adjusting multi-line text input that grows/shrinks with content.
 * Designed for dynamic content scenarios where length is unpredictable.
 * 
 * Usage Scenarios:
 * - Chat message input (primary use case)
 * - Comment/reply boxes that expand as user types
 * - Feedback forms with variable content length
 * - Any input where height should adapt to content
 * 
 * When NOT to use:
 * - Single-line input → Use Input instead
 * - Fixed-height multi-line → Use Textarea instead
 * - Scenarios requiring precise layout control → Use Textarea instead
 * 
 * Features:
 * - Automatic height adjustment as content changes
 * - Configurable min/max height (via minRows and maxHeightMultiplier)
 * - Smooth transitions between height changes
 * - Imperatively controllable via ref (resetHeight, focus)
 * - Transparent styling (designed for embedded contexts)
 * 
 * Technical Details:
 * - Uses scrollHeight to calculate required height
 * - Switches to overflow scroll when exceeding max height
 * - Exposes resetHeight() method for post-submit cleanup
 * - Initial height is captured and used as baseline
 * 
 * Comparison with other components:
 * - vs Input: Multi-line with dynamic height
 * - vs Textarea: Height adapts to content instead of fixed rows
 * 
 * @example
 * ```tsx
 * const ref = useRef<AutoResizeTextareaRef>(null);
 * 
 * const handleSubmit = () => {
 *   // Reset height after sending message
 *   ref.current?.resetHeight();
 * };
 * 
 * <AutoResizeTextarea
 *   ref={ref}
 *   value={message}
 *   onChange={(e) => setMessage(e.target.value)}
 *   minRows={3}
 *   maxHeightMultiplier={2}
 *   placeholder="Type a message..."
 * />
 * ```
 */
import { useRef, useEffect, forwardRef, useImperativeHandle, useCallback, type ComponentProps } from 'react';
import { cn } from '@/lib/utils';

interface AutoResizeTextareaProps extends Omit<ComponentProps<'textarea'>, 'rows'> {
  /** Maximum height as a multiplier of initial height (default: 2) */
  maxHeightMultiplier?: number;
  /** Minimum number of visible rows (default: 3) */
  minRows?: number;
  /** Callback fired when height is reset */
  onReset?: () => void;
}

/**
 * Methods exposed to parent component via ref
 */
export interface AutoResizeTextareaRef {
  /** Reset height to initial (minimum) height */
  resetHeight: () => void;
  /** Programmatically focus the textarea */
  focus: () => void;
}

export const AutoResizeTextarea = forwardRef<AutoResizeTextareaRef, AutoResizeTextareaProps>(
  ({ maxHeightMultiplier = 2, minRows = 3, className, value, onChange, onReset, ...props }, ref) => {
    const internalRef = useRef<HTMLTextAreaElement>(null);
    const textareaRef = internalRef;
    const initialHeightRef = useRef<number>(0);

    // Reset height to initial state
    const resetHeight = useCallback(() => {
      const textarea = textareaRef.current;
      if (textarea && initialHeightRef.current > 0) {
        textarea.style.height = `${initialHeightRef.current}px`;
        textarea.style.overflowY = 'hidden';
        onReset?.();
      }
    }, [onReset, textareaRef]);

    // Expose methods to parent component
    useImperativeHandle(ref, () => ({
      resetHeight,
      focus: () => textareaRef.current?.focus(),
    }), [resetHeight, textareaRef]);

    // Capture initial height on mount
    useEffect(() => {
      const textarea = textareaRef.current;
      if (textarea && initialHeightRef.current === 0) {
        textarea.style.height = 'auto';
        const naturalHeight = textarea.scrollHeight;
        initialHeightRef.current = naturalHeight;
        textarea.style.height = `${naturalHeight}px`;
      }
    }, [textareaRef]);

    // Auto-adjust height based on content
    useEffect(() => {
      const textarea = textareaRef.current;
      if (textarea && initialHeightRef.current > 0) {
        textarea.style.height = 'auto';
        const scrollHeight = textarea.scrollHeight;
        const maxHeight = initialHeightRef.current * maxHeightMultiplier;
        
        if (scrollHeight <= maxHeight) {
          textarea.style.height = `${Math.max(scrollHeight, initialHeightRef.current)}px`;
          textarea.style.overflowY = 'hidden';
        } else {
          textarea.style.height = `${maxHeight}px`;
          textarea.style.overflowY = 'auto';
        }
      }
    }, [value, maxHeightMultiplier, textareaRef]);

    return (
      <textarea
        ref={textareaRef}
        value={value}
        onChange={onChange}
        rows={minRows}
        className={cn(
          'w-full bg-transparent text-foreground placeholder:text-secondary-foreground',
          'text-base leading-relaxed resize-none border-none outline-none focus:ring-0',
          'py-3 min-h-[60px]', // Optimized padding and minimum height
          className
        )}
        {...props}
      />
    );
  }
);

AutoResizeTextarea.displayName = 'AutoResizeTextarea';
