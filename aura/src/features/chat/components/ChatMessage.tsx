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

interface ChatMessageProps {
  message: Message;
  isLastMessage: boolean;
  currentRunStatus: RunStatus;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isLastMessage,
  currentRunStatus
}) => {
  // Determine if this is the active AI message that should show dynamic states
  const isActiveAIMessage = message.role === 'AI' && isLastMessage;

  // For active AI messages, determine what to render based on run status
  const shouldShowThinking = isActiveAIMessage && currentRunStatus === 'thinking';
  const shouldShowStreaming = isActiveAIMessage && currentRunStatus === 'streaming_text';

  // For historical messages or non-AI messages, use static rendering
  const shouldUseStaticRendering = !isActiveAIMessage;

  // Determine if we should use typewriter effect
  const isStreaming = shouldShowStreaming || (message.metadata?.isStreaming ?? false);

  // Use typewriter engine only for streaming content
  const { displayedContent } = useTypewriter({
    targetContent: message.content,
    isStreamingMessage: isStreaming && !shouldUseStaticRendering,
  });

  // Helper function to render tool calls - extracted to avoid duplication
  const renderToolCalls = (toolCalls: typeof message.toolCalls) => {
    if (!toolCalls || toolCalls.length === 0) return null;

    return (
      <div className="space-y-2">
        {toolCalls.map((toolCall) => (
          <ToolCallCard key={toolCall.id} toolCall={toolCall} />
        ))}
      </div>
    );
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

      // For streaming states, render both text content and tool calls
      const hasContent = message.content && message.content.trim().length > 0;

      return (
        <div className="space-y-3">
          {/* Text content - show if there's any content */}
          {hasContent && (
            <MarkdownRenderer content={displayedContent} />
          )}

          {/* Tool calls - reuse helper function */}
          {renderToolCalls(message.toolCalls)}
        </div>
      );
    }

    // Default: static rendering for historical messages
    return (
      <div className="space-y-3">
        {/* Text content */}
        <MarkdownRenderer content={message.content} />

        {/* Tool calls - reuse helper function */}
        {renderToolCalls(message.toolCalls)}
      </div>
    );
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
