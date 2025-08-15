// src/components/ui/Timestamp.tsx
// 智能时间显示组件 - 支持相对时间和悬停显示
import React from 'react';
import { cn } from '@/lib/utils';

interface TimestampProps {
  date: Date;
  format?: 'time' | 'date' | 'datetime' | 'smart';
  className?: string;
  showOnHover?: boolean; // 是否只在悬停时显示
}

export const Timestamp: React.FC<TimestampProps> = ({
  date,
  format = 'smart',
  className,
  showOnHover = false
}) => {
  const getSmartTime = (date: Date) => {
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    const diffInDays = Math.floor(diffInSeconds / 86400);

    // 今天的消息显示时间
    if (diffInDays === 0) {
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    }

    // 1-6天前显示"X天前"
    if (diffInDays <= 6) {
      return `${diffInDays}天前`;
    }

    // 7天以上显示月日
    if (diffInDays <= 365) {
      return date.toLocaleDateString('zh-CN', {
        month: 'short',
        day: 'numeric'
      });
    }

    // 超过一年显示年月日
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatTime = (date: Date, format: string) => {
    switch (format) {
      case 'time':
        return date.toLocaleTimeString('zh-CN', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: false
        });
      case 'date':
        return date.toLocaleDateString('zh-CN');
      case 'datetime':
        return date.toLocaleString('zh-CN');
      case 'smart':
        return getSmartTime(date);
      default:
        return getSmartTime(date);
    }
  };

  const getFullDateTime = (date: Date) => {
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  };

  return (
    <time
      dateTime={date.toISOString()}
      title={getFullDateTime(date)}
      className={cn(
        'text-xs text-secondary-foreground/60 select-none transition-opacity duration-200',
        showOnHover && 'opacity-0 group-hover:opacity-100',
        className
      )}
    >
      {formatTime(date, format)}
    </time>
  );
};
