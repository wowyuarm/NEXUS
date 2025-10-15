# Motion and Animation System

## Design Philosophy

### The Unified Rhythm Principle

> "All state transitions should use a unified timing of 400ms to create a cohesive rhythm across the entire interface."

The motion system in AURA is not merely about adding visual polish—it's about creating a **perceptual language** that users unconsciously learn and trust. Just as music needs consistent tempo to feel coherent, our interface needs unified timing to feel comfortable.

**Core Beliefs**:

1. **Rhythm Over Flash**: Consistent 0.4-second transitions create a predictable "breathing pattern" for the interface
2. **Subtlety Over Spectacle**: Motion should acknowledge, not announce; guide, not demand attention
3. **Physics Over Mechanics**: Animations should feel like natural movement, not robotic state changes

### Why 0.4 Seconds?

This specific duration was chosen through careful consideration:

- **Not Too Fast** (< 200ms): Users can't perceive the transition, defeating its purpose
- **Not Too Slow** (> 600ms): Creates perceived lag, frustrating users
- **Just Right** (400ms): Long enough to register, short enough to feel responsive

**Perceptual Impact**:
```
100ms - Instant (feels like no animation)
200ms - Quick (might feel jarring)
400ms - Comfortable (predictable, trustworthy) ← Our choice
600ms - Slow (starts feeling like lag)
```

### The Silence, Comfort, Intuition Triad

Every animation decision traces back to our three core principles:

- **Silence**: Transitions should be felt, not noticed consciously
- **Comfort**: Timing should match users' natural expectations
- **Intuition**: Motion should reinforce mental models, not confuse them

---

## Architecture Overview

### The Motion Hierarchy

```
Design Philosophy (frontend-design-principles.mdc)
         ↓
Motion Configuration (lib/motion.ts) ← Single Source of Truth
         ↓
Component Implementation (Button.tsx, Modal.tsx, etc.)
         ↓
User Experience (Cohesive rhythm)
```

### Integration in AURA's Architecture

The motion system sits at the **intersection of design and state**:

- **State Layer**: Motion reacts to state changes (loading, hovering, etc.)
- **Component Layer**: Components consume motion configs consistently
- **Visual Layer**: Users perceive unified rhythm across all interactions

---

## Technical Deep Dive

### The Single Source of Truth: `lib/motion.ts`

**File Location**: `aura/src/lib/motion.ts`

This file is the **only** place where animation timing is defined:

```typescript
/**
 * Motion Configuration - The Single Source of Truth for Animations
 * 
 * This file defines the unified animation timing and easing for the entire AURA interface.
 * Following the design principle: "All state transitions should use a unified timing of 400ms
 * to create a cohesive rhythm across the entire interface."
 */

export const MOTION_CONFIG = {
  /** Unified duration for all state transitions (0.4 seconds) */
  duration: 0.4,
  /** Unified easing function for smooth, natural motion */
  ease: 'easeOut' as const,
} as const;

export const TAILWIND_TRANSITION = 'transition-all duration-400 ease-out';

export const FRAMER_TRANSITION = {
  duration: MOTION_CONFIG.duration,
  ease: MOTION_CONFIG.ease,
};

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
```

**Design Rationale**:
- **Type Safety**: TypeScript ensures correct usage across the codebase
- **Single Edit Point**: Change once, update everywhere
- **Explicit Exceptions**: Documented reasons for deviations (spin, breathe)
- **Import Chain**: Refactoring updates all consumers automatically

### Tailwind Configuration

**File Location**: `aura/tailwind.config.js`

To use `duration-400` token (required for `@apply` directives):

```javascript
export default {
  theme: {
    extend: {
      transitionDuration: {
        '400': '400ms',  // ← Enables duration-400 utility
      },
    },
  },
}
```

**Critical Note**: Arbitrary values like `duration-[400ms]` **cannot** be used in `@apply` directives. Always use configured tokens.

### Animation Categories

#### 1. CSS Transitions (Tailwind)

**Use Case**: Simple state changes (hover, focus, disabled)

```typescript
import { TAILWIND_TRANSITION } from '@/lib/motion';

<div className={cn(
  'bg-card border border-border',
  TAILWIND_TRANSITION,  // ← Unified timing
  'hover:border-foreground/20'
)} />
```

**Benefits**:
- Performant (GPU-accelerated)
- Declarative
- Works without JavaScript

#### 2. Framer Motion Transitions

**Use Case**: Complex state machines (mount/unmount, gestures)

```typescript
import { FRAMER_TRANSITION } from '@/lib/motion';

<motion.div
  initial={{ opacity: 0, scale: 0.95 }}
  animate={{ opacity: 1, scale: 1 }}
  exit={{ opacity: 0, scale: 0.95 }}
  transition={FRAMER_TRANSITION}  // ← Unified timing
/>
```

**Benefits**:
- Gesture support (whileHover, whileTap)
- AnimatePresence for mount/unmount
- Spring physics (when needed)

#### 3. Exception Cases (Documented)

**Use Case**: Continuous animations that break the 0.4s rule

```typescript
import { MOTION_EXCEPTIONS } from '@/lib/motion';

// Loading spinner - must rotate continuously
<motion.div
  animate={{ rotate: 360 }}
  transition={MOTION_EXCEPTIONS.spin}  // ← 1s linear, infinite
/>
```

**Rule**: Every exception must have a comment explaining why:
```typescript
// Loading spinner - continuous rotation needs linear easing
transition={MOTION_EXCEPTIONS.spin}
```

---

## Component Patterns

### Pattern 1: Button State Transitions

**Design Goal**: Acknowledge interaction without being loud

**Implementation** (`components/ui/Button.tsx`):

```typescript
const baseStyles = [
  'transition-all duration-400 ease-out',  // CSS transition
  // ... other styles
];

const hoverAnimation = !isDisabled ? {
  opacity: 0.96,  // Subtle 4% reduction
  transition: { duration: 0.4, ease: 'easeOut' }
} : {};

const tapAnimation = !isDisabled ? {
  opacity: 0.9,   // 10% reduction for "press" feel
  transition: { duration: 0.4, ease: 'easeOut' }
} : {};

<motion.button
  className={cn(baseStyles, variantStyles[variant])}
  whileHover={hoverAnimation}
  whileTap={tapAnimation}
  animate={{ opacity: isDisabled ? 0.6 : 1 }}  // Disabled state
  transition={{ duration: 0.4, ease: 'easeOut' }}
>
  {children}
</motion.button>
```

**Key Principles**:
- Opacity changes only (no scale on text containers)
- Hover: 4% opacity reduction (subtle acknowledgment)
- Tap: 10% opacity reduction (physical feedback)
- Disabled: 60% opacity (clear but not harsh)

### Pattern 2: Modal Enter/Exit

**Design Goal**: "Entering a focused space" feeling

**Implementation** (`components/common/Modal.tsx`):

```typescript
import { FRAMER_TRANSITION } from '@/lib/motion';

<AnimatePresence>
  {isOpen && (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={FRAMER_TRANSITION}
        className="fixed inset-0 bg-background/80 backdrop-blur-xl"
      />
      
      {/* Content */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={FRAMER_TRANSITION}
      >
        {children}
      </motion.div>
    </>
  )}
</AnimatePresence>
```

**Design Decisions**:
- `scale: 0.95` suggests forward movement (not jarring pop)
- Backdrop blur creates depth separation
- Both fade and scale use unified 0.4s timing

### Pattern 3: List Item Stagger

**Design Goal**: Sequential reveal without overwhelming

**Implementation** (`features/command/CommandPalette.tsx`):

```typescript
{filteredCommands.map((command, index) => (
  <motion.div
    key={command.name}
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ delay: index * 0.02, ...FRAMER_TRANSITION }}
  >
    <Button variant="command">{command.name}</Button>
  </motion.div>
))}
```

**Stagger Calculation**:
- Base delay: `index * 0.02` (20ms per item)
- Transition: Uses unified 0.4s
- Result: Smooth cascade without feeling slow

### Pattern 4: Loading State Transition

**Design Goal**: Inform without blocking, maintain layout

**Implementation** (`components/ui/Button.tsx`):

```typescript
// Icon-only mode: Spinner replaces icon (no layout shift)
{loading && iconOnly ? (
  <motion.div
    initial={{ opacity: 0, scale: 0.8 }}
    animate={{ opacity: 1, scale: 1 }}
    transition={{ duration: 0.4 }}
    className="w-4 h-4 animate-spin ..."
  />
) : icon}

// Normal mode: Spinner on left, text fades
{loading && !iconOnly && <LoadingSpinner />}
<motion.span
  animate={{ opacity: loading ? 0.5 : 1 }}
  transition={{ duration: 0.4 }}
>
  {children}
</motion.span>
```

**Layout Stability**:
- Spinner dimensions match icon (no shift)
- Text remains in DOM (maintains width)
- Opacity change only (no re-layout)

---

## Integration Points

### With State Management

Motion responds to Zustand state changes:

```typescript
// chatStore.ts
const runStatus = useStore(s => s.currentRun.status);

// Component
<motion.div
  animate={{ 
    opacity: runStatus === 'thinking' ? 0.6 : 1 
  }}
  transition={FRAMER_TRANSITION}
/>
```

### With Design System

Motion timing complements visual design:

- **Grayscale Palette**: No color-based animations, only opacity/transform
- **Liquid Glass**: Backdrop blur transitions at 0.4s
- **Shadows**: Shadow changes transition smoothly via CSS

### With Accessibility

Motion respects user preferences:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Note**: This is global reset, not in current implementation. Future enhancement.

---

## Best Practices

### DO: Import from lib/motion.ts

```typescript
// ✅ Correct
import { FRAMER_TRANSITION, TAILWIND_TRANSITION } from '@/lib/motion';

<motion.div transition={FRAMER_TRANSITION} />
<div className={TAILWIND_TRANSITION} />
```

```typescript
// ❌ Wrong - hardcoded timing
<motion.div transition={{ duration: 0.4 }} />
<div className="transition-all duration-[400ms]" />
```

### DO: Document Exceptions

```typescript
// ✅ Correct - explained exception
import { MOTION_EXCEPTIONS } from '@/lib/motion';

// Breathing animation - slower 2s cycle for ambient effect
<motion.div
  animate={{ opacity: [0.4, 1, 0.4] }}
  transition={MOTION_EXCEPTIONS.breathe}
/>
```

```typescript
// ❌ Wrong - unexplained deviation
<motion.div
  animate={{ opacity: [0.4, 1, 0.4] }}
  transition={{ duration: 2, repeat: Infinity }}
/>
```

### DO: Use Appropriate Tool

| Scenario | Tool | Reason |
|----------|------|--------|
| Hover state | Tailwind CSS | Simple, performant |
| Mount/unmount | Framer Motion | AnimatePresence support |
| Continuous rotation | Framer Motion | Infinite loop control |
| Focus ring (suppressed) | CSS | No animation needed |

### DON'T: Scale Text Containers

```typescript
// ❌ Wrong - causes text rendering shifts
<motion.button
  whileHover={{ scale: 1.05 }}  // Text becomes blurry!
>
  {children}
</motion.button>
```

```typescript
// ✅ Correct - opacity only
<motion.button
  whileHover={{ opacity: 0.96 }}
>
  {children}
</motion.button>
```

### DON'T: Mix Timing Values

```typescript
// ❌ Wrong - inconsistent rhythm
<div className="transition-all duration-200" />  // 200ms
<motion.div transition={{ duration: 0.3 }} />    // 300ms
```

```typescript
// ✅ Correct - unified rhythm
import { TAILWIND_TRANSITION, FRAMER_TRANSITION } from '@/lib/motion';

<div className={TAILWIND_TRANSITION} />          // 400ms
<motion.div transition={FRAMER_TRANSITION} />    // 400ms
```

---

## Troubleshooting

### Issue: Build Error with `duration-[400ms]`

**Error**:
```
The `duration-[400ms]` class does not exist. 
If `duration-[400ms]` is a custom class, make sure it is defined within a `@layer` directive.
```

**Cause**: Arbitrary values cannot be used in `@apply` directives (e.g., in `globals.css`)

**Solution**:
1. Add to `tailwind.config.js`:
   ```javascript
   transitionDuration: { '400': '400ms' }
   ```
2. Use `duration-400` instead of `duration-[400ms]`
3. Update `TAILWIND_TRANSITION` constant:
   ```typescript
   export const TAILWIND_TRANSITION = 'transition-all duration-400 ease-out';
   ```

### Issue: Animations Feel Jerky or Inconsistent

**Symptoms**: Some transitions feel faster/slower than others

**Diagnosis**:
```bash
# Search for hardcoded durations
grep -r "duration.*ms\|transition.*duration" aura/src --include="*.tsx" --include="*.ts"
```

**Solution**: Replace all hardcoded values with imports from `lib/motion.ts`

### Issue: Text Becomes Blurry on Hover

**Cause**: Scale transform on text container forces subpixel rendering

**Solution**: Use opacity instead of scale for text-containing elements

```typescript
// Before (blurry text)
whileHover={{ scale: 1.05 }}

// After (crisp text)
whileHover={{ opacity: 0.96 }}
```

### Issue: Button Test Fails with `toBeDisabled()`

**Error**:
```
Received element is not disabled: <span />
```

**Cause**: `getByText` finds inner `<span>`, not `<button>` element

**Solution**: Use `getByRole` for interactive elements

```typescript
// Before
const button = screen.getByText(/确认/i);
expect(button).toBeDisabled();  // Fails!

// After
const button = screen.getByRole('button', { name: /确认/i });
expect(button).toBeDisabled();  // Works!
```

---

## Performance Considerations

### GPU Acceleration

These properties trigger GPU acceleration (performant):
- `opacity`
- `transform` (translate, scale, rotate)

Avoid animating these (triggers reflow):
- `width`, `height`
- `padding`, `margin`
- `top`, `left` (use `transform: translate` instead)

### Animation Budget

**Rule of Thumb**: No more than 3-4 simultaneous animations on screen

**Current Implementation**:
- Modal enter: Backdrop (1) + Content (1) = 2 animations ✅
- Button hover: Single element opacity ✅
- List stagger: Sequential, not simultaneous ✅

### Will-Change Optimization

For frequently animated elements:

```css
.animated-element {
  will-change: opacity, transform;
}
```

**Warning**: Don't overuse—creates new layer, uses memory

---

## Testing Strategy

### Unit Testing Motion Config

```typescript
import { MOTION_CONFIG, FRAMER_TRANSITION } from '@/lib/motion';

describe('Motion System', () => {
  it('enforces 0.4s standard duration', () => {
    expect(MOTION_CONFIG.duration).toBe(0.4);
  });

  it('uses easeOut easing', () => {
    expect(MOTION_CONFIG.ease).toBe('easeOut');
  });

  it('provides Framer transition object', () => {
    expect(FRAMER_TRANSITION).toEqual({
      duration: 0.4,
      ease: 'easeOut',
    });
  });
});
```

### Component Animation Testing

```typescript
import { render } from '@testing-library/react';
import { Button } from '@/components/ui/Button';

it('applies correct transition timing', () => {
  const { container } = render(<Button>Click me</Button>);
  const button = container.querySelector('button');
  
  const styles = window.getComputedStyle(button);
  expect(styles.transitionDuration).toContain('400ms');
});
```

### Visual Regression Testing

For critical animations, use visual snapshots:

```typescript
it('matches modal enter animation snapshot', async () => {
  const { container } = render(<Modal isOpen={true}>Content</Modal>);
  
  // Wait for animation to complete
  await new Promise(resolve => setTimeout(resolve, 500));
  
  expect(container).toMatchSnapshot();
});
```

---

## Migration Guide

### From Hardcoded to Unified Timing

**Step 1**: Install motion constants
```typescript
// Add to component
import { FRAMER_TRANSITION, TAILWIND_TRANSITION } from '@/lib/motion';
```

**Step 2**: Replace Tailwind transitions
```typescript
// Before
className="transition-all duration-200"

// After
className={TAILWIND_TRANSITION}
```

**Step 3**: Replace Framer Motion transitions
```typescript
// Before
transition={{ duration: 0.3, ease: 'easeOut' }}

// After
transition={FRAMER_TRANSITION}
```

**Step 4**: Document exceptions
```typescript
// If timing MUST differ
// Continuous rotation - requires 1s linear loop
transition={{ duration: 1, ease: 'linear', repeat: Infinity }}
```

### Audit Checklist

- [ ] All `duration-*` classes use `duration-400`
- [ ] All Framer `transition` props import from `lib/motion.ts`
- [ ] No hardcoded `0.2`, `0.3`, `200ms`, `300ms` values
- [ ] Exceptions are documented with comments
- [ ] Tests verify timing consistency

---

## Update History

### 2025-10-15: Initial Documentation

**Context**: Comprehensive UI/UX audit revealed timing inconsistencies. Created unified motion system.

**Changes**:
- Created `lib/motion.ts` as single source of truth
- Migrated 10+ components to unified 0.4s timing
- Added Tailwind `duration-400` token
- Documented exceptions (spin, breathe)
- Established testing patterns

**Validation**: All components now use consistent rhythm, tests passing, build successful.

---

## References

### Internal Documentation
- Design Philosophy: `.cursor/rules/frontend-design-principles.mdc`
- AURA Architecture: `../03_AURA_ARCHITECTURE.md`
- Component Patterns: `./component_architecture.md` (coming soon)

### Code Locations
- Motion Config: `aura/src/lib/motion.ts`
- Button Component: `aura/src/components/ui/Button.tsx`
- Modal Component: `aura/src/components/common/Modal.tsx`
- Tailwind Config: `aura/tailwind.config.js`

### External Resources
- [Framer Motion Docs](https://www.framer.com/motion/)
- [Material Design Motion](https://m3.material.io/styles/motion/overview)
- [Designing Interface Animation](https://www.designbetter.co/animation-handbook)

---

*This document is a living reference. As our motion system evolves, this guide should be updated to reflect new patterns, edge cases, and best practices.*

