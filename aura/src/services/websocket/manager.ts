/**
 * NEXUS WebSocket Manager for AURA
 * 
 * A pure communication manager that handles WebSocket connections, heartbeat,
 * reconnection logic, and event emission. This manager is completely decoupled
 * from UI state and only focuses on protocol-level communication.
 * 
 * Architecture:
 * - Maintains WebSocket connection lifecycle
 * - Parses incoming NEXUS events and emits them via EventEmitter
 * - Provides clean API for sending messages to backend
 * - Handles connection errors and automatic reconnection
 */

import { v4 as uuidv4 } from 'uuid';
import {
  parseNexusEvent,
  createClientMessage,
  isWebSocketResponse
} from './protocol';

// ===== Event Emitter Implementation =====

type EventCallback<T = unknown> = (payload: T) => void;

class EventEmitter {
  private events: Map<string, EventCallback[]> = new Map();

  on<T = unknown>(event: string, callback: EventCallback<T>): void {
    if (!this.events.has(event)) {
      this.events.set(event, []);
    }
    this.events.get(event)!.push(callback as EventCallback);
  }

  off<T = unknown>(event: string, callback: EventCallback<T>): void {
    const callbacks = this.events.get(event);
    if (callbacks) {
      const index = callbacks.indexOf(callback as EventCallback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  emit<T = unknown>(event: string, payload: T): void {
    const callbacks = this.events.get(event);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(payload);
        } catch (error) {
          console.error(`Error in event callback for ${event}:`, error);
        }
      });
    }
  }

  removeAllListeners(event?: string): void {
    if (event) {
      this.events.delete(event);
    } else {
      this.events.clear();
    }
  }
}

// ===== WebSocket Manager =====

export interface WebSocketManagerConfig {
  url: string;
  heartbeatInterval?: number;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private config: Required<WebSocketManagerConfig>;
  private emitter: EventEmitter = new EventEmitter();
  private sessionId: string = uuidv4();
  private isConnected: boolean = false;
  private reconnectAttempts: number = 0;
  private heartbeatTimer: number | null = null;
  private reconnectTimer: number | null = null;

  constructor(config: WebSocketManagerConfig) {
    this.config = {
      url: config.url,
      heartbeatInterval: config.heartbeatInterval ?? 30000, // 30 seconds
      reconnectInterval: config.reconnectInterval ?? 5000,   // 5 seconds
      maxReconnectAttempts: config.maxReconnectAttempts ?? 10
    };
  }

  // ===== Public API =====

  async connect(): Promise<void> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.config.url);
        
        this.ws.onopen = () => {
          console.log('WebSocket connected to NEXUS');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          this.emitter.emit('connected', { sessionId: this.sessionId });
          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data);
        };

        this.ws.onclose = () => {
          console.log('WebSocket disconnected from NEXUS');
          this.isConnected = false;
          this.stopHeartbeat();
          this.emitter.emit('disconnected', {});
          this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.emitter.emit('error', { error });
          reject(error);
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  disconnect(): void {
    this.stopHeartbeat();
    this.stopReconnect();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.isConnected = false;
  }

  sendMessage(input: string): void {
    if (!this.isConnected || !this.ws) {
      console.error('Cannot send message: WebSocket not connected');
      return;
    }

    const message = createClientMessage(input, this.sessionId);
    const messageStr = JSON.stringify(message);
    
    try {
      this.ws.send(messageStr);
      console.log('Sent message to NEXUS:', { input, sessionId: this.sessionId });
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  }

  // ===== Event Subscription API =====

  on<T = unknown>(event: string, callback: EventCallback<T>): void {
    this.emitter.on(event, callback);
  }

  off<T = unknown>(event: string, callback: EventCallback<T>): void {
    this.emitter.off(event, callback);
  }

  // ===== Private Methods =====

  private handleMessage(data: string): void {
    try {
      // Try to parse as NEXUS event first
      const nexusEvent = parseNexusEvent(data);
      if (nexusEvent) {
        console.log('Received NEXUS event:', nexusEvent.event, nexusEvent.run_id);
        this.emitter.emit(nexusEvent.event, nexusEvent.payload);
        return;
      }

      // Try to parse as WebSocket response
      const response = JSON.parse(data);
      if (isWebSocketResponse(response)) {
        console.log('Received WebSocket response:', response.type, response.run_id);
        this.emitter.emit('websocket_response', response);
        return;
      }

      console.warn('Received unknown message format:', data);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error, data);
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.emitter.emit('reconnect_failed', {});
      return;
    }

    this.reconnectAttempts++;
    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.config.maxReconnectAttempts})...`);

    this.reconnectTimer = window.setTimeout(() => {
      this.connect().catch(error => {
        console.error('Reconnection failed:', error);
      });
    }, this.config.reconnectInterval);
  }

  private stopReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  // ===== Getters =====

  get connected(): boolean {
    return this.isConnected;
  }

  get currentSessionId(): string {
    return this.sessionId;
  }
}

// ===== Singleton Instance =====

export const websocketManager = new WebSocketManager({
  url: 'ws://localhost:8000/ws'
});
