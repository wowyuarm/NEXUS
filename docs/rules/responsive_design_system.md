# Responsive Design System - AURA 响应式设计规范

> **Purpose**: This document defines the responsive design standards for AURA, ensuring optimal user experience across all device sizes while maintaining our core design principles of silence, comfort, intuition, and rhythm.

---

## Core Principles

1. **Mobile-First, Desktop-Preserved**  
   Default styles target mobile devices (<640px). Desktop styles are restored via responsive prefixes.

2. **Progressive Enhancement**  
   Smooth transitions from 320px (smallest phones) to 1920px+ (large desktops).

3. **Design Language Consistency**  
   Responsive modifications never compromise grayscale moderation, liquid glass materials, or cognitive rhythm.

---

## Responsive Breakpoints

AURA uses Tailwind CSS's default breakpoint system:

| Breakpoint | Min Width | Target Devices | Usage |
|------------|-----------|----------------|-------|
| **(default)** | < 640px | Mobile phones | Base styles |
| `sm:` | ≥ 640px | Small tablets (portrait) | Intermediate adjustments |
| `md:` | ≥ 768px | Tablets (landscape) / Small laptops | **Primary desktop transition** |
| `lg:` | ≥ 1024px | Desktops / Large laptops | Full desktop experience |
| `xl:` | ≥ 1280px | Large desktops | Reserved for future use |

**Design Decision**: We primarily use `md:` (768px) as the mobile-to-desktop transition point, matching common tablet landscape widths and ensuring a clean two-tier system (mobile default + desktop restore).

---

## Space System

### Padding Hierarchy

**Container Padding (Outer layers: Modal, ChatView)**
- Mobile (default): `px-3` (12px)
- Desktop (`md:`): `px-4` (16px)

**Panel Padding (Middle layers: Panel header/content/footer)**
- Mobile (default): `px-4 py-3` (16px/12px)
- Desktop (`md:`): `px-6 py-4` (24px/16px)

**Content Padding (Inner layers: IdentityPanel, ConfigPanel)**
- Mobile (default): `px-4 py-3` (16px/12px)
- Desktop (`md:`): `px-7 py-4` (28px/16px)

### Margin & Gap Hierarchy

**Message Spacing**
- Mobile (default): `gap-1` (4px), `ml-3` (12px)
- Desktop (`md:`): `gap-2` (8px), `ml-6` (24px)

**Vertical Spacing**
- Mobile (default): `py-4` (16px)
- Desktop (`md:`): `py-6` (24px)

**CommandPalette**
- Mobile (default): `gap-2` (8px)
- Desktop (`md:`): `gap-4` (16px)

---

## Component Sizing

### RoleSymbol

**Layout Strategy**: Vertical stacking (Symbol + Timestamp above, Content below)

**Mobile (default)**:
- Size: `w-8 h-8` (32x32px)
- Font: `text-[18px]`
- Larger than before since vertical layout eliminates horizontal space constraints

**Desktop (`md:`)**:
- Size: `w-10 h-10` (40x40px)
- Font: `text-[22px]`
- Prominent but proportional to larger desktop content

**Rationale**: Vertical layout allows larger, more readable symbols without sacrificing content width. Symbol is now 12.5-37.5% larger than body text (16px), providing clear visual hierarchy.

---

### Touch Targets (Interactive Elements)

Following iOS Human Interface Guidelines (44pt minimum) and Material Design (48dp minimum):

**Icon Buttons (`variant="icon"`)**

| Size | Mobile (default) | Desktop (`md:`) | Usage |
|------|------------------|-----------------|-------|
| `sm` | `w-10 h-10` (40px) | `w-8 h-8` (32px) | Close buttons, help icons |
| `md` | `w-11 h-11` (44px) | `w-10 h-10` (40px) | Primary actions |
| `lg` | `w-12 h-12` (48px) | `w-12 h-12` (48px) | Large actions (no change) |

**Text Buttons** (non-icon):
- Maintain existing padding (sufficient touch area inherently)
- No responsive adjustment needed

**Rationale**: Mobile touch targets meet accessibility standards (≥40px), while desktop allows compact UI (32px acceptable with mouse precision).

---

### Font System

**Mobile Guidelines**:
- Minimum font size: `text-sm` (14px) for body text
- Preferred: `text-base` (16px) to prevent browser auto-zoom
- Labels/hints: `text-xs` (12px) acceptable

**Desktop**:
- Original design preserved (including `text-xs` where appropriate)

**CommandPalette Descriptions**:
- Mobile: `text-xs` (12px) to conserve space
- Desktop: `text-sm` (14px) for comfortable reading

---

## Implementation Patterns

### Tailwind Responsive Classes

**Basic Pattern**:
```typescript
className={cn(
  // Mobile (default) - no prefix
  "px-3 gap-1 text-sm",
  // Desktop - md: prefix
  "md:px-6 md:gap-2 md:text-base"
)}
```

**Icon Button Pattern**:
```typescript
variant === 'icon' 
  ? cn(
      // Mobile: larger touch target
      'w-10 h-10 rounded-full',
      // Desktop: restore compact size
      'md:w-8 md:h-8'
    )
  : /* other variants */
```

**Multi-Property Pattern**:
```typescript
className={cn(
  "group relative flex items-baseline",
  // Mobile: compact spacing
  "py-4 gap-1",
  // Desktop: comfortable spacing
  "md:py-6 md:gap-2"
)}
```

---

## Space Recovery Calculations

### Phase 1: Core Message Layout (iPhone SE 320px width)

**Original**:
- RoleSymbol: 32px
- gap: 8px
- ml: 24px
- px (container): 16px × 2 = 32px
- **Content width**: 320 - 32 (padding) - 32 (symbol) - 8 (gap) - 24 (ml) = **224px (70%)**

**Optimized**:
- RoleSymbol: 24px (-8px)
- gap: 4px (-4px)
- ml: 12px (-12px)
- px (container): 12px × 2 = 24px (-8px)
- **Content width**: 320 - 24 (padding) - 24 (symbol) - 4 (gap) - 12 (ml) = **256px (80%)** ✅

**Total recovery**: 32px = **+10% content width**

### Phase 2: Modal + Panel (iPhone SE 375px width)

**Optimized**:
- Modal: `p-3` (12px × 2 = 24px, from 48px) **-24px**
- Panel: `px-4` (16px × 2 = 32px, from 48px) **-16px**
- **Content width**: 375 - 24 (Modal) - 32 (Panel) = **319px (85%)** ✅

**Total recovery**: 40px = **+11% content width**

### Phase 3: Inner Content Panels (iPhone SE 375px in Modal+Panel+Content)

**Optimized**:
- Modal: 24px
- Panel: 32px
- IdentityPanel/ConfigPanel: `px-4` (16px × 2 = 32px, from 56px) **-24px**
- **Content width**: 375 - 24 - 32 - 32 = **287px (76.5%)** ✅

**Total recovery**: 64px = **+17% content width** vs original

### Phase 4: Vertical Layout Transformation (iPhone SE 375px - Final)

**Strategy Change**: Shift from horizontal (Symbol left, Content right) to vertical (Symbol + Timestamp top, Content bottom full-width)

**Horizontal Layout (Phase 1-3)**:
- Container padding: 24px (12px × 2)
- Content width: 375 - 24 = **351px (93.6%)** ✅

**Space Allocation**:
- Row 1 (Symbol + Timestamp + Copy): 40px height
  - Symbol: 32×32px (mobile) / 40×40px (desktop)
  - Timestamp: inline, auto-width
  - Copy button: 40×40px (mobile touch target)
- Row 2 (Content): Full width, no horizontal constraints

**Benefits**:
- **Content width**: From 256px (80%) to 351px (93.6%)
- **Additional recovery**: +40px horizontal = **+13.6% content width**
- **Cumulative improvement**: From 224px (70%) to 351px (93.6%) = **+23.6% total**

**Trade-off**:
- Vertical space: +40px per message (acceptable, promotes readability)
- Timestamp: Always visible (improved UX, no hover required)
- Copy functionality: Integrated inline (enhanced discoverability)

---

## Testing Matrix

### Device Coverage

| Device | Resolution | Breakpoint | Key Validations |
|--------|-----------|------------|-----------------|
| iPhone SE | 375×667 | < 640px | Content width ≥ 93%, RoleSymbol 32px, vertical layout, touch targets ≥ 40px |
| iPhone 12/13 | 390×844 | < 640px | All interactions smooth, copy button visible on hover |
| iPhone 12 Pro Max | 428×926 | < 640px | Layout balanced, no excessive whitespace |
| iPad Mini | 768×1024 | ≥ 768px (`md:`) | Desktop layout active, identical to laptop |
| MacBook Air 13" | 1280×720 | ≥ 1024px (`lg:`) | Full desktop experience |
| Desktop | 1920×1080 | ≥ 1024px (`lg:`) | **Regression test: unchanged from before** |

### Manual Testing Workflow

**Chrome DevTools**:
1. Open DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M / Cmd+Shift+M)
3. Select each device from the matrix
4. Verify for each:
   - RoleSymbol size (Inspect element → Computed tab)
   - Content width percentage (measure with DevTools ruler)
   - Touch target dimensions (≥40px × 40px)
   - Modal/Panel layout (no excessive padding)
   - CommandPalette readability (text not overly wrapped)
   - Animation smoothness (≥30fps)

**Real Device Testing** (if available):
- iOS Safari: Check virtual keyboard behavior, safe area insets
- Android Chrome: Verify touch targets, font rendering

---

## Common Patterns by Component

### ChatMessage (Vertical Layout)
```typescript
<div className={cn(
  "group relative flex flex-col",  // Vertical stacking
  "py-4",                           // Mobile: compact vertical spacing
  "md:py-6"                         // Desktop: comfortable vertical spacing
)}>
  {/* Row 1: Symbol + Timestamp + Copy Button */}
  <div className="flex items-center justify-between w-full mb-2 -ml-2.5">
    <div className="flex items-center gap-2">
      <RoleSymbol />  {/* 32px mobile, 40px desktop */}
      <Timestamp 
        format="compact" 
        showOnHover={false}
        className={cn(
          "text-sm text-secondary-foreground",
          "opacity-0 group-hover:opacity-100",  // Desktop: show on hover
          mobileActive && "opacity-100",         // Mobile: show when tapped
          TAILWIND_TRANSITION
        )}
      />
    </div>
    
    {/* Copy button - hover reveal with smooth icon transition */}
    <button
      onClick={handleCopy}
      className={cn(
        "p-1.5 text-secondary-foreground/60 rounded",
        "opacity-0 group-hover:opacity-100",
        mobileActive && "opacity-100",
        TAILWIND_TRANSITION,
        "hover:text-secondary-foreground hover:bg-muted/50"
      )}
    >
      <div className="relative h-4 w-4">
        {/* Icon transition: Copy → Check with rotation + scale */}
        <Copy className={cn(
          "absolute", TAILWIND_TRANSITION,
          copied ? "opacity-0 scale-50 rotate-90" : "opacity-100 scale-100 rotate-0"
        )} />
        <Check className={cn(
          "absolute", TAILWIND_TRANSITION,
          copied ? "opacity-100 scale-100 rotate-0" : "opacity-0 scale-50 -rotate-90"
        )} />
      </div>
    </button>
  </div>

  {/* Row 2: Full-width content - tap to toggle mobile active state */}
  <div onClick={handleMobileToggle} className="cursor-pointer md:cursor-default">
    <motion.div className="w-full">
      {/* Content takes full width - no horizontal constraints */}
    </motion.div>
  </div>
</div>
```

**Key Implementation Details**:
- **Vertical Layout**: `flex-col` instead of `items-baseline` for vertical stacking
- **Alignment**: `-ml-2.5` (negative margin) aligns RoleSymbol left edge with content text
- **Hover/Touch Interaction**:
  - Desktop: `group-hover:opacity-100` reveals timestamp and copy button
  - Mobile: `mobileActive` state toggled by tapping content area
  - Smooth transitions via `TAILWIND_TRANSITION`
- **Copy Button Animation**:
  - Double icon pattern: `Copy` and `Check` absolutely positioned
  - Transition: rotation (90deg) + scale (0.5) + opacity
  - Matches code block copy button behavior
- **Content Width**: Row 2 uses full width (93.6% of viewport on mobile)
- **Timestamp Format**: `compact` - "10:23" (today), "昨天 10:23" (yesterday), "10-23 22:14" (older)

### Modal + Panel Combination
```typescript
{/* Modal */}
<div className={cn(
  "fixed inset-0 z-50 flex items-center justify-center pointer-events-none",
  "p-3",                   // Mobile: 12px outer margin
  "md:p-6"                 // Desktop: 24px outer margin
)}>
  {/* Panel */}
  <div className="max-w-2xl w-full ...">
    {/* Header */}
    <div className={cn(
      "border-b border-border flex items-center justify-between shrink-0",
      "px-4 py-3",         // Mobile: 16px/12px
      "md:px-6 md:py-4"    // Desktop: 24px/16px
    )}>
```

### CommandPalette
```typescript
<div className={cn(
  "flex items-baseline",
  "gap-2",                 // Mobile: 8px column gap
  "md:gap-4"               // Desktop: 16px column gap
)}>
  <div className={cn(
    "flex-shrink-0",
    "min-w-[6rem]",        // Mobile: 96px command name width
    "md:min-w-[8rem]"      // Desktop: 128px command name width
  )}>
    {/* Command name */}
  </div>
  <div className="flex-1 min-w-0">
    <span className={cn(
      "text-secondary-foreground",
      "text-xs",             // Mobile: 12px description
      "md:text-sm"           // Desktop: 14px description
    )}>
      {/* Description */}
    </span>
  </div>
</div>
```

---

## Integration with Design Principles

### Silence
Responsive changes maintain visual quietness:
- No jarring layout shifts between breakpoints
- Smooth, predictable size transitions
- Spacing reductions are proportional, not dramatic

### Comfort
Users never feel cramped or disoriented:
- Mobile content width ≥ 80% (industry best practice: 75-85%)
- Touch targets meet accessibility standards (≥40px)
- Text remains readable (≥14px body, ≥12px hints)

### Intuition
Behavior matches user expectations:
- Mobile: compact, touch-optimized, efficient use of space
- Desktop: comfortable, precise, familiar desktop patterns
- Transition at natural device boundary (tablet landscape)

### Rhythm
Animation timing unchanged across devices:
- FRAMER.reveal (350ms), FRAMER.scene (450ms) work universally
- No performance degradation on mobile (tested ≥30fps)
- Cognitive rhythm system applies equally to all screen sizes

---

## Maintenance Guidelines

### When Adding New Components
1. **Default to mobile-first**: Write base styles for mobile
2. **Add desktop overrides**: Use `md:` prefix to restore desktop behavior
3. **Test across matrix**: Verify on ≥3 devices (iPhone SE, iPad Mini, Desktop)
4. **Document patterns**: Update this file if introducing new responsive patterns

### When Modifying Existing Components
1. **Preserve desktop**: Ensure `md:` styles match pre-responsive behavior exactly
2. **Validate space recovery**: Measure mobile content width percentage
3. **Check touch targets**: Icon buttons must be ≥40px on mobile
4. **Regression test**: Desktop (1920×1080) must look identical to before

### Red Flags (Avoid These)
- ❌ **Uniform spacing**: Don't use same padding/margin for all breakpoints
- ❌ **Breakpoint proliferation**: Stick to `md:` for most cases; avoid `sm:`, `lg:`, `xl:` unless necessary
- ❌ **Inconsistent patterns**: Follow established patterns in this document
- ❌ **Font size < 12px**: Never go below `text-xs` (12px) on mobile

---

## Future Enhancements

### Planned (Not in Current Scope)
- **Virtual keyboard adaptation**: Adjust ChatInput position when keyboard appears
- **Landscape mobile optimization**: Special handling for mobile landscape mode
- **PWA-specific features**: Install prompt, standalone mode tweaks
- **Touch gestures**: Swipe navigation for mobile

### Under Consideration
- **Extreme small screens** (< 320px): Currently not targeted
- **Ultra-wide displays** (> 1920px): May benefit from max-width constraints
- **Accessibility modes**: High contrast, large text support

---

## Appendix: Migration Checklist

When applying responsive design to a new component:

- [ ] Import `cn` utility: `import { cn } from '@/lib/utils';`
- [ ] Identify space-consuming elements (padding, margin, gaps, sizes)
- [ ] Apply mobile-first base styles (no prefix)
- [ ] Add desktop overrides with `md:` prefix
- [ ] Test on iPhone SE (375px): content width ≥ 80%
- [ ] Test on iPad Mini (768px): matches desktop layout
- [ ] Test on Desktop (1920px): unchanged from before
- [ ] Verify touch targets ≥ 40px (icon buttons)
- [ ] Check font sizes ≥ 14px (body text)
- [ ] Run `pnpm tsc -b` (type check)
- [ ] Run `pnpm build` (build verification)

---

**Last Updated**: 2025-10-24  
**Status**: ✅ Active (Phase 1-3 implemented)  
**Owner**: AURA Frontend Team

---

*This document embodies AURA's commitment to universal accessibility and optimal user experience across all devices, while maintaining the core design philosophy of silence, comfort, intuition, and rhythm.*
