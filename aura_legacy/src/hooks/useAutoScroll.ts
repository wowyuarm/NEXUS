// src/hooks/useAutoScroll.ts
// 通用自动滚动管理Hook - 处理滚动容器的智能滚动逻辑
import { useRef, useCallback, useState, useEffect } from 'react';

interface UseAutoScrollOptions {
  /**
   * 判断是否接近底部的阈值（像素）
   * 当距离底部小于此值时，认为用户在底部
   */
  threshold?: number;
  /**
   * 是否启用调试日志
   */
  debug?: boolean;
}

interface UseAutoScrollReturn {
  /** 滚动容器的ref */
  scrollContainerRef: React.RefObject<HTMLDivElement | null>;
  /** 是否显示滚动到底部按钮 */
  showScrollButton: boolean;
  /** 滚动到底部的函数 */
  scrollToBottom: (behavior?: ScrollBehavior) => void;
}

/**
 * useAutoScroll Hook - 智能滚动行为管理
 *
 * 核心逻辑：
 * 1. 引入isAutoScrollingEnabled状态来跟踪是否应启用自动跟随
 * 2. 场景A: 用户发送消息时，立即滚动到底部
 * 3. 场景B: AI流式输出且用户在底部时，自动跟随新内容
 * 4. 场景C: AI流式输出但用户已向上滚动时，不自动滚动
 * 5. 场景D: 用户从上方返回底部时，重新启用自动跟随
 *
 * @param dependencies 依赖项数组，当内容更新时触发检查
 * @param options 配置选项
 */
export const useAutoScroll = (
  dependencies: any[] = [], // 依赖项数组，当内容更新时触发检查
  options: UseAutoScrollOptions = {}
): UseAutoScrollReturn => {
  const { threshold = 50 } = options;

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);

  // 关键状态：使用ref来避免不必要的重渲染
  const isAutoScrollingEnabled = useRef(true);
  const lastScrollHeight = useRef(0);
  const isSmoothScrolling = useRef(false); // 跟踪是否有平滑滚动正在进行
  const smoothScrollTimeout = useRef<NodeJS.Timeout | null>(null);
  const heightCheckInterval = useRef<NodeJS.Timeout | null>(null); // 高度检查定时器

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'auto') => {
    const container = scrollContainerRef.current;
    if (!container) return;

    // 如果是平滑滚动，设置标记并清除之前的超时
    if (behavior === 'smooth') {
      isSmoothScrolling.current = true;
      if (smoothScrollTimeout.current) {
        clearTimeout(smoothScrollTimeout.current);
      }
      // 设置超时来重置平滑滚动标记（平滑滚动通常需要几百毫秒）
      smoothScrollTimeout.current = setTimeout(() => {
        isSmoothScrolling.current = false;
      }, 800); // 给足够的时间让平滑滚动完成
    }

    // 使用 requestAnimationFrame 确保在下一次绘制前滚动
    requestAnimationFrame(() => {
      container.scrollTo({ top: container.scrollHeight, behavior });
      // 更新 lastScrollHeight 以避免滚动中断
      lastScrollHeight.current = container.scrollHeight;
    });

    // 如果是用户主动点击滚动到底部，则重新启用自动滚动
    if (behavior === 'smooth') {
      isAutoScrollingEnabled.current = true;
    }
  }, []);

  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    const isAtBottom = distanceFromBottom < threshold;

    // 更新自动滚动状态和按钮显示
    isAutoScrollingEnabled.current = isAtBottom;
    setShowScrollButton(!isAtBottom);

    // 更新记录的滚动高度
    lastScrollHeight.current = scrollHeight;
  }, [threshold]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    // 当内容更新时（由依赖项数组触发）
    if (isAutoScrollingEnabled.current) {
      // 如果有平滑滚动正在进行，跳过这次自动滚动
      if (isSmoothScrolling.current) {
        console.log('跳过自动滚动，平滑滚动正在进行');
        return;
      }

      // 使用节流，避免过于频繁的滚动
      const scrollDelay = 16; // 约60fps，减少滚动频率
      setTimeout(() => {
        if (isAutoScrollingEnabled.current && !isSmoothScrolling.current) {
          scrollToBottom('auto');
        }
      }, scrollDelay);
    }

    // 显示/隐藏按钮的逻辑
    const { scrollTop, scrollHeight, clientHeight } = container;
    setShowScrollButton(scrollHeight - scrollTop - clientHeight > threshold);

  }, [dependencies, scrollToBottom, threshold]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  // 高度变化检测 - 用于捕获打字机效果导致的内容变化
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    // 启动高度检查定时器
    heightCheckInterval.current = setInterval(() => {
      const currentHeight = container.scrollHeight;

      // 如果高度增加且用户在底部，自动滚动
      if (currentHeight > lastScrollHeight.current && isAutoScrollingEnabled.current) {
        console.log('高度变化检测到滚动需求:', {
          currentHeight,
          lastHeight: lastScrollHeight.current,
          isAutoScrollingEnabled: isAutoScrollingEnabled.current,
          isSmoothScrolling: isSmoothScrolling.current
        });

        // 避免与平滑滚动冲突
        if (!isSmoothScrolling.current) {
          scrollToBottom('auto');
        }
        lastScrollHeight.current = currentHeight;
      }
    }, 50); // 每50ms检查一次高度变化

    return () => {
      if (heightCheckInterval.current) {
        clearInterval(heightCheckInterval.current);
        heightCheckInterval.current = null;
      }
    };
  }, [scrollToBottom]);

  // 清理超时和定时器
  useEffect(() => {
    return () => {
      if (smoothScrollTimeout.current) {
        clearTimeout(smoothScrollTimeout.current);
      }
      if (heightCheckInterval.current) {
        clearInterval(heightCheckInterval.current);
      }
    };
  }, []);

  return {
    scrollContainerRef,
    showScrollButton,
    scrollToBottom,
  };
};
