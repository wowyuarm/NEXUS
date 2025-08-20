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

import React from 'react';
import { motion } from 'framer-motion';
import { MarkdownRenderer } from '@/components/ui/MarkdownRenderer';
import { Timestamp } from '@/components/ui/Timestamp';
import { RoleSymbol } from '@/components/ui/RoleSymbol';
import { ToolCallCard } from './ToolCallCard';
import { useTypewriter } from '../hooks/useTypewriter';
import type { Message } from '../types';
import type { RunStatus } from '../store/auraStore';

// How many characters before a tool insertion boundary we allow early reveal
const EARLY_REVEAL_CHARS = 6 as const;

interface ChatMessageProps {
  message: Message;
  isLastMessage: boolean;
  currentRunStatus: RunStatus;
  suppressAutoScroll?: (durationMs?: number) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isLastMessage,
  currentRunStatus,
  suppressAutoScroll
}) => {
  // Determine if this is the active AI message that should show dynamic states
  const isActiveAIMessage = message.role === 'AI' && isLastMessage;

  // For active AI messages, determine what to render based on run status
  const shouldShowThinking = isActiveAIMessage && currentRunStatus === 'thinking';
  const shouldShowStreaming = isActiveAIMessage && currentRunStatus === 'streaming_text';

  // For historical messages or non-AI messages, use static rendering
  const shouldUseStaticRendering = !isActiveAIMessage;

  // Determine if we should use typewriter effect
  const isStreaming =
    shouldShowStreaming || message.isStreaming || (message.metadata?.isStreaming ?? false);

  // Use typewriter engine for streaming and to gracefully finish after stream ends
  const { displayedContent, isTyping } = useTypewriter({
    targetContent: message.content,
    isStreamingMessage: isStreaming && !shouldUseStaticRendering,
  });

  // Decide the content we should render right now
  const toolCalls = message.toolCalls || [];
  const minInsertIndex = toolCalls.reduce<number>((min, tc) => {
    const idx = typeof tc.insertIndex === 'number' ? tc.insertIndex : Number.POSITIVE_INFINITY;
    return Math.min(min, idx);
  }, Number.POSITIVE_INFINITY);

  // Prefer typewriter output while it is still running, even after stream flag turns off
  const isActivelyTyping = (isStreaming && !shouldUseStaticRendering) || isTyping;
  let contentForRender = isActivelyTyping ? displayedContent : message.content;
  // Fast-forward pre-text up to the earliest tool insertion boundary so the card can appear immediately after the explanation
  if (isActivelyTyping && Number.isFinite(minInsertIndex)) {
    const boundary = minInsertIndex as number;
    if (contentForRender.length < boundary) {
      contentForRender = message.content.slice(0, boundary);
    }
  }

  // Render tool calls interleaved by individual insertIndex
  const renderInterleaved = () => {
    const toolCalls = message.toolCalls || [];
    if (toolCalls.length === 0) return (
      <>{contentForRender && <MarkdownRenderer content={contentForRender} />}</>
    );

    // Sort tool calls by their insertIndex (default to end)
    const sorted = [...toolCalls].sort((a, b) => (a.insertIndex ?? Infinity) - (b.insertIndex ?? Infinity));

    const fragments: React.ReactNode[] = [];
    let cursor = 0;

    for (const tc of sorted) {
      const idx = Math.min(tc.insertIndex ?? contentForRender.length, contentForRender.length);
      const slice = contentForRender.slice(cursor, idx);
      if (slice.trim().length > 0) {
        fragments.push(<MarkdownRenderer key={`txt-${cursor}-${idx}`} content={slice} />);
      }

      // Show tool card as soon as we pass close to its insertion point
      // Allow slight early reveal (lead-in) so the card appears almost immediately after the explanation
      const okToShow = contentForRender.length + EARLY_REVEAL_CHARS >= idx;
      if (okToShow) {
        fragments.push(
          <ToolCallCard key={tc.id} toolCall={tc} suppressAutoScroll={suppressAutoScroll} />
        );
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

  // Render content based on current state
  const renderContent = () => {
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

  // Don't render anything during thinking state - ChatView handles the breathing animation
  if (shouldShowThinking) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="group relative py-6 flex items-start gap-4"
      data-message-id={message.id}
    >
      {/* Left: Role symbol */}
      <RoleSymbol
        role={message.role}
        isThinking={false} // Never show thinking animation here
      />

      {/* Right: Message content area */}
      <div className="flex-1 min-w-0 relative">
        {/* Timestamp - hover to show, top right */}
        <div className="absolute top-0 right-0">
          <Timestamp
            date={new Date(message.timestamp)}
            format="smart"
            showOnHover={true}
          />
        </div>

        {/* Message content - dynamic rendering based on state */}
        <div className="pr-16"> {/* Right margin for timestamp */}
          {renderContent()}
        </div>
      </div>
    </motion.div>
  );
};
