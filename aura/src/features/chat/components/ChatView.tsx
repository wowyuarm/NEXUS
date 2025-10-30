// src/features/chat/components/ChatView.tsx
// Chat view component - pure display component
//
// Responsibilities:
// - Render all visual elements of the chat interface
// - Handle animations and transition effects
// - Respond to user interactions (through callback functions)
// - Display UI elements such as message flow, input box, buttons, etc.
//
// Design principles:
// - Pure display component: does not contain business logic and state management
// - Receive all data and callback functions through props
// - Focus on UI rendering and user experience
// - Integrate LogStream message rendering logic

import React, { useMemo, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { Message } from '../types';
import type { RunStatus } from '../store/chatStore';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { ScrollToBottomButton } from './ScrollToBottomButton';
import { RoleSymbol } from '@/components/ui/RoleSymbol';
import { CommandPalette } from '@/features/command/components/CommandPalette';
import type { Command } from '@/features/command/command.types';
import { FRAMER } from '@/lib/motion';

interface ChatViewProps {
  messages: Message[];
  currentRunStatus: RunStatus;
  currentRunId: string | null;
  onSendMessage: (message: string) => void;
  scrollContainerRef: React.RefObject<HTMLDivElement | null>;
  showScrollButton: boolean;
  onScrollToBottom: () => void;
  suppressAutoScroll?: (durationMs?: number) => void;
  // Command props
  isPaletteOpen: boolean;
  query: string;
  availableCommands: Command[];
  selectedCommandIndex: number;
  onOpenPalette: () => void;
  onClosePalette: () => void;
  onSetQuery: (query: string) => void;
  onSetSelectedCommandIndex: (index: number) => void;
  onExecuteCommand: (command: string) => void;
}

export const ChatView: React.FC<ChatViewProps> = ({
  messages,
  currentRunStatus,
  currentRunId,
  onSendMessage,
  scrollContainerRef,
  showScrollButton,
  onScrollToBottom,
  suppressAutoScroll,
  // Command props
  isPaletteOpen,
  query,
  availableCommands,
  selectedCommandIndex,
  onOpenPalette,
  onClosePalette,
  onSetQuery,
  onSetSelectedCommandIndex,
  onExecuteCommand,
}) => {
  // Note: toolCallHistory prop is reserved for future tool history implementation
  // Computed values for cleaner render logic
  // Whether started (whether any message exists)
  const hasStarted = messages.length > 0;

  // Thinking indicator display control: only show when "current run exists and text stream hasn't started" and last message is user message (with slight delay)
  const lastMessage = messages[messages.length - 1];
  const isLastHuman = lastMessage?.role === 'HUMAN';
  const [showThinkingIndicator, setShowThinkingIndicator] = useState(false);

  // Whether there are AI streaming messages for current run (no longer show thinking indicator after typing starts)
  const hasStreamingAICurrentRun = useMemo(() => {
    if (!currentRunId) return false;
    return messages.some((m) => {
      const contentLength = typeof m.content === 'string' ? m.content.length : 0;
      return m.role === 'AI'
        && (m.isStreaming || ((m.metadata?.isStreaming ?? false)))
        && m.runId === currentRunId
        && (contentLength > 0);
    });
  }, [messages, currentRunId]);

  // Display condition: only when current status is thinking, streaming hasn't started, and last message is user message
  const shouldDisplayThinking = currentRunStatus === 'thinking' && Boolean(currentRunId) && isLastHuman && !hasStreamingAICurrentRun;

  // Thinking phase separate row: only show when shouldDisplayThinking and showThinkingIndicator are true (with slight delay)
  const showThinkingRow = shouldDisplayThinking && showThinkingIndicator;

  useEffect(() => {
    let t: number | undefined;
    if (shouldDisplayThinking) {
      // Slight delay to avoid appearing in same frame as user message
      t = window.setTimeout(() => setShowThinkingIndicator(true), 800);
    } else {
      setShowThinkingIndicator(false);
    }
    return () => {
      if (t) window.clearTimeout(t);
    };
  }, [shouldDisplayThinking]);

  // Input area animation: in single parent container, control from center -> bottom through transform
  // Complex choreography: complete scene switching from page center to bottom
  const inputMotion = useMemo(() => {
    return {
      initial: false as const, // Avoid flicker on first mount
      animate: hasStarted
        ? { y: 0, opacity: 1 }
        : { y: 'calc(-50vh + 4rem)', opacity: 1 },
      transition: FRAMER.complex,
    };
  }, [hasStarted]);

  // Title fade in/out - scene switching level transition
  const titleMotion = useMemo(() => {
    return {
      initial: { opacity: 0 },
      animate: { opacity: hasStarted ? 0 : 1 },
      transition: FRAMER.scene,
    };
  }, [hasStarted]);

  return (
    <div className="h-screen bg-background text-foreground font-sans relative overflow-hidden">
      {/* Unified layout: top content area + central/bottom animation input area */}
      <div className="h-full relative">
        {/* Scroll message area: control visibility and entrance based on hasStarted - scene switching */}
        <motion.div
          className="h-full overflow-y-auto pb-32"
          style={{ scrollBehavior: 'auto', scrollbarGutter: 'stable both-edges', overflowAnchor: 'auto' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: hasStarted ? 1 : 0 }}
          transition={FRAMER.scene}
          ref={scrollContainerRef}
        >
          <div className="flex justify-center">
            {/* Message stream rendering - integrated LogStream logic */}
            <div className={cn(
              "w-full max-w-3xl mx-auto",
              // Mobile: px-3 (reduced horizontal padding)
              "px-3",
              // Desktop: restore px-4
              "md:px-4"
            )}>
              {messages.map((message, index) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  isLastMessage={index === messages.length - 1}
                  currentRunStatus={currentRunStatus}
                  suppressAutoScroll={suppressAutoScroll}
                />
              ))}

              {/* Thinking phase: independent breathing symbol row, only displayed when AI text for current run has not yet appeared */}
              {showThinkingRow && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={FRAMER.reveal}
                  className="py-6 flex items-center w-full -ml-2.5"
                >
                  <RoleSymbol role="AI" isThinking={true} />
                  <div className="flex-1 min-w-0 ml-6" />
                </motion.div>
              )}

              {/* Tool cards are rendered internally by ChatMessage at the insertion position, avoiding duplication and order drift */}
            </div>
          </div>
        </motion.div>

        {/* Initial title: only displayed when not started, located above the center of the page */}
        <motion.div
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          {...titleMotion}
        >
          <h1 className="text-4xl font-light text-secondary-foreground tracking-[0.2em] -translate-y-32">
            NEXUS
          </h1>
        </motion.div>

        {/* Input area: single parent container, transition from center to bottom */}
        <motion.div
          className="absolute left-0 right-0 bottom-0 flex justify-center p-6"
          {...inputMotion}
        >
          <div className="w-full max-w-2xl relative">
            {/* Command palette - directly integrated above the input box */}
            <CommandPalette
              isOpen={isPaletteOpen}
              query={query}
              availableCommands={availableCommands}
              selectedIndex={selectedCommandIndex}
              onExecute={onExecuteCommand}
              onSelectIndex={onSetSelectedCommandIndex}
            />

            <ChatInput
              onSendMessage={onSendMessage}
              // Command props
              isPaletteOpen={isPaletteOpen}
              query={query}
              availableCommands={availableCommands}
              selectedCommandIndex={selectedCommandIndex}
              onOpenPalette={onOpenPalette}
              onClosePalette={onClosePalette}
              onSetQuery={onSetQuery}
              onSetSelectedCommandIndex={onSetSelectedCommandIndex}
              onExecuteCommand={onExecuteCommand}
            />
            <ScrollToBottomButton
              show={showScrollButton && hasStarted}
              onClick={onScrollToBottom}
              placement="above-input"
              className="md:hidden"
            />
          </div>
        </motion.div>

        {/* Scroll to bottom button */}
        <ScrollToBottomButton
          show={showScrollButton && hasStarted}
          onClick={onScrollToBottom}
          className="hidden md:block"
        />
      </div>
    </div>
  );
};
