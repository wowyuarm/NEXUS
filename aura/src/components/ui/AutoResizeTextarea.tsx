// src/components/ui/AutoResizeTextarea.tsx
// 自动调整高度的文本输入框 - 纯UI组件
import { useRef, useEffect, forwardRef, useImperativeHandle, type ComponentProps } from 'react';
import { cn } from '@/lib/utils';

interface AutoResizeTextareaProps extends Omit<ComponentProps<'textarea'>, 'rows'> {
  maxHeightMultiplier?: number; // 最大高度倍数，默认为2
  minRows?: number; // 最小行数，默认为3
  onReset?: () => void; // 重置时的回调
}

// 暴露给父组件的方法
export interface AutoResizeTextareaRef {
  resetHeight: () => void;
  focus: () => void;
}

export const AutoResizeTextarea = forwardRef<AutoResizeTextareaRef, AutoResizeTextareaProps>(
  ({ maxHeightMultiplier = 2, minRows = 3, className, value, onChange, onReset, ...props }, ref) => {
    const internalRef = useRef<HTMLTextAreaElement>(null);
    const textareaRef = internalRef;
    const initialHeightRef = useRef<number>(0);

    // 重置高度到初始状态
    const resetHeight = () => {
      const textarea = textareaRef.current;
      if (textarea && initialHeightRef.current > 0) {
        textarea.style.height = `${initialHeightRef.current}px`;
        textarea.style.overflowY = 'hidden';
        onReset?.();
      }
    };

    // 暴露方法给父组件
    useImperativeHandle(ref, () => ({
      resetHeight,
      focus: () => textareaRef.current?.focus(),
    }), []);

    // 获取初始高度
    useEffect(() => {
      const textarea = textareaRef.current;
      if (textarea && initialHeightRef.current === 0) {
        textarea.style.height = 'auto';
        const naturalHeight = textarea.scrollHeight;
        initialHeightRef.current = naturalHeight;
        textarea.style.height = `${naturalHeight}px`;
      }
    }, []);

    // 自动调整高度
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
    }, [value, maxHeightMultiplier]);

    return (
      <textarea
        ref={textareaRef}
        value={value}
        onChange={onChange}
        rows={minRows}
        className={cn(
          'w-full bg-transparent text-foreground placeholder:text-secondary-foreground',
          'text-base leading-relaxed resize-none border-none outline-none focus:ring-0',
          'py-3 min-h-[60px]', // 优化的内边距和最小高度
          className
        )}
        {...props}
      />
    );
  }
);

AutoResizeTextarea.displayName = 'AutoResizeTextarea';
