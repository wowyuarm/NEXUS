/**
 * Motion Configuration - The Single Source of Truth for Animations
 * 
 * This file defines the unified animation timing and easing for the entire AURA interface.
 * Following the design principle: "All state transitions should use a unified timing of 400ms
 * to create a cohesive rhythm across the entire interface."
 * 
 * @see .cursor/rules/frontend-design-principles.mdc
 */

/**
 * The golden rhythm for all state transitions
 */
export const MOTION_CONFIG = {
  /** Unified duration for all state transitions (0.4 seconds) */
  duration: 0.4,
  /** Unified easing function for smooth, natural motion */
  ease: 'easeOut' as const,
} as const;

/**
 * Pre-built Tailwind CSS transition class for consistent styling
 * Use this for CSS-based transitions on hover, focus, etc.
 */
export const TAILWIND_TRANSITION = 'transition-all duration-400 ease-out';

/**
 * Pre-built Framer Motion transition config
 * Use this for motion components that need standard transitions
 */
export const FRAMER_TRANSITION = {
  duration: MOTION_CONFIG.duration,
  ease: MOTION_CONFIG.ease,
};

/**
 * Exceptions to the 0.4s rule (must be documented)
 */
export const MOTION_EXCEPTIONS = {
  /** Loading spinners - continuous rotation needs linear easing */
  spin: {
    duration: 1,
    ease: 'linear' as const,
    repeat: Infinity,
  },
  /** Breathing animations - slower for subtle, ambient effects */
  breathe: {
    duration: 2,
    ease: 'easeInOut' as const,
    repeat: Infinity,
  },
} as const;

