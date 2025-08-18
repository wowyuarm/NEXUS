/**
 * ChatContainer Component - Business Logic and State Management
 *
 * This container component orchestrates the complete chat experience by:
 * - Managing chat state through the useAura hook
 * - Handling auto-scroll logic for message flow
 * - Coordinating user interaction events
 * - Passing data and callbacks to presentation components
 *
 * Architecture:
 * - Separation of concerns: logic vs presentation
 * - Single responsibility: state management and event handling
 * - Data flow: passes data and callbacks down via props
 * - Integration with AURA state management system
 */

import { useCallback } from 'react';
import { useAura } from './hooks/useAura';
import { useAutoScroll } from '@/hooks/useAutoScroll';
import { ChatView } from './components/ChatView';

export const ChatContainer = () => {
  // Complete AURA state management
  const {
    messages,
    currentRun,
    toolCallHistory,
    sendMessage
  } = useAura();

  // Auto-scroll functionality - depends on messages and current run state
  const { scrollContainerRef, showScrollButton, scrollToBottom, suppressAutoScroll } = useAutoScroll(
    [messages, currentRun.status, toolCallHistory],
    { threshold: 100 }
  );

  // Message sending handler: send and smooth scroll to bottom
  const handleSendMessage = useCallback(
    (message: string) => {
      sendMessage(message);
      // Use setTimeout to ensure message is added to DOM before scrolling
      setTimeout(() => {
        scrollToBottom('smooth'); // Use smooth scrolling
      }, 50); // Give enough time for DOM update
    },
    [sendMessage, scrollToBottom]
  );

  // Scroll to bottom handler
  const handleScrollToBottom = useCallback(() => {
    scrollToBottom('smooth');
  }, [scrollToBottom]);

  return (
    <ChatView
      messages={messages}
      currentRunStatus={currentRun.status}
      currentRunId={currentRun.runId}
      toolCallHistory={toolCallHistory}
      onSendMessage={handleSendMessage}
      scrollContainerRef={scrollContainerRef}
      showScrollButton={showScrollButton}
      onScrollToBottom={handleScrollToBottom}
      suppressAutoScroll={suppressAutoScroll}
    />
  );
};
