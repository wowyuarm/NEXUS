# Motion and Animation System 2.0

## Design Philosophy

### The Cognitive Rhythm Principle

> "Interface motion should mirror human thought—varied, organic, and alive."

The motion system in AURA is not merely about adding visual polish—it's about creating a **perceptual language** that users unconsciously learn and trust. Unlike mechanical systems that use uniform timing, this system matches animation tempo to human cognitive processing speed through five distinct layers.

**Core Philosophy: Silent, Comfortable, Intuitive, Rhythmic**

1. **Silent**: Transitions should be felt, not noticed consciously
2. **Comfortable**: Timing should match users' natural expectations  
3. **Intuitive**: Motion should reinforce mental models, not confuse them
4. **Rhythmic**: Varied timing creates organic, lifelike interaction patterns

### From Mechanical to Organic

**Previous System (0.4s Unified)**:
```
All animations → 400ms → Predictable but lifeless
```

**Current System (Cognitive Layers)**:
```
Micro-Feedback    → 150ms  → Instant acknowledgment
State Transition  → 250ms  → Rapid perception
Content Reveal    → 350ms  → Comfortable expansion
Scene Change      → 450ms  → Context preparation
Complex           → 600ms  → Visual storytelling
```

This creates a "breathing pattern" where interactions feel more like a conversation than a machine operation.

---

## The Five Cognitive Layers

Each layer corresponds to a different level of user attention and information processing:

### 1. Micro-Feedback (100-200ms)
**Question**: "Did my action register?"  
**Purpose**: Instant acknowledgment for exploratory actions

**Use Cases**:
- Button hover states
- Icon tap feedback
- Cursor state changes

**Example**:
```typescript
import { FRAMER } from '@/lib/motion';

<motion.button
  whileHover={{ opacity: 0.96 }}
  transition={FRAMER.micro}  // 150ms
>
```

### 2. State Transition (200-300ms)
**Question**: "What changed?"  
**Purpose**: Rapid changes that need to be perceived

**Use Cases**:
- Loading indicators appearing
- Button enable/disable
- Form validation states
- Status icon changes

**Example**:
```typescript
<motion.div
  animate={{ opacity: isLoading ? 0.6 : 1 }}
  transition={FRAMER.transition}  // 250ms
>
```

### 3. Content Reveal (300-450ms)
**Question**: "What's new?"  
**Purpose**: Comfortable expansion for understanding new content

**Use Cases**:
- Tool call cards appearing
- Chat messages streaming in
- Accordion/collapse expansion
- New content sections

**Example**:
```typescript
<motion.div
  initial={{ opacity: 0, y: 12 }}
  animate={{ opacity: 1, y: 0 }}
  transition={FRAMER.reveal}  // 350ms
>
```

### 4. Scene Change (400-600ms)
**Question**: "Where am I now?"  
**Purpose**: Full context shifts requiring psychological preparation

**Use Cases**:
- Modal dialogs opening
- Page transitions
- Major view switches
- Chat start animation

**Example**:
```typescript
<motion.div
  initial={{ opacity: 0, scale: 0.95 }}
  animate={{ opacity: 1, scale: 1 }}
  transition={FRAMER.scene}  // 450ms, Material Design curve
>
```

### 5. Complex Choreography (500-800ms)
**Question**: "What's happening?"  
**Purpose**: Multi-step sequences that tell a visual story

**Use Cases**:
- Multi-element entrance sequences
- Input field repositioning (center → bottom)
- Coordinated component transformations

**Example**:
```typescript
<motion.div
  animate={{ y: hasStarted ? 0 : 'calc(-50vh + 4rem)' }}
  transition={FRAMER.complex}  // 600ms
>
```

---

## The Asymmetric Exit Principle

> "Entrances invite attention; exits acknowledge completion."

**Philosophy**: Objects appearing (entering) and disappearing (exiting) follow different patterns:
- **Entrances**: Smooth, gradual, inviting (grace and elegance)
- **Exits**: Decisive, quick, responsive (efficiency and purpose)

**Rule**: Exit animations are **28-38% faster** than entrances

### Asymmetric Timing Table

| Layer | Entrance | Exit | Speed Reduction |
|-------|----------|------|-----------------|
| Micro | 150ms | 100ms | -33% |
| Transition | 250ms | 180ms | -28% |
| Reveal | 350ms | 250ms | -28% |
| Scene | 450ms | 280ms | -38% |

**Example**:
```typescript
import { FRAMER, MOTION_EXIT } from '@/lib/motion';

<AnimatePresence>
  {isOpen && (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={FRAMER.scene}  // 450ms enter
      exit={{ 
        opacity: 0,
        transition: { 
          duration: MOTION_EXIT.scene,  // 280ms exit
          ease: MOTION_EXIT.ease 
        }
      }}
    />
  )}
</AnimatePresence>
```

---

## AI-Specific Rhythms: The "Stream of Thought"

AI interactions require special timing to feel organic, not mechanical.

### Typewriter Effect with Micro-Variation

**Problem**: Uniform typing speed (15ms/char) feels robotic  
**Solution**: Variable speed (10-25ms/char) + startup delay (50-100ms)

**Implementation**:
```typescript
import { getTypewriterSpeed, getTypewriterStartupDelay } from '@/lib/motion';

// In useTypewriter hook
const startupDelay = getTypewriterStartupDelay();  // 50-100ms
const charDelay = getTypewriterSpeed();            // 10-25ms random
```

**Effect**: Creates "thinking, then speaking" feeling with natural pauses

### Tool Call Cards

Tool calls appear with "Content Reveal" timing (350ms) to signal a new event occurring.

```typescript
<ToolCallCard
  transition={FRAMER.reveal}  // 350ms, matches content rhythm
/>
```

---

## Architecture Overview

### The Motion Hierarchy

```
Design Philosophy (.cursor/rules/frontend-design-principles.mdc)
         ↓
Motion Configuration (lib/motion.ts) ← Single Source of Truth
         ↓
Component Implementation (Button.tsx, Modal.tsx, etc.)
         ↓
User Experience (Organic, rhythmic interaction)
```

### File Structure

**`aura/src/lib/motion.ts`** - The complete system:

```typescript
// Core layer definitions
export const MOTION_MICRO = { duration: 0.15, ease: 'easeOut' };
export const MOTION_TRANSITION = { duration: 0.25, ease: 'easeInOut' };
export const MOTION_REVEAL = { duration: 0.35, ease: 'easeOut' };
export const MOTION_SCENE = { duration: 0.45, ease: [0.4, 0, 0.2, 1] };
export const MOTION_COMPLEX = { duration: 0.6, ease: 'easeInOut' };

// Asymmetric exit timings
export const MOTION_EXIT = {
  micro: 0.1,
  transition: 0.18,
  reveal: 0.25,
  scene: 0.28,
  ease: 'easeIn',
};

// Pre-built Framer Motion configs
export const FRAMER = {
  micro: { duration: 0.15, ease: 'easeOut' },
  transition: { duration: 0.25, ease: 'easeInOut' },
  reveal: { duration: 0.35, ease: 'easeOut' },
  scene: { duration: 0.45, ease: [0.4, 0, 0.2, 1] },
  complex: { duration: 0.6, ease: 'easeInOut' },
  exit: {
    micro: { duration: 0.1, ease: 'easeIn' },
    transition: { duration: 0.18, ease: 'easeIn' },
    reveal: { duration: 0.25, ease: 'easeIn' },
    scene: { duration: 0.28, ease: 'easeIn' },
  },
  spin: { duration: 1, ease: 'linear', repeat: Infinity },
  breathe: { duration: 2, ease: 'easeInOut', repeat: Infinity },
};

// Pre-built Tailwind classes
export const TAILWIND = {
  micro: 'transition-all duration-150 ease-out',
  transition: 'transition-all duration-250 ease-in-out',
  reveal: 'transition-all duration-350 ease-out',
  scene: 'transition-all duration-450 ease-out',
};

// AI-specific helpers
export const getTypewriterSpeed = () => Math.floor(Math.random() * 16) + 10;  // 10-25ms
export const getTypewriterStartupDelay = () => Math.floor(Math.random() * 51) + 50;  // 50-100ms
```

**`aura/tailwind.config.js`** - Custom duration tokens:

```javascript
export default {
  theme: {
    extend: {
      transitionDuration: {
        '100': '100ms',
        '150': '150ms',
        '180': '180ms',
        '200': '200ms',
        '250': '250ms',
        '280': '280ms',
        '350': '350ms',
        '450': '450ms',
      },
    },
  },
}
```

---

## Component Patterns

### Pattern 1: Button Interactions (Micro-Feedback)

```typescript
import { FRAMER } from '@/lib/motion';

<motion.button
  className="transition-all duration-150 ease-out"  // CSS for base
  whileHover={{ opacity: 0.96 }}
  whileTap={{ opacity: 0.9 }}
  animate={{ opacity: isDisabled ? 0.6 : 1 }}
  transition={FRAMER.micro}  // 150ms for all states
>
```

**Key Principles**:
- Opacity changes only (no scale on text)
- Hover: 4% reduction (subtle)
- Tap: 10% reduction (clear feedback)
- Disabled: 40% reduction (clear state)

### Pattern 2: Modal Enter/Exit (Scene + Asymmetric)

```typescript
import { FRAMER, MOTION_EXIT } from '@/lib/motion';

<AnimatePresence>
  {isOpen && (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{
          ...FRAMER.scene,  // 450ms enter
          exit: { duration: MOTION_EXIT.scene, ease: MOTION_EXIT.ease }  // 280ms exit
        }}
      />
      
      {/* Content */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ 
          opacity: 0, 
          scale: 0.95,
          transition: { duration: MOTION_EXIT.scene, ease: MOTION_EXIT.ease }
        }}
        transition={FRAMER.scene}
      />
    </>
  )}
</AnimatePresence>
```

### Pattern 3: Tool Call Card (Content Reveal)

```typescript
import { FRAMER, MOTION_EXIT } from '@/lib/motion';

<motion.div
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  transition={FRAMER.reveal}  // 350ms entrance
>
  {/* Expandable content */}
  <AnimatePresence>
    {isExpanded && (
      <motion.div
        initial={{ height: 0, opacity: 0 }}
        animate={{ 
          height: 'auto', 
          opacity: 1,
          transition: { ...FRAMER.reveal, ease: 'easeOut' }  // 350ms expand
        }}
        exit={{ 
          height: 0, 
          opacity: 0,
          transition: { duration: MOTION_EXIT.reveal, ease: MOTION_EXIT.ease }  // 250ms collapse
        }}
      />
    )}
  </AnimatePresence>
</motion.div>
```

### Pattern 4: Chat View Initial Animation (Complex)

```typescript
import { FRAMER } from '@/lib/motion';

// Input field: center → bottom (complex choreography)
<motion.div
  initial={false}
  animate={hasStarted 
    ? { y: 0, opacity: 1 } 
    : { y: 'calc(-50vh + 4rem)', opacity: 1 }
  }
  transition={FRAMER.complex}  // 600ms for major layout shift
>

// Title fade (scene change)
<motion.h1
  initial={{ opacity: 0 }}
  animate={{ opacity: hasStarted ? 0 : 1 }}
  transition={FRAMER.scene}  // 450ms
>

// Thinking indicator (content reveal)
<motion.div
  initial={{ opacity: 0, y: 10 }}
  animate={{ opacity: 1, y: 0 }}
  transition={FRAMER.reveal}  // 350ms
>
```

---

## Best Practices

### DO: Use Layer-Appropriate Timing

```typescript
// ✅ Correct - matches cognitive layer
import { FRAMER } from '@/lib/motion';

<motion.button whileHover={{ opacity: 0.96 }} transition={FRAMER.micro} />  // Micro
<motion.div animate={{ opacity: isLoading ? 0.6 : 1 }} transition={FRAMER.transition} />  // State
<ToolCallCard transition={FRAMER.reveal} />  // Content
<Modal transition={FRAMER.scene} />  // Scene
```

```typescript
// ❌ Wrong - arbitrary timing
<motion.button whileHover={{ opacity: 0.96 }} transition={{ duration: 0.2 }} />
<ToolCallCard transition={{ duration: 0.5 }} />
```

### DO: Apply Asymmetric Exit

```typescript
// ✅ Correct - faster exit
<AnimatePresence>
  {show && (
    <motion.div
      animate={{ opacity: 1 }}
      transition={FRAMER.scene}  // 450ms enter
      exit={{ 
        opacity: 0,
        transition: { duration: MOTION_EXIT.scene, ease: MOTION_EXIT.ease }  // 280ms exit
      }}
    />
  )}
</AnimatePresence>
```

```typescript
// ❌ Wrong - symmetric timing
<motion.div
  animate={{ opacity: 1 }}
  exit={{ opacity: 0 }}
  transition={FRAMER.scene}  // Same timing for enter/exit
/>
```

### DON'T: Scale Text Containers

```typescript
// ❌ Wrong - causes text rendering artifacts
<motion.button whileHover={{ scale: 1.05 }}>
  {text}  // Text becomes blurry!
</motion.button>
```

```typescript
// ✅ Correct - opacity only
<motion.button whileHover={{ opacity: 0.96 }}>
  {text}  // Crisp text rendering
</motion.button>
```

### DON'T: Animate Layout-Triggering Properties

```typescript
// ❌ Avoid - causes reflow
animate={{ width: '300px', padding: '20px' }}
```

```typescript
// ✅ Better - GPU-accelerated
animate={{ opacity: 1, transform: 'translateX(0)' }}
```

---

## Performance Considerations

### GPU-Accelerated Properties

These properties are performant (use freely):
- `opacity`
- `transform` (translate, scale, rotate)

Avoid animating these (triggers reflow):
- `width`, `height`
- `padding`, `margin`
- `top`, `left` (use `transform: translate` instead)

### Animation Budget

**Rule of Thumb**: No more than 3-4 simultaneous animations

**Current Implementation**:
- Modal: Backdrop (1) + Content (1) = 2 ✅
- Button hover: Single element ✅
- Tool card expand: Single element ✅

### Will-Change Optimization

For frequently animated elements:

```css
.animated-element {
  will-change: opacity, transform;
}
```

**Warning**: Creates new layer, uses memory. Don't overuse.

---

## Testing Strategy

### Unit Testing Motion Config

```typescript
import { MOTION_MICRO, FRAMER } from '@/lib/motion';

describe('Motion System', () => {
  it('defines all cognitive layers', () => {
    expect(MOTION_MICRO.duration).toBe(0.15);
    expect(FRAMER.transition.duration).toBe(0.25);
    expect(FRAMER.reveal.duration).toBe(0.35);
    expect(FRAMER.scene.duration).toBe(0.45);
    expect(FRAMER.complex.duration).toBe(0.6);
  });

  it('enforces asymmetric exit principle', () => {
    expect(FRAMER.exit.scene.duration).toBeLessThan(FRAMER.scene.duration);
    // 280ms < 450ms (38% faster)
  });
});
```

### Component Animation Testing

```typescript
import { render } from '@testing-library/react';
import { Button } from '@/components/ui/Button';

it('applies correct transition timing', () => {
  const { container } = render(<Button>Click</Button>);
  const button = container.querySelector('button');
  
  const styles = window.getComputedStyle(button);
  expect(styles.transitionDuration).toContain('150ms');  // Micro-feedback
});
```

---

## Migration Guide

### From Old System (0.4s Unified)

**All deprecated constants have been removed from `lib/motion.ts`**. Use the cognitive rhythm layers:

```typescript
// Import the new system
import { FRAMER, TAILWIND, MOTION_EXIT } from '@/lib/motion';

// Framer Motion - use layer-specific timings
transition={FRAMER.micro}      // 150ms for hover
transition={FRAMER.transition} // 250ms for state changes  
transition={FRAMER.reveal}     // 350ms for content
transition={FRAMER.scene}      // 450ms for modals

// Tailwind CSS - use pre-built classes
className={TAILWIND.micro}     // hover/tap effects
className={TAILWIND.transition} // loading states
className={TAILWIND.reveal}    // content expansion

// Asymmetric exits
exit={{ 
  opacity: 0,
  transition: { duration: MOTION_EXIT.reveal, ease: MOTION_EXIT.ease }
}}
```

### Audit Checklist

- [ ] All hover/tap effects use `FRAMER.micro` (150ms)
- [ ] Loading states use `FRAMER.transition` (250ms)
- [ ] Content reveals use `FRAMER.reveal` (350ms)
- [ ] Modals use `FRAMER.scene` (450ms)
- [ ] Major layouts use `FRAMER.complex` (600ms)
- [ ] All exits use `MOTION_EXIT` timings
- [ ] No hardcoded duration values
- [ ] No text scaling animations

---

## Update History

### 2025-10-17: Cognitive Rhythm Revolution

**Context**: Complete overhaul from mechanical 0.4s unified timing to cognitive-based rhythm system.

**Changes**:
- Introduced Five Cognitive Layers (Micro → Complex)
- Implemented Asymmetric Exit Principle (30-38% faster exits)
- Added AI-specific "Stream of Thought" timing
- Migrated 10+ components to new system
- Updated Tailwind config with all duration tokens
- Added `FRAMER.complex` for major layout shifts

**Philosophy**: "Silent, Comfortable, Intuitive, **Rhythmic**"

**Validation**: All components migrated, tests passing, build successful.

### 2025-10-15: Initial Unified System

**Context**: Established 0.4s unified timing to replace inconsistent durations.

**Changes**:
- Created `lib/motion.ts` as single source of truth
- Unified 10+ components to 0.4s
- Added Tailwind `duration-400` token

---

## References

### Internal Documentation
- Design Philosophy: `.cursor/rules/frontend-design-principles.mdc`
- AURA Architecture: `../03_AURA_ARCHITECTURE.md`

### Code Locations
- Motion Config: `aura/src/lib/motion.ts`
- Button Component: `aura/src/components/ui/Button.tsx`
- Modal Component: `aura/src/components/common/Modal.tsx`
- Tool Card: `aura/src/features/chat/components/ToolCallCard.tsx`
- Chat View: `aura/src/features/chat/components/ChatView.tsx`
- Typewriter Hook: `aura/src/features/chat/hooks/useTypewriter.ts`
- Tailwind Config: `aura/tailwind.config.js`

### External Resources
- [Framer Motion Docs](https://www.framer.com/motion/)
- [Material Design Motion](https://m3.material.io/styles/motion/overview)
- [Laws of UX - Doherty Threshold](https://lawsofux.com/doherty-threshold/)

---

*This document reflects Motion System 2.0 - the cognitive rhythm architecture. As our understanding evolves, this guide will be updated with new patterns, refinements, and discoveries.*
