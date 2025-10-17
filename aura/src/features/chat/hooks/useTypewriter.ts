// src/features/chat/hooks/useTypewriter.ts
// 流式渲染引擎 - 自主管理打字机效果，实现 AI 思绪流
// 
// Stream of Thought: 文本以有机的、类人的节奏出现，而非机械打印
// - 微观变速：每个字符的延迟在 10-25ms 之间随机变化
// - 启动延迟：首字符前有 50-100ms 的"思考启动"停顿
import { useState, useEffect, useRef } from 'react';
import { getTypewriterSpeed, getTypewriterStartupDelay } from '@/lib/motion';

interface UseTypewriterOptions {
  /** 目标文本，这个值会随着新的chunk流入而动态变化 */
  targetContent: string;
  /** 是否为流式消息（用于判断是否需要打字机效果） */
  isStreamingMessage: boolean;
  /** 
   * @deprecated 不再使用固定速度，现在使用微观变速（10-25ms）
   * 保留此参数仅为向后兼容
   */
  speed?: number;
}

interface UseTypewriterReturn {
  /** 当前显示的内容 */
  displayedContent: string;
  /** 打字机是否正在工作 */
  isTyping: boolean;
  /** 打字机是否已完成 */
  isFinished: boolean;
}

/**
 * useTypewriter Hook - AI 思绪流渲染引擎
 *
 * 核心设计理念：
 * 1. 自主管理打字机状态，不依赖外部enabled控制
 * 2. 智能检测内容变化，持续渲染直到完成
 * 3. 区分"非流式消息"和"流式消息"的渲染策略
 * 4. **微观变速**：每个字符的延迟随机变化（10-25ms），模拟有机思考节奏
 * 5. **启动延迟**：首字符前短暂停顿（50-100ms），模拟"开始思考"
 *
 * 解决的问题：
 * - 流式输出中途被中断的问题
 * - 外部状态变化导致打字机重置的问题
 * - 缺乏打字机完成状态的问题
 * - **机械式均匀速度的问题** - 现在速度有机变化
 */
export const useTypewriter = ({
  targetContent,
  isStreamingMessage,
  speed: _speed, // deprecated, ignored (prefixed with _ to suppress warning)
}: UseTypewriterOptions): UseTypewriterReturn => {
  const [displayedContent, setDisplayedContent] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isFinished, setIsFinished] = useState(false);

  const currentIndexRef = useRef(0);
  const timeoutIdRef = useRef<number | undefined>(undefined); // Changed from interval to timeout
  const targetContentRef = useRef(targetContent);
  const lastTargetLengthRef = useRef(0);
  const hasStartedRef = useRef(false); // Track if we've applied startup delay

  // 更新目标内容引用
  useEffect(() => {
    targetContentRef.current = targetContent;
  }, [targetContent]);

  // 核心打字机逻辑
  useEffect(() => {
    // 非流式消息：仅在未开始打字（历史消息）时直接显示；如果已开始或有未完成的内容则继续打字至完成
    if (!isStreamingMessage && currentIndexRef.current === 0) {
      setDisplayedContent(targetContent);
      setIsTyping(false);
      setIsFinished(true);
      currentIndexRef.current = targetContent.length;
      return;
    }

    // 流式消息：启动打字机效果
    if (!isTyping && targetContent.length > 0) {
      setIsTyping(true);
      setIsFinished(false);
    }

    // 如果没有内容，重置状态
    if (targetContent.length === 0) {
      setDisplayedContent('');
      setIsTyping(false);
      setIsFinished(false);
      currentIndexRef.current = 0;
      lastTargetLengthRef.current = 0;
      return;
    }

    // 递归打字函数：使用 setTimeout 实现变速
    const typeNextChar = () => {
      const currentTarget = targetContentRef.current;

      if (currentIndexRef.current >= currentTarget.length) {
        // 已经显示完所有当前内容，等待更多内容或检查是否完成
        // 如果目标内容长度没有变化一段时间，认为打字完成
        timeoutIdRef.current = window.setTimeout(() => {
          if (currentIndexRef.current >= targetContentRef.current.length) {
            setIsTyping(false);
            setIsFinished(true);
            timeoutIdRef.current = undefined;
          }
        }, 50); // 等待 50ms 检查是否还有新内容
        return;
      }

      const nextChar = currentTarget[currentIndexRef.current];
      setDisplayedContent((prev) => prev + nextChar);
      currentIndexRef.current++;

      // 获取下一个字符的变速延迟（10-25ms 随机）
      const nextDelay = getTypewriterSpeed();
      
      timeoutIdRef.current = window.setTimeout(typeNextChar, nextDelay);
    };

    // 启动或继续打字机：当处于流式中，或虽已结束但尚未追平目标内容
    if (!timeoutIdRef.current && (isStreamingMessage || currentIndexRef.current < targetContentRef.current.length)) {
      // 如果是首次启动，应用启动延迟（50-100ms）
      if (!hasStartedRef.current && currentIndexRef.current === 0) {
        hasStartedRef.current = true;
        const startupDelay = getTypewriterStartupDelay();
        timeoutIdRef.current = window.setTimeout(typeNextChar, startupDelay);
      } else {
        // 继续打字，不需要启动延迟
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

  // 清理定时器
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
