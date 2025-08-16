// src/components/ui/ConnectionStatus.tsx
// WebSocket连接状态指示器组件

import React, { useEffect, useState } from 'react';
import wsManager from '@/services/websocket/manager';
import type { ConnectionStatusChangeEvent } from '@/services/websocket/protocol';

interface ConnectionStatusProps {
  className?: string;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ className = '' }) => {
  const [status, setStatus] = useState<ConnectionStatusChangeEvent | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  // 检查是否使用模拟数据模式
  const useMockData = import.meta.env.VITE_USE_MOCK_DATA === 'true';

  useEffect(() => {
    if (useMockData) {
      // 模拟模式下显示模拟状态
      setStatus({
        status: 'connected',
        timestamp: new Date().toISOString(),
        reconnectAttempts: 0,
      });
      setIsVisible(true);
      return;
    }

    // 真实模式下监听WebSocket状态变化
    const handleStatusChange = (statusEvent: ConnectionStatusChangeEvent) => {
      setStatus(statusEvent);
      
      // 只在非连接状态时显示指示器
      setIsVisible(statusEvent.status !== 'connected');
      
      // 连接成功后3秒隐藏指示器
      if (statusEvent.status === 'connected') {
        setTimeout(() => setIsVisible(false), 3000);
      }
    };

    wsManager.onStatusChange(handleStatusChange);

    return () => {
      // 清理监听器（如果WebSocketManager支持的话）
    };
  }, [useMockData]);

  if (!isVisible || !status) {
    return null;
  }

  const getStatusIndicator = () => {
    // 遵循灰度铁律：只使用灰度，通过透明度和动画表达状态
    switch (status.status) {
      case 'connected':
        return 'bg-white/20'; // 连接成功：较亮的灰度
      case 'connecting':
        return 'bg-white/10 animate-pulse'; // 连接中：脉动动画
      case 'reconnecting':
        return 'bg-white/15 animate-pulse'; // 重连中：中等亮度脉动
      case 'disconnected':
        return 'bg-white/5'; // 断开：最暗的灰度
      default:
        return 'bg-white/8';
    }
  };

  const getStatusText = () => {
    if (useMockData) {
      return '🎭 模拟模式';
    }

    switch (status.status) {
      case 'connected':
        return '🔗 已连接';
      case 'connecting':
        return '🔄 连接中...';
      case 'reconnecting':
        return `🔄 重连中... (${status.reconnectAttempts}/5)`;
      case 'disconnected':
        return '❌ 连接断开';
      default:
        return '❓ 未知状态';
    }
  };

  return (
    <div className={`fixed top-4 right-4 z-50 ${className}`}>
      {/* 遵循标准材质：半透明背景、模糊效果、纤细边框、柔和阴影 */}
      <div className="flex items-center space-x-3 bg-card/75 backdrop-blur-xl border border-border shadow-lg shadow-black/20 rounded-lg px-4 py-2 text-sm text-foreground transition-colors duration-300 ease-in-out">
        <div className={`w-2 h-2 rounded-full ${getStatusIndicator()}`} />
        <span className="text-sm">{getStatusText()}</span>
        {status.error && (
          <span className="text-xs text-muted-foreground">({status.error})</span>
        )}
      </div>
    </div>
  );
};

export default ConnectionStatus;
