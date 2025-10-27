/**
 * Motion System 2.0 - Cognitive Rhythm Architecture
 * 
 * This file defines the rhythmic animation system for AURA, built on cognitive psychology
 * principles rather than arbitrary timing constants.
 * 
 * Core Philosophy: Silent, Comfortable, Intuitive, **Rhythmic**
 * 
 * "Interface motion should mirror human thought—varied, organic, and alive."
 * 
 * Unlike mechanical systems that use uniform timing, this system matches animation tempo
 * to human cognitive processing speed through five distinct layers.
 * 
 * @see .cursor/rules/frontend-design-principles.mdc - Design Philosophy
 */

/**
 * The Five Cognitive Layers
 * 
 * Each layer corresponds to a different level of user attention and information processing:
 * 
 * 1. **Micro-Feedback** (100-200ms) - "Did my action register?"
 *    Instant acknowledgment for exploratory actions (hover, tap)
 * 
 * 2. **State Transition** (200-300ms) - "What changed?"
 *    Rapid changes that need to be perceived (loading, enable/disable)
 * 
 * 3. **Content Reveal** (300-450ms) - "What's new?"
 *    Comfortable expansion for understanding new content (cards, messages)
 * 
 * 4. **Scene Change** (400-600ms) - "Where am I now?"
 *    Full context shifts requiring psychological preparation (modals, pages)
 * 
 * 5. **Complex Choreography** (500-800ms) - "What's happening?"
 *    Multi-step sequences that tell a visual story
 */

/**
 * Layer 1: Micro-Feedback
 * Instant acknowledgment of user actions
 */
export const MOTION_MICRO = {
  /** Duration for entrance/hover (150ms) */
  duration: 0.15,
  /** Easing for quick response with smooth landing */
  ease: 'easeOut' as const,
} as const;

/**
 * Layer 2: State Transition
 * Rapid state changes that need to be perceived
 */
export const MOTION_TRANSITION = {
  /** Duration for state changes (250ms) */
  duration: 0.25,
  /** Easing for balanced, symmetrical feel */
  ease: 'easeInOut' as const,
} as const;

/**
 * Layer 3: Content Reveal
 * Comfortable expansion for new content
 */
export const MOTION_REVEAL = {
  /** Duration for content appearance (350ms) */
  duration: 0.35,
  /** Easing for smooth entrance without abruptness */
  ease: 'easeOut' as const,
} as const;

/**
 * Layer 4: Scene Change
 * Full context shifts with psychological preparation
 */
export const MOTION_SCENE = {
  /** Duration for major transitions (450ms) */
  duration: 0.45,
  /** Material Design's signature easing curve - graceful and deliberate */
  ease: [0.4, 0, 0.2, 1] as const,
} as const;

/**
 * Layer 5: Complex Choreography
 * Reserved for special multi-step animations
 * Duration varies by use case (500-800ms range)
 */
export const MOTION_COMPLEX = {
  /** Base duration for complex sequences */
  duration: 0.6,
  /** Easing varies by choreography needs */
  ease: 'easeInOut' as const,
} as const;

/**
 * The Asymmetric Exit Principle
 * 
 * Objects appearing (entering) and disappearing (exiting) follow different patterns:
 * - Entrances invite attention, require smooth acceleration
 * - Exits respond to completion, should be decisive and quick
 * 
 * Rule: Exit animations are 30-40% faster than entrances
 */
export const MOTION_EXIT = {
  /** Exit duration for micro-feedback (100ms) */
  micro: 0.1,
  /** Exit duration for state transitions (180ms) */
  transition: 0.18,
  /** Exit duration for content reveals (250ms) */
  reveal: 0.25,
  /** Exit duration for scene changes (280ms) */
  scene: 0.28,
  /** Easing for all exits - quick and decisive */
  ease: 'easeIn' as const,
} as const;

/**
 * Special Cases: Continuous Animations
 * These don't follow the cognitive layers as they serve different purposes
 */
export const MOTION_SPECIAL = {
  /** Loading spinners - continuous rotation */
  spin: {
    duration: 1,
    ease: 'linear' as const,
    repeat: Infinity,
  },
  /** Breathing animations - subtle, ambient effects */
  breathe: {
    duration: 2,
    ease: 'easeInOut' as const,
    repeat: Infinity,
  },
} as const;

/**
 * AI-Specific: Stream of Thought
 * 
 * AI interactions must feel organic, not mechanical
 */
export const MOTION_AI = {
  /** 
   * Typewriter effect configuration
   * Delays set to 0 for instant text rendering (no streaming delay)
   */
  typewriter: {
    /** Minimum delay between characters (ms) */
    minSpeed: 0,
    /** Maximum delay between characters (ms) */
    maxSpeed: 0,
    /** Average speed target */
    averageSpeed: 0,
    /** Startup delay before first character (ms) */
    startupDelay: { min: 0, max: 0 },
  },
} as const;

// ============================================================================
// Framer Motion Presets
// ============================================================================

/**
 * Pre-built Framer Motion transition configs
 * Use these directly with motion components
 */
export const FRAMER = {
  micro: {
    duration: MOTION_MICRO.duration,
    ease: MOTION_MICRO.ease,
  },
  transition: {
    duration: MOTION_TRANSITION.duration,
    ease: MOTION_TRANSITION.ease,
  },
  reveal: {
    duration: MOTION_REVEAL.duration,
    ease: MOTION_REVEAL.ease,
  },
  scene: {
    duration: MOTION_SCENE.duration,
    ease: MOTION_SCENE.ease,
  },
  complex: {
    duration: MOTION_COMPLEX.duration,
    ease: MOTION_COMPLEX.ease,
  },
  // Exit variants (faster, different easing)
  exit: {
    micro: {
      duration: MOTION_EXIT.micro,
      ease: MOTION_EXIT.ease,
    },
    transition: {
      duration: MOTION_EXIT.transition,
      ease: MOTION_EXIT.ease,
    },
    reveal: {
      duration: MOTION_EXIT.reveal,
      ease: MOTION_EXIT.ease,
    },
    scene: {
      duration: MOTION_EXIT.scene,
      ease: MOTION_EXIT.ease,
    },
  },
  // Special cases
  spin: MOTION_SPECIAL.spin,
  breathe: MOTION_SPECIAL.breathe,
} as const;

// ============================================================================
// Tailwind CSS Helpers
// ============================================================================

/**
 * Generate Tailwind transition class for a specific layer
 * Use for CSS-based transitions (hover, focus, etc.)
 */
export const getTailwindTransition = (layer: 'micro' | 'transition' | 'reveal' | 'scene') => {
  const durationMap = {
    micro: '150',
    transition: '250', 
    reveal: '350',
    scene: '450',
  };
  const easingMap = {
    micro: 'ease-out',
    transition: 'ease-in-out',
    reveal: 'ease-out',
    scene: 'ease-out', // Note: Tailwind doesn't support custom bezier directly
  };
  
  return `transition-all duration-${durationMap[layer]} ${easingMap[layer]}`;
};

/**
 * Pre-built Tailwind classes for common use cases
 */
export const TAILWIND = {
  /** Button hover, icon highlights (150ms, ease-out) */
  micro: getTailwindTransition('micro'),
  /** Loading states, icon rotations (250ms, ease-in-out) */
  transition: getTailwindTransition('transition'),
  /** Card expansions, message reveals (350ms, ease-out) */
  reveal: getTailwindTransition('reveal'),
  /** Modal backdrops, page transitions (450ms, ease-out) */
  scene: getTailwindTransition('scene'),
} as const;

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Get a variable typewriter speed with natural variation
 * Returns a delay in milliseconds between 10-25ms
 */
export const getTypewriterSpeed = (): number => {
  const { minSpeed, maxSpeed } = MOTION_AI.typewriter;
  // Simple randomization - could be enhanced with gaussian distribution
  return minSpeed + Math.random() * (maxSpeed - minSpeed);
};

/**
 * Get a random startup delay for typewriter effect
 * Returns a delay in milliseconds between 50-100ms
 */
export const getTypewriterStartupDelay = (): number => {
  const { min, max } = MOTION_AI.typewriter.startupDelay;
  return min + Math.random() * (max - min);
};

// ============================================================================
// Backwards Compatibility (Deprecated)
// ============================================================================

/**
 * @deprecated Use FRAMER.reveal instead
 * Legacy constant for migration period
 */
export const FRAMER_TRANSITION = FRAMER.reveal;

/**
 * @deprecated Use getTailwindTransition() or TAILWIND constants instead
 * Legacy constant for migration period
 */
export const TAILWIND_TRANSITION = TAILWIND.reveal;

/**
 * @deprecated Use specific MOTION_* constants instead
 * Legacy constant for migration period
 */
export const MOTION_CONFIG = {
  duration: MOTION_REVEAL.duration,
  ease: MOTION_REVEAL.ease,
} as const;

/**
 * @deprecated Use MOTION_SPECIAL instead
 * Legacy constant for migration period
 */
export const MOTION_EXCEPTIONS = MOTION_SPECIAL;
