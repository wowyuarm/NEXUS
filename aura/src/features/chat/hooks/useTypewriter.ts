// src/features/chat/hooks/useTypewriter.ts
// 流式渲染引擎 - 自主管理打字机效果，不依赖外部状态控制
import { useState, useEffect, useRef } from 'react';

interface UseTypewriterOptions {
  /** 目标文本，这个值会随着新的chunk流入而动态变化 */
  targetContent: string;
  /** 是否为流式消息（用于判断是否需要打字机效果） */
  isStreamingMessage: boolean;
  /** 打字速度 (ms/char) */
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
 * useTypewriter Hook - 重新设计的流式渲染引擎
 *
 * 核心设计理念：
 * 1. 自主管理打字机状态，不依赖外部enabled控制
 * 2. 智能检测内容变化，持续渲染直到完成
 * 3. 区分"非流式消息"和"流式消息"的渲染策略
 * 4. 提供完整的状态信息供外部使用
 *
 * 解决的问题：
 * - 流式输出中途被中断的问题
 * - 外部状态变化导致打字机重置的问题
 * - 缺乏打字机完成状态的问题
 */
export const useTypewriter = ({
  targetContent,
  isStreamingMessage,
  speed = 15,
}: UseTypewriterOptions): UseTypewriterReturn => {
  const [displayedContent, setDisplayedContent] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isFinished, setIsFinished] = useState(false);

  const currentIndexRef = useRef(0);
  const intervalIdRef = useRef<number | undefined>(undefined);
  const targetContentRef = useRef(targetContent);
  const lastTargetLengthRef = useRef(0);

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

    // 启动或继续打字机定时器：当处于流式中，或虽已结束但尚未追平目标内容
    if (!intervalIdRef.current && (isStreamingMessage || currentIndexRef.current < targetContentRef.current.length)) {
      intervalIdRef.current = window.setInterval(() => {
        const currentTarget = targetContentRef.current;

        if (currentIndexRef.current >= currentTarget.length) {
          // 已经显示完所有当前内容，等待更多内容或结束
          return;
        }

        const nextChar = currentTarget[currentIndexRef.current];
        setDisplayedContent((prev) => prev + nextChar);
        currentIndexRef.current++;

        // 检查是否完成
        if (currentIndexRef.current >= currentTarget.length) {
          // 如果目标内容长度没有变化一段时间，认为打字完成
          setTimeout(() => {
            if (currentIndexRef.current >= targetContentRef.current.length) {
              setIsTyping(false);
              setIsFinished(true);
              if (intervalIdRef.current) {
                window.clearInterval(intervalIdRef.current);
                intervalIdRef.current = undefined;
              }
            }
          }, speed * 3); // 等待3个字符的时间
        }
      }, speed);
    }

    return () => {
      if (intervalIdRef.current) {
        window.clearInterval(intervalIdRef.current);
        intervalIdRef.current = undefined;
      }
    };
  }, [targetContent, isStreamingMessage, speed, isTyping]);

  // 清理定时器
  useEffect(() => {
    return () => {
      if (intervalIdRef.current) {
        window.clearInterval(intervalIdRef.current);
      }
    };
  }, []);

  return {
    displayedContent,
    isTyping,
    isFinished
  };
};
