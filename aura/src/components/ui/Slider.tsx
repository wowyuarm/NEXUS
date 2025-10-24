/**
 * Slider Component
 * 
 * Range slider for numeric values with grayscale styling
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { cn } from '@/lib/utils';

export interface SliderProps {
  /** Current value (array for compatibility with shadcn API) */
  value: number[];
  /** Callback when value changes */
  onValueChange: (value: number[]) => void;
  /** Minimum value */
  min?: number;
  /** Maximum value */
  max?: number;
  /** Step increment */
  step?: number;
  /** Disabled state */
  disabled?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export const Slider: React.FC<SliderProps> = ({
  value,
  onValueChange,
  min = 0,
  max = 100,
  step = 1,
  disabled = false,
  className,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const sliderRef = useRef<HTMLDivElement>(null);

  const currentValue = value[0] ?? min;
  const percentage = ((currentValue - min) / (max - min)) * 100;

  const updateValue = useCallback((clientX: number) => {
    if (!sliderRef.current || disabled) return;

    const rect = sliderRef.current.getBoundingClientRect();
    const percentage = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    const rawValue = min + percentage * (max - min);
    const steppedValue = Math.round(rawValue / step) * step;
    const clampedValue = Math.max(min, Math.min(max, steppedValue));

    if (clampedValue !== currentValue) {
      onValueChange([clampedValue]);
    }
  }, [disabled, min, max, step, currentValue, onValueChange]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (disabled) return;
    setIsDragging(true);
    updateValue(e.clientX);
  };

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      updateValue(e.clientX);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, updateValue]);

  return (
    <div
      ref={sliderRef}
      className={cn('relative flex h-5 w-full touch-none items-center', className)}
      onMouseDown={handleMouseDown}
    >
      {/* Track Background */}
      <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-muted/30">
        {/* Track Fill */}
        <div
          className={cn(
            'absolute h-full bg-foreground/20 transition-all duration-100',
            isDragging && 'transition-none'
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Thumb */}
      <div
        className={cn(
          'absolute h-4 w-4 rounded-full border-2 border-foreground/30 bg-background',
          'shadow-sm transition-all duration-100',
          'hover:scale-110 hover:border-foreground/50',
          isDragging && 'scale-110 border-foreground/50 shadow-md transition-none',
          disabled && 'cursor-not-allowed opacity-50'
        )}
        style={{ left: `${percentage}%`, transform: 'translateX(-50%)' }}
      />
    </div>
  );
};
