/**
 * ChatMessage Component - Intelligent AI State Presenter
 *
 * This component serves as a smart message renderer that dynamically displays
 * different content based on the current AI run status. It handles:
 * - Historical messages (static rendering with text and tool calls)
 * - Active AI thinking state (breathing animation)
 * - Tool execution state (tool call cards within message bubble)
 * - Text streaming state (typewriter effect)
 * - Composite content rendering (text + tool calls in single bubble)
 *
 * Architecture:
 * - Conditional rendering based on message role and run status
 * - Integration with ToolCallCard for tool visualization
 * - Unified rendering logic for both streaming and historical messages
 * - DRY principle applied with extracted helper functions
 */

import React, { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from '@/components/ui/MarkdownRenderer';
import { Timestamp } from '@/components/ui/Timestamp';
import { RoleSymbol } from '@/components/ui/RoleSymbol';
import { ToolCallCard } from './ToolCallCard';
import { useTypewriter } from '../hooks/useTypewriter';
import type { Message, SystemMessageContent } from '../types';
import type { RunStatus } from '../store/chatStore';
import { FRAMER, TAILWIND_TRANSITION } from '@/lib/motion';


interface ChatMessageProps {
  message: Message;
  isLastMessage: boolean;
  currentRunStatus: RunStatus;
  suppressAutoScroll?: (durationMs?: number) => void;
  // Render variant: 'normal' renders the full row (with RoleSymbol on the left),
  // 'contentOnly' renders only the right content area, intended for use within a parent row that provides the persistent RoleSymbol.
  variant?: 'normal' | 'contentOnly';
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isLastMessage,
  currentRunStatus,
  suppressAutoScroll,
  variant = 'normal',
}) => {
  // Determine if this is the active AI message that should show dynamic states
  const isActiveAIMessage = message.role === 'AI' && isLastMessage;

  // For active AI messages, determine what to render based on run status
  const shouldShowThinking = isActiveAIMessage && currentRunStatus === 'thinking';
  const shouldShowStreaming = isActiveAIMessage && currentRunStatus === 'streaming_text';

  // For historical messages or non-AI messages, use static rendering
  const shouldUseStaticRendering = !isActiveAIMessage;

  // Extract string content (SYSTEM messages will skip typewriter logic)
  const stringContent = typeof message.content === 'string' ? message.content : '';

  // Determine if we should use typewriter effect
  const isStreaming =
    shouldShowStreaming || message.isStreaming || (message.metadata?.isStreaming ?? false);

  // Use typewriter engine for streaming and to gracefully finish after stream ends
  const { displayedContent, isTyping } = useTypewriter({
    targetContent: stringContent,
    isStreamingMessage: isStreaming && !shouldUseStaticRendering,
  });

  // Copy button state (must be declared before any conditional returns)
  const [copied, setCopied] = useState(false);
  // Mobile active state (for touch devices)
  const [mobileActive, setMobileActive] = useState(false);

  // Decide the content we should render right now

  // Prefer typewriter output until it has fully caught up to message.content, to avoid sudden jump-to-full
  const shouldUseTypewriterOutput =
    !shouldUseStaticRendering && (
      isTyping ||
      (displayedContent.length > 0 && displayedContent.length < (stringContent?.length ?? 0)) ||
      isStreaming
    );
  const isActivelyTyping = shouldUseTypewriterOutput;
  const contentForRender = shouldUseTypewriterOutput ? displayedContent : stringContent;
  // Strict gating: do not fast-forward. Cards will only appear after text up to their insertIndex has streamed.

  // Render tool calls interleaved by individual insertIndex
  const lockedInsertIndexRef = useRef<Record<string, number>>({});

  const renderInterleaved = () => {
    const toolCalls = message.toolCalls || [];
    if (toolCalls.length === 0) return (
      <>{contentForRender && <MarkdownRenderer content={contentForRender} />}</>
    );

    // Sort tool calls by their insertIndex (default to end)
    // Lock stable insertIndex once first observed as finite, to prevent momentary end-placement when backend toggles state at completion
    for (const tc of toolCalls) {
      const cand = typeof tc.insertIndex === 'number' ? tc.insertIndex : undefined;
      if (typeof cand === 'number' && Number.isFinite(cand) && lockedInsertIndexRef.current[tc.id] === undefined) {
        lockedInsertIndexRef.current[tc.id] = cand;
      }
    }

    const getEffectiveInsertIndex = (tc: typeof toolCalls[number]) => {
      const locked = lockedInsertIndexRef.current[tc.id];
      if (typeof locked === 'number' && Number.isFinite(locked)) return locked;
      if (typeof tc.insertIndex === 'number' && Number.isFinite(tc.insertIndex)) return tc.insertIndex;
      return Infinity; // default to end if unknown
    };

    const sorted = [...toolCalls].sort((a, b) => getEffectiveInsertIndex(a) - getEffectiveInsertIndex(b));

    const fragments: React.ReactNode[] = [];
    let cursor = 0;

    for (const tc of sorted) {
      const effectiveIdx = getEffectiveInsertIndex(tc);
      const idx = Math.min(
        Number.isFinite(effectiveIdx) ? effectiveIdx : contentForRender.length,
        contentForRender.length
      );
      const slice = contentForRender.slice(cursor, idx);
      if (slice.trim().length > 0) {
        fragments.push(<MarkdownRenderer key={`txt-${cursor}-${idx}`} content={slice} />);
      }

      // Strict reveal: show tool card only after text has streamed past its insertion point.
      // Use the un-clamped effectiveIdx for gating. If index is unknown (Infinity), show only after typing finishes.
      const okToShow = Number.isFinite(effectiveIdx)
        ? contentForRender.length >= (effectiveIdx as number)
        : !isActivelyTyping;
      if (okToShow) {
        fragments.push(
          <ToolCallCard key={tc.id} toolCall={tc} suppressAutoScroll={suppressAutoScroll} />
        );
        // If we revealed with a known finite index, lock it for stability
        if (Number.isFinite(effectiveIdx) && lockedInsertIndexRef.current[tc.id] === undefined) {
          lockedInsertIndexRef.current[tc.id] = effectiveIdx as number;
        }
      }
      cursor = idx;
    }

    // Remaining text after last tool
    const tail = contentForRender.slice(cursor);
    if (tail.trim().length > 0) {
      fragments.push(<MarkdownRenderer key={`txt-tail-${cursor}`} content={tail} />);
    }

    return <div className="space-y-3">{fragments}</div>;
  };

  // Helper: Check if content is SystemMessageContent
  const isSystemContent = (content: string | SystemMessageContent): content is SystemMessageContent => {
    return typeof content === 'object' && 'command' in content;
  };

  // Helper: Format object result as key-value pairs with intelligent type formatting
  const formatObjectResult = (obj: Record<string, unknown>): string => {
    return Object.entries(obj)
      .map(([key, value]) => {
        // Smart formatting based on value type
        let formattedValue: string;
        if (Array.isArray(value)) {
          // Arrays: format as bullet list for primitives, otherwise summarize
          const isPrimitiveArray = value.every(v => ['string', 'number', 'boolean'].includes(typeof v));
          if (isPrimitiveArray) {
            formattedValue = value.map(v => `- ${typeof v === 'boolean' ? (v ? '✓' : '✗') : String(v)}`).join('\n');
          } else {
            const preview = JSON.stringify(value.slice(0, 2), null, 2);
            const more = value.length > 2 ? `\n... and ${value.length - 2} more` : '';
            formattedValue = '```json\n' + preview + '\n```' + more;
          }
        } else if (typeof value === 'boolean') {
          formattedValue = value ? '✓' : '✗';
        } else if (typeof value === 'number') {
          formattedValue = value.toString();
        } else if (typeof value === 'string') {
          formattedValue = value;
        } else if (value === null || value === undefined) {
          formattedValue = String(value);
        } else {
          formattedValue = '```json\n' + JSON.stringify(value, null, 2) + '\n```';
        }
        return `**${key}:** ${formattedValue}`;
      })
      .join('\n\n');
  };

  // Render SYSTEM message with structured command/result layout
  const renderSystemMessage = () => {
    if (!isSystemContent(message.content)) {
      // Fallback for old string-based SYSTEM messages
      return <MarkdownRenderer content={message.content as string} />;
    }

    const { command, result } = message.content;
    // Prefer explicit human-readable message from command result metadata when available
    const commandResult = message.metadata?.commandResult as { status?: string; message?: string; data?: Record<string, unknown> } | undefined;
    const messageText = typeof commandResult?.message === 'string' ? commandResult?.message : undefined;

    // Deduplication: if result is a string and equals messageText, don't show result
    // This prevents showing "pong\npong" for commands that return { message: "pong" }
    const isDuplicateResult = typeof result === 'string' && result === messageText;
    const shouldShowResult = result && !isDuplicateResult;

    const hasDetails = Boolean(messageText) || Boolean(shouldShowResult);

    return (
      <div className="space-y-3">
        {/* Command line - always shown */}
        <div className="font-mono text-sm text-foreground" data-testid="system-command">
          {command}
        </div>

        {/* Divider - show when there is any detail (message or result) */}
        {hasDetails && (
          <hr className="border-border my-3" data-testid="system-divider" />
        )}

        {/* Human-readable message from backend, if provided (below divider) */}
        {messageText && (
          <div className="text-sm" data-testid="system-message">
            <MarkdownRenderer content={messageText} />
          </div>
        )}

        {/* Result area - only when result exists and is not a duplicate of messageText */}
        {shouldShowResult && (
          <div className="text-sm" data-testid="system-result">
            {typeof result === 'string' ? (
              <MarkdownRenderer content={result} />
            ) : (
              <MarkdownRenderer content={formatObjectResult(result as Record<string, unknown>)} />
            )}
          </div>
        )}
      </div>
    );
  };

  // Render content based on current state
  const renderContent = () => {
    // SYSTEM role: use special structured rendering
    if (message.role === 'SYSTEM') {
      return renderSystemMessage();
    }

    // Active AI message states
    if (isActiveAIMessage) {
      // Thinking state: this should not render any message bubble
      // The thinking animation is handled by ChatView as an independent element
      if (shouldShowThinking) {
        return null; // This message should not be rendered at all during thinking
      }

      // Streaming/hybrid rendering: split text by tool insertion index
      return renderInterleaved();
    }

    // Static rendering for historical messages: keep the tool card at the recorded insertion point
    // Static rendering uses the same interleaving logic (all text is known)
    return renderInterleaved();
  };

  // In 'normal' variant, we hide the entire row during thinking.
  // In 'contentOnly' variant, the parent row manages thinking display, so we allow rendering (but content will be empty via renderContent())
  if (shouldShowThinking && variant === 'normal') {
    return null;
  }

  const handleCopy = async () => {
    try {
      // Extract text content - handle both string and SystemMessageContent types
      const textContent = typeof message.content === 'string' 
        ? message.content 
        : (message.content as SystemMessageContent).command || '';
      
      await navigator.clipboard.writeText(textContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleMobileToggle = () => {
    setMobileActive(!mobileActive);
  };

  const ContentArea = (
    <motion.div
      className="w-full"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={FRAMER.reveal}
    >
      {/* Message content - full width */}
      {renderContent()}
    </motion.div>
  );

  if (variant === 'contentOnly') {
    return ContentArea;
  }

  return (
    <div
      className={cn(
        "group relative flex flex-col",
        // Vertical spacing: Mobile py-4, Desktop py-6
        "py-4",
        "md:py-6"
      )}
      data-message-id={message.id}
    >
      {/* Row 1: Role Symbol + Timestamp + Copy Button */}
      <div className="flex items-center justify-between w-full mb-2 -ml-2.5">
        <div className="flex items-center gap-2">
          <RoleSymbol
            role={message.role}
            isThinking={false}
            status={message.role === 'SYSTEM' ? message.metadata?.status : undefined}
          />
          <Timestamp
            date={new Date(message.timestamp)}
            format="compact"
            showOnHover={false}
            className={cn(
              "text-sm text-secondary-foreground",
              "opacity-0 group-hover:opacity-100",
              mobileActive && "opacity-100",
              TAILWIND_TRANSITION
            )}
          />
        </div>
        
        {/* Copy button - show on hover with icon transition */}
        <button
          onClick={handleCopy}
          className={cn(
            "p-1.5 text-secondary-foreground/60 rounded",
            "opacity-0 group-hover:opacity-100",
            mobileActive && "opacity-100",
            TAILWIND_TRANSITION,
            "hover:text-secondary-foreground hover:bg-muted/50",
            "outline-none focus:outline-none focus-visible:outline-none active:outline-none",
            "ring-0 focus:ring-0 focus-visible:ring-0 active:ring-0",
            "appearance-none"
          )}
          aria-label={copied ? "Copied" : "Copy message"}
        >
          <div className="relative h-4 w-4">
            <Copy
              size={16}
              className={cn(
                "absolute",
                TAILWIND_TRANSITION,
                copied
                  ? "opacity-0 scale-50 rotate-90"
                  : "opacity-100 scale-100 rotate-0"
              )}
            />
            <Check
              size={16}
              className={cn(
                "absolute",
                TAILWIND_TRANSITION,
                copied
                  ? "opacity-100 scale-100 rotate-0"
                  : "opacity-0 scale-50 -rotate-90"
              )}
            />
          </div>
        </button>
      </div>

      {/* Row 2: Full-width content - click to toggle mobile active state */}
      <div onClick={handleMobileToggle} className="cursor-pointer md:cursor-default">
        {ContentArea}
      </div>
    </div>
  );
};
