// src/features/chat/components/ChatMessage.tsx
// 消息组件 - 集成流式渲染引擎，实现数据与渲染分离
import React from 'react';
import { motion } from 'framer-motion';
import { MarkdownRenderer } from '@/components/ui/MarkdownRenderer';
import { Timestamp } from '@/components/ui/Timestamp';
import { RoleSymbol } from '@/components/ui/RoleSymbol';
import { useTypewriter } from '../hooks/useTypewriter';
import type { Message } from '../types';

interface ChatMessageProps {
  message: Message;
  isLastMessage: boolean;
  isThinking: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, isLastMessage, isThinking }) => {
  const isXiThinking = message.role === 'AI' && isLastMessage && isThinking;
  const isStreaming = message.metadata?.isStreaming ?? false;

  // 使用流式渲染引擎
  const { displayedContent } = useTypewriter({
    targetContent: message.content,
    isStreamingMessage: isStreaming,
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="group relative py-6 flex items-start gap-4"
      data-message-id={message.id}
    >
      {/* 左侧：角色符号独立一列 */}
      <RoleSymbol role={message.role} isThinking={isXiThinking} />

      {/* 右侧：消息内容区域 */}
      <div className="flex-1 min-w-0 relative">
        {/* 时间戳 - 悬停显示，右上角 */}
        <div className="absolute top-0 right-0">
          <Timestamp
            date={new Date(message.timestamp)}
            format="smart"
            showOnHover={true}
          />
        </div>

        {/* 消息内容 - 使用流式渲染引擎输出 */}
        <div className="pr-16"> {/* 右边距为时间戳留出空间 */}
          <MarkdownRenderer content={displayedContent} />
        </div>
      </div>
    </motion.div>
  );
};
