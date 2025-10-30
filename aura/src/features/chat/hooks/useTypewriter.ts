// src/features/chat/hooks/useTypewriter.ts
// Streaming rendering engine - autonomously manages typewriter effect, implementing AI thought flow
// 
// Stream of Thought: Text appears at an organic, human-like rhythm rather than mechanical printing
// - Micro-variation: delay for each character varies randomly between 10-25ms
// - Startup delay: 50-100ms "thinking startup" pause before first character
import { useState, useEffect, useRef } from 'react';
import { getTypewriterSpeed, getTypewriterStartupDelay } from '@/lib/motion';

interface UseTypewriterOptions {
  /** Target text, this value dynamically changes as new chunks flow in */
  targetContent: string;
  /** Whether it's a streaming message (used to determine if typewriter effect is needed) */
  isStreamingMessage: boolean;
  /** 
   * @deprecated No longer using fixed speed, now using micro-variation (10-25ms)
   * Keep this parameter only for backward compatibility
   */
  speed?: number;
}

interface UseTypewriterReturn {
  /** Currently displayed content */
  displayedContent: string;
  /** Whether typewriter is working */
  isTyping: boolean;
  /** Whether typewriter is finished */
  isFinished: boolean;
}

/**
 * useTypewriter Hook - AI thought flow rendering engine
 *
 * Core design philosophy:
 * 1. Autonomously manage typewriter state, not dependent on external enabled control
 * 2. Intelligently detect content changes, continuously render until completion
 * 3. Distinguish rendering strategies for "non-streaming messages" and "streaming messages"
 * 4. **Micro-variation**: Random delay for each character (10-25ms), simulating organic thinking rhythm
 * 5. **Startup delay**: Brief pause before first character (50-100ms), simulating "start thinking"
 *
 * Problems solved:
 * - Problem of streaming output being interrupted midway
 * - Problem of typewriter reset due to external state changes
 * - Problem of lacking typewriter completion status
 * - **Problem of mechanical uniform speed** - speed now varies organically
 */
export const useTypewriter = ({
  targetContent,
  isStreamingMessage,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  speed: _speed, // deprecated, ignored
}: UseTypewriterOptions): UseTypewriterReturn => {
  const [displayedContent, setDisplayedContent] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isFinished, setIsFinished] = useState(false);

  const currentIndexRef = useRef(0);
  const timeoutIdRef = useRef<number | undefined>(undefined); // Changed from interval to timeout
  const targetContentRef = useRef(targetContent);
  const lastTargetLengthRef = useRef(0);
  const hasStartedRef = useRef(false); // Track if we've applied startup delay

  // Update target content reference
  useEffect(() => {
    targetContentRef.current = targetContent;
  }, [targetContent]);

  // Core typewriter logic
  useEffect(() => {
    // Non-streaming message: only display directly when not started typing (historical message); if already started or has unfinished content, continue typing until completion
    if (!isStreamingMessage && currentIndexRef.current === 0) {
      setDisplayedContent(targetContent);
      setIsTyping(false);
      setIsFinished(true);
      currentIndexRef.current = targetContent.length;
      return;
    }

    // Streaming message: start typewriter effect
    if (!isTyping && targetContent.length > 0) {
      setIsTyping(true);
      setIsFinished(false);
    }

    // If no content, reset state
    if (targetContent.length === 0) {
      setDisplayedContent('');
      setIsTyping(false);
      setIsFinished(false);
      currentIndexRef.current = 0;
      lastTargetLengthRef.current = 0;
      return;
    }

    // Recursive typing function: use setTimeout to implement variable speed
    const typeNextChar = () => {
      const currentTarget = targetContentRef.current;

      if (currentIndexRef.current >= currentTarget.length) {
        // Already displayed all current content, waiting for more content or checking if completed
        // If target content length hasn't changed for a while, consider typing completed
        timeoutIdRef.current = window.setTimeout(() => {
          if (currentIndexRef.current >= targetContentRef.current.length) {
            setIsTyping(false);
            setIsFinished(true);
            timeoutIdRef.current = undefined;
          }
        }, 50); // Wait 50ms to check if there's new content
        return;
      }

      const nextChar = currentTarget[currentIndexRef.current];
      setDisplayedContent((prev) => prev + nextChar);
      currentIndexRef.current++;

      // Get variable speed delay for next character (10-25ms random)
      const nextDelay = getTypewriterSpeed();
      
      timeoutIdRef.current = window.setTimeout(typeNextChar, nextDelay);
    };

    // Start or continue typewriter: when streaming, or when finished but haven't caught up to target content
    if (!timeoutIdRef.current && (isStreamingMessage || currentIndexRef.current < targetContentRef.current.length)) {
      // If first time starting, apply startup delay (50-100ms)
      if (!hasStartedRef.current && currentIndexRef.current === 0) {
        hasStartedRef.current = true;
        const startupDelay = getTypewriterStartupDelay();
        timeoutIdRef.current = window.setTimeout(typeNextChar, startupDelay);
      } else {
        // Continue typing, no startup delay needed
        typeNextChar();
      }
    }

    return () => {
      if (timeoutIdRef.current) {
        window.clearTimeout(timeoutIdRef.current);
        timeoutIdRef.current = undefined;
      }
    };
  }, [targetContent, isStreamingMessage, isTyping]);

  // Clean up timer
  useEffect(() => {
    return () => {
      if (timeoutIdRef.current) {
        window.clearTimeout(timeoutIdRef.current);
      }
    };
  }, []);

  return {
    displayedContent,
    isTyping,
    isFinished
  };
};
