// src/components/ui/Timestamp.tsx
// 智能时间显示组件 - 支持相对时间和悬停显示
import React from 'react';
import { cn } from '@/lib/utils';
import { TAILWIND } from '@/lib/motion';

interface TimestampProps {
  date: Date;
  format?: 'time' | 'date' | 'datetime' | 'smart' | 'compact';
  className?: string;
  showOnHover?: boolean; // Whether to show only on hover
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

    // Today: show time only
    if (diffInDays === 0) {
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    }

    // 1-6 days ago: show "X days ago"
    if (diffInDays <= 6) {
      return `${diffInDays}天前`;
    }

    // 7+ days: show month-day
    if (diffInDays <= 365) {
      return date.toLocaleDateString('zh-CN', {
        month: 'short',
        day: 'numeric'
      });
    }

    // Over a year: show year-month-day
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getCompactTime = (date: Date) => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const messageDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const diffInDays = Math.floor((today.getTime() - messageDate.getTime()) / 86400000);

    const timeStr = date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });

    // Today: show time only (e.g., "10:23")
    if (diffInDays === 0) {
      return timeStr;
    }

    // Yesterday: show "昨天 10:23"
    if (diffInDays === 1) {
      return `昨天 ${timeStr}`;
    }

    // Earlier: show "MM-DD HH:mm" (e.g., "10-23 22:14")
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${month}-${day} ${timeStr}`;
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
      case 'compact':
        return getCompactTime(date);
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
        'text-xs text-secondary-foreground/60 select-none',
        TAILWIND.micro,
        showOnHover && 'opacity-0 group-hover:opacity-100',
        className
      )}
    >
      {formatTime(date, format)}
    </time>
  );
};
