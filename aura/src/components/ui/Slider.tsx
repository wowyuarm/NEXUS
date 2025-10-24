/**
 * Slider Component
 * 
 * Range slider for numeric values with grayscale styling.
 * Features smooth transitions during drag using Framer Motion spring physics.
 * 
 * Usage Scenarios:
 * - Temperature/top_p parameter adjustment (LLM configs)
 * - Volume/opacity controls
 * - Any numeric value with min/max range
 * 
 * Design:
 * - Grayscale styling
 * - Spring-based smooth transitions (not linear)
 * - Visual feedback during drag (border emphasis, shadow)
 * - Disabled state support
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

// ============================================================================
// Constants
// ============================================================================

const SPRING_TRANSITION = {
  type: 'spring' as const,
  stiffness: 300,
  damping: 30,
  mass: 0.5,
};

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
        {/* Track Fill - Smooth spring animation */}
        <motion.div
          className="absolute h-full bg-foreground/20"
          animate={{ width: `${percentage}%` }}
          transition={SPRING_TRANSITION}
        />
      </div>

      {/* Thumb - Smooth spring animation */}
      <motion.div
        className={cn(
          'absolute h-4 w-4 rounded-full border-2 border-foreground/30 bg-background',
          'shadow-sm',
          'hover:border-foreground/50 hover:opacity-96',
          isDragging && 'border-foreground/50 shadow-md',
          disabled && 'cursor-not-allowed opacity-50'
        )}
        animate={{ 
          left: `${percentage}%`,
        }}
        transition={SPRING_TRANSITION}
        style={{ transform: 'translateX(-50%)' }}
      />
    </div>
  );
};
