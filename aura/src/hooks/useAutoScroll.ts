// src/hooks/useAutoScroll.ts
// Universal auto-scroll management Hook - handles smart scrolling logic for scroll containers
import { useRef, useCallback, useState, useEffect } from 'react';

// Constant definitions
const SMOOTH_SCROLL_DURATION = 800; // Smooth scroll duration (milliseconds)
const SCROLL_THROTTLE_DELAY = 16; // Scroll throttle delay (approx. 60fps)
const HEIGHT_CHECK_INTERVAL = 50; // Height check interval (milliseconds)

interface UseAutoScrollOptions {
  /**
   * Threshold for determining if near bottom (pixels)
   * When distance from bottom is less than this value, user is considered at bottom
   */
  threshold?: number;
}

interface UseAutoScrollReturn {
  /** Ref for the scroll container */
  scrollContainerRef: React.RefObject<HTMLDivElement | null>;
  /** Whether to show scroll to bottom button */
  showScrollButton: boolean;
  /** Function to scroll to bottom */
  scrollToBottom: (behavior?: ScrollBehavior) => void;
  /** Temporarily suppress auto-scroll (for interactions that cause instantaneous height changes like expanding cards) */
  suppressAutoScroll: (durationMs?: number) => void;
}


/**
 * useAutoScroll Hook - Smart scroll behavior management
 *
 * Core logic:
 * 1. Introduce isAutoScrollingEnabled state to track whether auto-follow should be enabled
 * 2. Scenario A: When user sends message, immediately scroll to bottom
 * 3. Scenario B: When AI streams output and user is at bottom, auto-follow new content
 * 4. Scenario C: When AI streams output but user has scrolled up, do not auto-scroll
 * 5. Scenario D: When user returns to bottom from above, re-enable auto-follow
 *
 * @param dependencies Array of dependencies that triggers check when content updates
 * @param options Configuration options
 */
export const useAutoScroll = (
  dependencies: unknown[] = [], // Dependency array, triggers check when content updates
  options: UseAutoScrollOptions = {}
): UseAutoScrollReturn => {
  const { threshold = 50 } = options;

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);

  // Key state: use ref to avoid unnecessary re-renders
  const isAutoScrollingEnabled = useRef(true);
  const lastScrollHeight = useRef(0);
  const isSmoothScrolling = useRef(false); // Track if smooth scrolling is in progress
  const smoothScrollTimeout = useRef<NodeJS.Timeout | null>(null);
  const heightCheckInterval = useRef<NodeJS.Timeout | null>(null); // Height check timer
  const suppressUntil = useRef<number>(0); // Suppression end timestamp for auto-scroll (ms)

  const isSuppressed = () => Date.now() < suppressUntil.current;

  const suppressAutoScroll = useCallback((durationMs: number = 400) => {
    suppressUntil.current = Date.now() + durationMs;
    // Avoid any auto-scroll during suppression period
    isAutoScrollingEnabled.current = false;
  }, []);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'auto') => {
    const container = scrollContainerRef.current;
    if (!container) return;

    // If smooth scrolling, set flag and clear previous timeout
    if (behavior === 'smooth') {
      isSmoothScrolling.current = true;
      if (smoothScrollTimeout.current) {
        clearTimeout(smoothScrollTimeout.current);
      }
      // Set timeout to reset smooth scrolling flag
      smoothScrollTimeout.current = setTimeout(() => {
        isSmoothScrolling.current = false;
      }, SMOOTH_SCROLL_DURATION);
    }

    // Use requestAnimationFrame to ensure scrolling before next paint
    requestAnimationFrame(() => {
      container.scrollTo({ top: container.scrollHeight, behavior });
      // Update lastScrollHeight to avoid scroll interruption
      lastScrollHeight.current = container.scrollHeight;
    });

    // If user manually clicks scroll to bottom, re-enable auto-scroll
    if (behavior === 'smooth') {
      isAutoScrollingEnabled.current = true;
    }
  }, []);

  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    const isAtBottom = distanceFromBottom < threshold;

    // Update auto-scroll state and button display
    isAutoScrollingEnabled.current = isAtBottom;
    setShowScrollButton(!isAtBottom);

    // Update recorded scroll height
    lastScrollHeight.current = scrollHeight;
  }, [threshold]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    // When content updates (triggered by dependency items array)
    if (isAutoScrollingEnabled.current && !isSuppressed()) {
      // If smooth scrolling is in progress, skip this auto-scroll
      if (isSmoothScrolling.current) {
        return;
      }

      // Use throttling to avoid overly frequent scrolling
      setTimeout(() => {
        if (isAutoScrollingEnabled.current && !isSmoothScrolling.current && !isSuppressed()) {
          scrollToBottom('auto');
        }
      }, SCROLL_THROTTLE_DELAY);
    }

    // Show/hide button logic
    const { scrollTop, scrollHeight, clientHeight } = container;
    setShowScrollButton(scrollHeight - scrollTop - clientHeight > threshold);

  }, [dependencies, scrollToBottom, threshold]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  // Height change detection - used to capture content changes caused by typewriter effect
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    // Start height check timer
    heightCheckInterval.current = setInterval(() => {
      const currentHeight = container.scrollHeight;

      // If height increases and user is at bottom, auto-scroll
      if (currentHeight > lastScrollHeight.current && isAutoScrollingEnabled.current && !isSuppressed()) {
        // During non-smooth scrolling, immediately align to bottom; even for large jumps (e.g., inserting tool cards), don't delay
        if (!isSmoothScrolling.current) {
          requestAnimationFrame(() => scrollToBottom('auto'));
        }
        lastScrollHeight.current = currentHeight;
      }
    }, HEIGHT_CHECK_INTERVAL);

    return () => {
      if (heightCheckInterval.current) {
        clearInterval(heightCheckInterval.current);
        heightCheckInterval.current = null;
      }
    };
  }, [scrollToBottom]);

  // Clean up timeouts and timers
  useEffect(() => {
    return () => {
      if (smoothScrollTimeout.current) {
        clearTimeout(smoothScrollTimeout.current);
      }
      if (heightCheckInterval.current) {
        clearInterval(heightCheckInterval.current);
      }
    };
  }, []);

  return {
    scrollContainerRef,
    showScrollButton,
    scrollToBottom,
    suppressAutoScroll,
  };
};
