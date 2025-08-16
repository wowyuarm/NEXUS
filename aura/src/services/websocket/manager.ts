// src/services/websocket/manager.ts

import type {
  XiSystemEvent,
  WebSocketStatus,
  WebSocketManagerConfig,
  ConnectionStatusChangeEvent,
  ClientMessage
} from './protocol';
import { parseProtocolMessage } from './protocol';

class WebSocketManager {
  private socket: WebSocket | null = null;
  private url: string;
  private status: WebSocketStatus = 'disconnected';

  // 重连相关状态
  private reconnectAttempts = 0;
  private maxReconnectAttempts: number;
  private reconnectBackoffBase: number;
  private isManualDisconnect = false;
  private reconnectTimer: NodeJS.Timeout | null = null;

  // 心跳相关状态
  private heartbeatInterval: number;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private enableHeartbeat: boolean;
  private enableAutoReconnect: boolean;

  // 回调函数
  private onMessageCallback: ((event: XiSystemEvent) => void) | null = null;
  private onStatusChangeCallback: ((event: ConnectionStatusChangeEvent) => void) | null = null;

  constructor(url: string, config: Partial<WebSocketManagerConfig> = {}) {
    this.url = url;

    // 配置参数
    this.maxReconnectAttempts = config.maxReconnectAttempts ?? 5;
    this.heartbeatInterval = config.heartbeatInterval ?? 30000; // 30秒
    this.reconnectBackoffBase = config.reconnectBackoffBase ?? 1000; // 1秒
    this.enableHeartbeat = config.enableHeartbeat ?? true;
    this.enableAutoReconnect = config.enableAutoReconnect ?? true;

    console.log('WebSocketManager initialized with config:', {
      url: this.url,
      maxReconnectAttempts: this.maxReconnectAttempts,
      heartbeatInterval: this.heartbeatInterval,
      enableHeartbeat: this.enableHeartbeat,
      enableAutoReconnect: this.enableAutoReconnect
    });
  }

  public connect() {
    // 防止重复连接
    if (this.socket && (this.socket.readyState === WebSocket.CONNECTING || this.socket.readyState === WebSocket.OPEN)) {
      console.log('WebSocket is already connecting or connected');
      return;
    }

    this.isManualDisconnect = false;
    this.setStatus('connecting');

    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        console.log('WebSocket connected successfully');
        this.reconnectAttempts = 0; // 重置重连计数
        this.setStatus('connected');
        this.startHeartbeat(); // 启动心跳
      };

      this.socket.onmessage = (event) => {
        this.handleMessage(event.data);
      };

      this.socket.onclose = (event) => {
        console.log('WebSocket connection closed:', event.code, event.reason);
        this.stopHeartbeat(); // 停止心跳

        if (this.isManualDisconnect) {
          this.setStatus('disconnected');
        } else if (this.enableAutoReconnect) {
          this.reconnect();
        } else {
          this.setStatus('disconnected');
        }
      };

      this.socket.onerror = (error) => {
        console.error('WebSocket Error:', error);
        this.stopHeartbeat();

        if (!this.isManualDisconnect && this.enableAutoReconnect) {
          this.reconnect();
        } else {
          this.setStatus('disconnected');
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.setStatus('disconnected');
    }
  }

  /**
   * 处理接收到的WebSocket消息
   */
  private handleMessage(data: string) {
    try {
      // 首先检查是否是心跳响应或其他特殊消息
      if (data === 'pong') {
        console.log('Received heartbeat pong');
        return;
      }

      // 尝试解析为协议消息
      const protocolEvent = parseProtocolMessage(data);

      if (protocolEvent && this.onMessageCallback) {
        this.onMessageCallback(protocolEvent);
        return;
      }

      // 向后兼容：处理非协议消息（如纯文本或魔法字符串）
      console.warn('Received non-protocol message:', data);

      // 为了向后兼容，将非协议消息包装成text_chunk事件
      if (this.onMessageCallback) {
        const fallbackEvent: XiSystemEvent = {
          type: 'text_chunk',
          payload: { chunk: data },
          metadata: {
            message_id: 'fallback-' + Date.now(),
            timestamp: new Date().toISOString()
          }
        };
        this.onMessageCallback(fallbackEvent);
      }

    } catch (error) {
      console.error('Error handling WebSocket message:', error);

      // 发送错误事件给回调
      if (this.onMessageCallback) {
        const errorEvent: XiSystemEvent = {
          type: 'error',
          payload: {
            message: 'Failed to parse WebSocket message',
            code: 1001
          },
          metadata: {
            message_id: 'error-' + Date.now(),
            timestamp: new Date().toISOString()
          }
        };
        this.onMessageCallback(errorEvent);
      }
    }
  }

  /**
   * 启动心跳机制
   */
  private startHeartbeat() {
    if (!this.enableHeartbeat) {
      return;
    }

    this.stopHeartbeat(); // 确保没有重复的定时器

    this.heartbeatTimer = setInterval(() => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        try {
          this.socket.send(JSON.stringify({ type: 'ping' }));
          console.log('Sent heartbeat ping');
        } catch (error) {
          console.error('Failed to send heartbeat:', error);
        }
      }
    }, this.heartbeatInterval);

    console.log(`Heartbeat started with interval: ${this.heartbeatInterval}ms`);
  }

  /**
   * 停止心跳机制
   */
  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
      console.log('Heartbeat stopped');
    }
  }

  /**
   * 自动重连逻辑（指数退避策略）
   */
  private reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(`WebSocket: Max reconnect attempts (${this.maxReconnectAttempts}) reached`);
      this.setStatus('disconnected');
      return;
    }

    this.reconnectAttempts++;
    this.setStatus('reconnecting');

    // 指数退避策略：1s, 2s, 4s, 8s, 16s...
    const delay = Math.pow(2, this.reconnectAttempts - 1) * this.reconnectBackoffBase;
    console.log(`WebSocket: Attempting to reconnect in ${delay / 1000}s... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  public sendMessage(data: ClientMessage) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    } else {
      console.error('WebSocket is not connected.');
    }
  }

  public onMessage(callback: (event: XiSystemEvent) => void) {
    this.onMessageCallback = callback;
  }

  public onStatusChange(callback: (event: ConnectionStatusChangeEvent) => void) {
    this.onStatusChangeCallback = callback;
  }

  private setStatus(status: WebSocketStatus, error?: string) {
    this.status = status;
    if (this.onStatusChangeCallback) {
      const statusEvent: ConnectionStatusChangeEvent = {
        status,
        timestamp: new Date().toISOString(),
        reconnectAttempts: this.reconnectAttempts,
        error
      };
      this.onStatusChangeCallback(statusEvent);
    }
  }

  public disconnect(isManual: boolean = true) {
    console.log(`WebSocket disconnect called (manual: ${isManual})`);

    this.isManualDisconnect = isManual;

    // 清理定时器
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    // 关闭连接
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }

    // 如果是手动断开，重置重连计数
    if (isManual) {
      this.reconnectAttempts = 0;
    }
  }

  public getStatus(): WebSocketStatus {
    return this.status;
  }
}

// 创建并导出一个单例
const wsManager = new WebSocketManager(
  import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/ws/chat',
  {
    maxReconnectAttempts: 5,
    heartbeatInterval: 30000, // 30秒
    reconnectBackoffBase: 1000, // 1秒
    enableHeartbeat: true,
    enableAutoReconnect: true
  }
);

export default wsManager;
