// aura/src/services/websocket/manager.ts
// A pure WebSocket communication layer for AURA. It manages connection,
// heartbeat, auto-reconnect, and broadcasts parsed events via an internal emitter.

import { v4 as uuidv4 } from 'uuid';
import type { NexusToAuraEvent } from './protocol';

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

// Minimal event emitter implementation to avoid extra deps
type Handler<T = any> = (payload: T) => void;
class Emitter {
  private map = new Map<string, Set<Handler>>();

  on(event: string, handler: Handler) {
    if (!this.map.has(event)) this.map.set(event, new Set());
    this.map.get(event)!.add(handler);
  }

  off(event: string, handler: Handler) {
    this.map.get(event)?.delete(handler);
  }

  emit<T = any>(event: string, payload: T) {
    this.map.get(event)?.forEach((h) => h(payload));
  }

  clearAll() {
    this.map.clear();
  }
}

export interface WebSocketManagerConfig {
  maxReconnectAttempts?: number; // default 5
  heartbeatIntervalMs?: number; // default 30_000
  reconnectBackoffBaseMs?: number; // default 1_000
  enableHeartbeat?: boolean; // default true
  enableAutoReconnect?: boolean; // default true
}

export interface AuraToNexusMessage {
  content: string;
}

class WebSocketManager {
  public readonly emitter = new Emitter();

  private socket: WebSocket | null = null;
  private baseUrl: string; // e.g., ws://localhost:8765/ws
  private sessionId: string | null = null;
  private status: WebSocketStatus = 'disconnected';

  // reconnect/heartbeat
  private reconnectAttempts = 0;
  private maxReconnectAttempts: number;
  private reconnectBackoffBase: number;
  private isManualDisconnect = false;
  private reconnectTimer: number | null = null;

  private heartbeatInterval: number;
  private heartbeatTimer: number | null = null;
  private enableHeartbeat: boolean;
  private enableAutoReconnect: boolean;

  constructor(baseUrl: string, config: WebSocketManagerConfig = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.maxReconnectAttempts = config.maxReconnectAttempts ?? 5;
    this.heartbeatInterval = config.heartbeatIntervalMs ?? 30_000;
    this.reconnectBackoffBase = config.reconnectBackoffBaseMs ?? 1_000;
    this.enableHeartbeat = config.enableHeartbeat ?? true;
    this.enableAutoReconnect = config.enableAutoReconnect ?? true;
  }

  getStatus(): WebSocketStatus {
    return this.status;
  }

  getSessionId(): string | null {
    return this.sessionId;
  }

  private setStatus(next: WebSocketStatus) {
    this.status = next;
    this.emitter.emit('status', next);
  }

  private loadOrCreateSessionId(): string {
    const key = 'aura_session_id';
    const existing = typeof window !== 'undefined' ? localStorage.getItem(key) : null;
    if (existing) return existing;
    const sid = `sess_${uuidv4()}`;
    try { localStorage.setItem(key, sid); } catch {}
    return sid;
  }

  connect(sessionId?: string) {
    // prevent duplicate connects
    if (this.socket && (this.socket.readyState === WebSocket.CONNECTING || this.socket.readyState === WebSocket.OPEN)) {
      return;
    }

    this.isManualDisconnect = false;
    this.sessionId = sessionId ?? this.loadOrCreateSessionId();
    const url = `${this.baseUrl}/${this.sessionId}`;

    this.setStatus('connecting');

    try {
      this.socket = new WebSocket(url);

      this.socket.onopen = () => {
        this.reconnectAttempts = 0;
        this.setStatus('connected');
        this.startHeartbeat();
      };

      this.socket.onmessage = (ev) => this.handleMessage(ev.data);

      this.socket.onclose = () => {
        this.stopHeartbeat();
        if (this.isManualDisconnect) {
          this.setStatus('disconnected');
        } else if (this.enableAutoReconnect) {
          this.reconnect();
        } else {
          this.setStatus('disconnected');
        }
      };

      this.socket.onerror = () => {
        this.stopHeartbeat();
        if (!this.isManualDisconnect && this.enableAutoReconnect) {
          this.reconnect();
        } else {
          this.setStatus('disconnected');
        }
      };
    } catch {
      this.setStatus('disconnected');
    }
  }

  disconnect(isManual = true) {
    this.isManualDisconnect = isManual;
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.socket) {
      try { this.socket.close(); } catch {}
      this.socket = null;
    }
    if (isManual) this.reconnectAttempts = 0;
  }

  sendMessage(msg: AuraToNexusMessage) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(msg));
    }
  }

  private startHeartbeat() {
    if (!this.enableHeartbeat) return;
    this.stopHeartbeat();
    this.heartbeatTimer = window.setInterval(() => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        try { this.socket.send('ping'); } catch {}
      }
    }, this.heartbeatInterval);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.setStatus('disconnected');
      return;
    }
    this.reconnectAttempts += 1;
    this.setStatus('reconnecting');
    const delay = Math.pow(2, this.reconnectAttempts - 1) * this.reconnectBackoffBase;
    this.reconnectTimer = window.setTimeout(() => this.connect(this.sessionId ?? undefined), delay);
  }

  private handleMessage(data: string) {
    try {
      const parsed = JSON.parse(data);
      // preferred protocol: { event, run_id, payload }
      if (parsed && typeof parsed.event === 'string' && typeof parsed.run_id === 'string') {
        this.emitter.emit(parsed.event, parsed as NexusToAuraEvent);
        this.emitter.emit('message', parsed as NexusToAuraEvent);
        return;
      }
      // fallback for legacy/simple responses: { type: 'response', run_id, content }
      if (parsed && parsed.type === 'response' && typeof parsed.run_id === 'string') {
        const fallback = {
          event: 'text_chunk',
          run_id: parsed.run_id,
          payload: { chunk: String(parsed.content ?? '') },
        } as NexusToAuraEvent;
        this.emitter.emit('text_chunk', fallback);
        this.emitter.emit('message', fallback);
        return;
      }
    } catch {
      // ignore non-JSON messages and heartbeat pongs
    }
  }
}

// Export a singleton instance
const base = (import.meta as any).env?.VITE_WS_BASE_URL || 'ws://localhost:8765/ws';
const websocketManager = new WebSocketManager(base, {
  maxReconnectAttempts: 5,
  heartbeatIntervalMs: 30_000,
  reconnectBackoffBaseMs: 1_000,
  enableHeartbeat: true,
  enableAutoReconnect: true,
});

export default websocketManager;
