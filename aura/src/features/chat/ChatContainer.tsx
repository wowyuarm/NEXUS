// src/features/chat/ChatContainer.tsx
// 聊天容器组件 - 负责业务逻辑和状态管理
// 
// 职责：
// - 管理聊天状态（消息、发送、思考状态）
// - 处理自动滚动逻辑
// - 协调用户交互事件
// - 将数据和回调函数传递给展示组件
//
// 设计原则：
// - 关注点分离：逻辑与展示分离
// - 单一职责：只负责状态管理和事件处理
// - 数据流向：通过props向下传递数据和回调

import { useCallback } from 'react';
import { useChat } from './hooks/useChat';
import { useAutoScroll } from '@/hooks/useAutoScroll';
import { ChatView } from './components/ChatView';

export const ChatContainer = () => {
  // 聊天状态管理
  const { messages, sendMessage, isThinking } = useChat();

  // 自动滚动功能
  const { scrollContainerRef, showScrollButton, scrollToBottom } = useAutoScroll(
    [messages, isThinking],
    { threshold: 100 }
  );

  // 发送消息处理：发送后平滑滚动到底部
  const handleSendMessage = useCallback(
    (message: string) => {
      sendMessage(message);
      // 使用 setTimeout 确保消息添加到DOM后再滚动
      setTimeout(() => {
        scrollToBottom('smooth'); // 使用平滑滚动
      }, 50); // 给足够的时间让DOM更新
    },
    [sendMessage, scrollToBottom]
  );

  // 滚动到底部处理
  const handleScrollToBottom = useCallback(() => {
    scrollToBottom('smooth');
  }, [scrollToBottom]);

  return (
    <ChatView
      messages={messages}
      isThinking={isThinking}
      onSendMessage={handleSendMessage}
      scrollContainerRef={scrollContainerRef}
      showScrollButton={showScrollButton}
      onScrollToBottom={handleScrollToBottom}
    />
  );
};
