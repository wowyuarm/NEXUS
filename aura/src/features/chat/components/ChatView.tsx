// src/features/chat/components/ChatView.tsx
// 聊天视图组件 - 纯展示组件
//
// 职责：
// - 渲染聊天界面的所有视觉元素
// - 处理动画和过渡效果
// - 响应用户交互（通过回调函数）
// - 展示消息流、输入框、按钮等UI元素
//
// 设计原则：
// - 纯展示组件：不包含业务逻辑和状态管理
// - 通过props接收所有数据和回调函数
// - 专注于UI渲染和用户体验
// - 集成LogStream的消息渲染逻辑

import React, { useMemo, useEffect, useState } from 'react';
import { motion, cubicBezier } from 'framer-motion';
import type { Message, ToolCall } from '../types';
import type { RunStatus } from '../store/auraStore';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { ScrollToBottomButton } from './ScrollToBottomButton';
import { RoleSymbol } from '@/components/ui/RoleSymbol';

interface ChatViewProps {
  messages: Message[];
  currentRunStatus: RunStatus;
  currentRunId: string | null;
  toolCallHistory: Record<string, ToolCall[]>;
  onSendMessage: (message: string) => void;
  scrollContainerRef: React.RefObject<HTMLDivElement | null>;
  showScrollButton: boolean;
  onScrollToBottom: () => void;
  suppressAutoScroll?: (durationMs?: number) => void;
}

export const ChatView: React.FC<ChatViewProps> = ({
  messages,
  currentRunStatus,
  currentRunId,
  toolCallHistory,
  onSendMessage,
  scrollContainerRef,
  showScrollButton,
  onScrollToBottom,
  suppressAutoScroll,
}) => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _toolCallHistory = toolCallHistory;
  // Computed values for cleaner render logic
  // 是否已开始（是否已存在任意消息）
  const hasStarted = messages.length > 0;

  // 思考标识显示控制：仅在「当前运行存在且尚未开始文本流」且最后一条为用户消息时显示（并有轻微延迟）
  const lastMessage = messages[messages.length - 1];
  const isLastHuman = lastMessage?.role === 'HUMAN';
  const [showThinkingIndicator, setShowThinkingIndicator] = useState(false);

  // 是否已有当前 run 的 AI 流式消息（开始打字后就不再显示思考符号）
  const hasStreamingAICurrentRun = useMemo(() => {
    if (!currentRunId) return false;
    return messages.some((m) =>
      m.role === 'AI'
      && (m.isStreaming || ((m.metadata?.isStreaming ?? false)))
      && m.runId === currentRunId
      && ((m.content?.length ?? 0) > 0)
    );
  }, [messages, currentRunId]);

  // 显示条件：仅当当前状态为 thinking，且未开始流式输出，并且上一条为用户消息
  const shouldDisplayThinking = currentRunStatus === 'thinking' && Boolean(currentRunId) && isLastHuman && !hasStreamingAICurrentRun;

  // 思考阶段单独行：仅在 shouldDisplayThinking 且 showThinkingIndicator 为真时展示（有轻微延迟）
  const showThinkingRow = shouldDisplayThinking && showThinkingIndicator;

  useEffect(() => {
    let t: number | undefined;
    if (shouldDisplayThinking) {
      // 轻微延迟，避免与用户消息同帧出现
      t = window.setTimeout(() => setShowThinkingIndicator(true), 800);
    } else {
      setShowThinkingIndicator(false);
    }
    return () => {
      if (t) window.clearTimeout(t);
    };
  }, [shouldDisplayThinking]);

  // 输入区域动画：单一父容器中，通过 transform 控制从居中 -> 底部
  const inputMotion = useMemo(() => {
    return {
      initial: false as const, // 避免首次挂载时闪烁
      animate: hasStarted
        ? { y: 0, opacity: 1 }
        : { y: 'calc(-50vh + 4rem)', opacity: 1 },
      transition: {
        duration: 0.8,
        ease: cubicBezier(0.22, 1, 0.36, 1),
        type: 'tween' as const,
      },
    };
  }, [hasStarted]);

  // 标题淡入淡出
  const titleMotion = useMemo(() => {
    return {
      initial: { opacity: 0 },
      animate: { opacity: hasStarted ? 0 : 1 },
      transition: { duration: 0.5, ease: cubicBezier(0.22, 1, 0.36, 1) },
    };
  }, [hasStarted]);

  return (
    <div className="h-screen bg-background text-foreground font-sans relative overflow-hidden">
      {/* 统一布局：顶部内容区 + 中央/底部动画输入区 */}
      <div className="h-full relative">
        {/* 滚动消息区：根据 hasStarted 控制可见性与入场 */}
        <motion.div
          className="h-full overflow-y-auto pb-32"
          style={{ scrollBehavior: 'auto', scrollbarGutter: 'stable both-edges', overflowAnchor: 'auto' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: hasStarted ? 1 : 0 }}
          transition={{ duration: 0.5, ease: cubicBezier(0.22, 1, 0.36, 1) }}
          ref={scrollContainerRef}
        >
          <div className="flex justify-center">
            {/* 消息流渲染 - 集成原LogStream逻辑 */}
            <div className="w-full max-w-3xl mx-auto px-4">
              {messages.map((message, index) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  isLastMessage={index === messages.length - 1}
                  currentRunStatus={currentRunStatus}
                  suppressAutoScroll={suppressAutoScroll}
                />
              ))}

              {/* 思考阶段：独立的呼吸符号行，仅在尚未出现当前 run 的 AI 文本时显示 */}
              {showThinkingRow && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, ease: 'easeOut' }}
                  className="py-6 flex items-center gap-3"
                >
                  <RoleSymbol role="AI" isThinking={true} />
                  <div className="flex-1 min-w-0" />
                </motion.div>
              )}

              {/* 工具卡片由 ChatMessage 内部按插入位置渲染，避免重复与顺序漂移 */}
            </div>
          </div>
        </motion.div>

        {/* 初始标题：仅在未开始时显示，位于页面中心上方更多 */}
        <motion.div
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          {...titleMotion}
        >
          <h1 className="text-4xl font-light text-secondary-foreground tracking-[0.2em] -translate-y-32">
            YX NEXUS
          </h1>
        </motion.div>

        {/* 输入区域：单一父容器内，过渡从中心 -> 底部 */}
        <motion.div
          className="absolute left-0 right-0 bottom-0 flex justify-center p-6"
          {...inputMotion}
        >
          <div className="w-full max-w-2xl">
            <ChatInput
              onSendMessage={onSendMessage}
            />
          </div>
        </motion.div>

        {/* 滚动到底部按钮 */}
        <ScrollToBottomButton
          show={showScrollButton && hasStarted}
          onClick={onScrollToBottom}
        />
      </div>
    </div>
  );
};
