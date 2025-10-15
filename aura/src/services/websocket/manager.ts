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

import {
  parseNexusEvent,
  createClientMessage,
  createSystemCommandMessage
} from './protocol';
// Following the Single Gateway Principle - derive WebSocket URL from NEXUS_BASE_URL
import { IdentityService } from '../identity/identity';

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
  heartbeatInterval?: number;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private config: Required<Omit<WebSocketManagerConfig, 'url'>>;
  private emitter: EventEmitter = new EventEmitter();
  publicKey: string = '';
  private baseUrl: string;
  private isConnected: boolean = false;
  private reconnectAttempts: number = 0;
  private heartbeatTimer: number | null = null;
  private reconnectTimer: number | null = null;

  constructor(config: WebSocketManagerConfig = {}) {
    this.baseUrl = this._getBaseUrl();
    // publicKey will be initialized in connect()
    this.config = {
      heartbeatInterval: config.heartbeatInterval ?? 30000, // 30 seconds
      reconnectInterval: config.reconnectInterval ?? 5000,   // 5 seconds
      maxReconnectAttempts: config.maxReconnectAttempts ?? 10
    };
  }

  // ===== Private URL Management =====

  private _getBaseUrl(): string {
    // Prefer configured base URL at build-time; fallback to current origin for runtime flexibility
    const configuredBase = (import.meta.env.VITE_NEXUS_BASE_URL || '').trim();
    const httpBase = configuredBase !== '' ? configuredBase : window.location.origin;

    // Convert HTTP to WebSocket protocol
    let wsUrl = httpBase.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');

    // Append WebSocket path
    wsUrl = `${wsUrl}/api/v1/ws`;

    console.log('🔗 Derived WebSocket URL from NEXUS_BASE_URL:', wsUrl);
    return wsUrl;
  }

  // ===== Private Identity Management =====

  private async _getPublicKey(): Promise<string> {
    // Get or create user identity and return the public key
    const identity = await IdentityService.getIdentity();
    console.log('🔑 Using Public Key for identity:', identity.publicKey);
    return identity.publicKey;
  }

  // ===== Public API =====

  async connect(): Promise<void> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    // Get persistent public key and construct full WebSocket URL
    this.publicKey = await this._getPublicKey();
    const fullUrl = `${this.baseUrl}/${this.publicKey}`;

    // Debug information
    const isDevelopment = window.location.hostname === 'localhost' ||
                         window.location.hostname === '127.0.0.1';
    console.log('🔌 Connecting to WebSocket with Public Key:', {
      environment: isDevelopment ? 'development' : 'production',
      hostname: window.location.hostname,
      baseUrl: this.baseUrl,
      fullUrl: fullUrl,
      publicKey: this.publicKey
    });

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(fullUrl);
        
        this.ws.onopen = () => {
          console.log('✅ WebSocket connected to NEXUS');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          this.emitter.emit('connected', { publicKey: this.publicKey });
          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data);
        };

        this.ws.onclose = () => {
          console.log('❌ WebSocket disconnected from NEXUS');
          this.isConnected = false;
          this.stopHeartbeat();
          this.emitter.emit('disconnected', {});
          this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
          console.error('💥 WebSocket error:', error);
          console.error('📍 Connection details:', {
            environment: isDevelopment ? 'development' : 'production',
            hostname: window.location.hostname,
            baseUrl: this.baseUrl,
            fullUrl: fullUrl,
            publicKey: this.publicKey,
            readyState: this.ws?.readyState
          });
          this.emitter.emit('error', { error });
          reject(error);
        };

      } catch (error) {
        console.error('💥 Failed to create WebSocket:', error);
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

  /**
   * Reconnect to WebSocket with optional new identity
   * Useful for identity switching scenarios (import/export)
   * 
   * @param newPublicKey - Optional new public key to use for reconnection
   */
  async reconnect(newPublicKey?: string): Promise<void> {
    console.log('🔄 Reconnecting WebSocket...', newPublicKey ? 'with new identity' : '');
    
    // Disconnect first
    this.disconnect();
    
    // If a new public key is provided, update it
    // Otherwise, connect() will fetch the current identity
    if (newPublicKey) {
      this.publicKey = newPublicKey;
    }
    
    // Reconnect with the (possibly new) identity
    await this.connect();
  }

  sendMessage(input: string): void {
    if (!this.isConnected || !this.ws) {
      console.error('Cannot send message: WebSocket not connected');
      return;
    }

    const clientTimestamp = new Date().toISOString();
    const message = createClientMessage(input, this.publicKey, clientTimestamp);
    const messageStr = JSON.stringify(message);

    try {
      this.ws.send(messageStr);
      console.log('Sent message to NEXUS:', { input, publicKey: this.publicKey, clientTimestamp });
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  }

  sendCommand(command: string, auth?: { publicKey: string; signature: string }): void {
    if (!this.isConnected || !this.ws) {
      console.error('Cannot send command: WebSocket not connected');
      return;
    }

    const message = createSystemCommandMessage(command, this.publicKey, auth);
    const messageStr = JSON.stringify(message);

    try {
      this.ws.send(messageStr);
      console.log('Sent command to NEXUS:', { 
        command, 
        publicKey: this.publicKey,
        signed: !!auth
      });
    } catch (error) {
      console.error('Failed to send command:', error);
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
        // The payload type depends on the event kind and is validated in parseNexusEvent.
        // We keep it unknown here and let subscribers type it.
        this.emitter.emit(nexusEvent.event, nexusEvent.payload as unknown);
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

  get currentPublicKey(): string {
    return this.publicKey;
  }
}

// ===== Singleton Instance =====

export const websocketManager = new WebSocketManager();
