/**
 * NEXUS Stream Manager for AURA
 * 
 * A communication manager that handles SSE streams and HTTP requests,
 * replacing WebSocket for real-time communication with NEXUS backend.
 * 
 * Architecture:
 * - Chat messages: POST /chat returns SSE stream
 * - Commands: POST /commands/execute returns JSON
 * - Connection state: GET /stream/{public_key} returns persistent SSE
 * - All events are emitted via EventEmitter pattern (same as WebSocket manager)
 */

import { getNexusConfig } from '../../config/nexus';
import { IdentityService } from '../identity/identity';
import type {
  ChatRequest,
  CommandExecuteRequest,
  CommandExecuteResponse
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

// ===== Stream Manager Configuration =====

export interface StreamManagerConfig {
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

// ===== Stream Manager Implementation =====

export class StreamManager {
  private eventSource: EventSource | null = null;
  private emitter: EventEmitter = new EventEmitter();
  private config: Required<StreamManagerConfig>;
  private baseUrl: string;
  private isConnected: boolean = false;
  private reconnectAttempts: number = 0;
  private reconnectTimer: number | null = null;
  private abortController: AbortController | null = null;
  publicKey: string = '';

  constructor(config: StreamManagerConfig = {}) {
    const nexusConfig = getNexusConfig();
    this.baseUrl = nexusConfig.apiUrl;
    this.config = {
      reconnectInterval: config.reconnectInterval ?? 5000,
      maxReconnectAttempts: config.maxReconnectAttempts ?? 10
    };
  }

  // ===== Private Identity Management =====

  private async _getPublicKey(): Promise<string> {
    const identity = await IdentityService.getIdentity();
    console.log('Using Public Key for identity:', identity.publicKey);
    return identity.publicKey;
  }

  // ===== Public API =====

  /**
   * Establish persistent SSE connection for connection_state and proactive events.
   */
  async connect(): Promise<void> {
    if (this.eventSource && this.eventSource.readyState !== EventSource.CLOSED) {
      console.log('SSE stream already connected');
      return;
    }

    this.publicKey = await this._getPublicKey();
    const streamUrl = `${this.baseUrl}/stream/${this.publicKey}`;

    const isDevelopment = window.location.hostname === 'localhost' ||
                         window.location.hostname === '127.0.0.1';
    console.log('Connecting to SSE stream:', {
      environment: isDevelopment ? 'development' : 'production',
      hostname: window.location.hostname,
      baseUrl: this.baseUrl,
      streamUrl: streamUrl,
      publicKey: this.publicKey
    });

    return new Promise((resolve, reject) => {
      try {
        this.eventSource = new EventSource(streamUrl);

        this.eventSource.onopen = () => {
          console.log('SSE stream connected to NEXUS');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.emitter.emit('connected', { publicKey: this.publicKey });
          resolve();
        };

        this.eventSource.onerror = (error) => {
          console.error('SSE stream error:', error);
          this.isConnected = false;
          this.emitter.emit('error', { error });
          
          if (this.eventSource?.readyState === EventSource.CLOSED) {
            this.emitter.emit('disconnected', {});
            this.attemptReconnect();
          }
          
          // Only reject if this is the initial connection attempt
          if (this.reconnectAttempts === 0) {
            reject(error);
          }
        };

        // Listen for specific SSE event types
        this.eventSource.addEventListener('connection_state', (e: MessageEvent) => {
          try {
            const data = JSON.parse(e.data);
            console.log('Received connection_state:', data);
            this.emitter.emit('connection_state', data);
          } catch (error) {
            console.error('Failed to parse connection_state:', error);
          }
        });

        this.eventSource.addEventListener('command_result', (e: MessageEvent) => {
          try {
            const data = JSON.parse(e.data);
            console.log('Received command_result:', data);
            // Extract payload for compatibility with existing handlers
            this.emitter.emit('command_result', data.payload || data);
          } catch (error) {
            console.error('Failed to parse command_result:', error);
          }
        });

        this.eventSource.addEventListener('error', (e: MessageEvent) => {
          try {
            const data = JSON.parse(e.data);
            console.log('Received error event:', data);
            this.emitter.emit('error', data.payload || data);
          } catch (error) {
            console.error('Failed to parse error event:', error);
          }
        });

      } catch (error) {
        console.error('Failed to create EventSource:', error);
        reject(error);
      }
    });
  }

  /**
   * Disconnect from SSE stream.
   */
  disconnect(): void {
    this.stopReconnect();

    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }

    this.isConnected = false;
  }

  /**
   * Reconnect to SSE stream with optional new identity.
   */
  async reconnect(newPublicKey?: string): Promise<void> {
    console.log('Reconnecting SSE stream...', newPublicKey ? 'with new identity' : '');
    
    this.disconnect();
    
    if (newPublicKey) {
      this.publicKey = newPublicKey;
    }
    
    await this.connect();
  }

  /**
   * Send chat message and handle streaming response.
   * 
   * This method:
   * 1. POSTs to /chat endpoint
   * 2. Receives SSE stream in response
   * 3. Parses and emits events (run_started, text_chunk, tool_call_*, run_finished)
   */
  async sendMessage(input: string): Promise<void> {
    // Cancel any existing chat stream
    if (this.abortController) {
      this.abortController.abort();
    }
    this.abortController = new AbortController();

    const chatRequest: ChatRequest = {
      content: input,
      client_timestamp_utc: new Date().toISOString(),
      client_timezone_offset: new Date().getTimezoneOffset()
    };

    console.log('Sending chat message via HTTP+SSE:', input.substring(0, 50) + '...');

    try {
      const response = await fetch(`${this.baseUrl}/chat`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.publicKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(chatRequest),
        signal: this.abortController.signal
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Chat request failed: ${response.status} - ${errorText}`);
      }

      // Parse SSE stream from response body
      await this.parseSSEStream(response);

    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        console.log('Chat request aborted');
        return;
      }
      console.error('Failed to send message:', error);
      this.emitter.emit('error', { message: String(error) });
      throw error;
    }
  }

  /**
   * Parse SSE stream from fetch response.
   */
  private async parseSSEStream(response: Response): Promise<void> {
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = '';
        let currentData = '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7);
          } else if (line.startsWith('data: ')) {
            currentData = line.slice(6);
          } else if (line === '' && currentEvent && currentData) {
            // Complete event - emit it
            try {
              const eventData = JSON.parse(currentData);
              console.log('Received SSE event:', currentEvent, eventData);
              
              // Emit with payload extraction for compatibility
              const payload = eventData.payload || eventData;
              this.emitter.emit(currentEvent, payload);
            } catch (parseError) {
              console.error('Failed to parse SSE event data:', parseError);
            }
            currentEvent = '';
            currentData = '';
          } else if (line.startsWith(':')) {
            // Comment line (keepalive), ignore
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Execute command via HTTP POST.
   * 
   * @param command - Command string (e.g., "/ping", "/identity")
   * @param auth - Optional authentication data for signed commands
   * @returns Command execution result
   */
  async executeCommand(
    command: string,
    auth?: { publicKey: string; signature: string }
  ): Promise<CommandExecuteResponse> {
    const request: CommandExecuteRequest = {
      command,
      auth
    };

    console.log('Executing command via HTTP:', command);

    try {
      const response = await fetch(`${this.baseUrl}/commands/execute`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.publicKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(request)
      });

      const result = await response.json();
      console.log('Command result:', result);
      return result;
    } catch (error) {
      console.error('Failed to execute command:', error);
      return {
        status: 'error',
        message: `Command execution failed: ${String(error)}`
      };
    }
  }

  /**
   * Send command via WebSocket-compatible interface.
   * This method is for backward compatibility with existing code.
   * Commands are executed via HTTP and results emitted via event.
   */
  sendCommand(command: string, auth?: { publicKey: string; signature: string }): void {
    this.executeCommand(command, auth).then(result => {
      // Emit command result for UI to handle
      this.emitter.emit('command_result', {
        command,
        result
      });
    });
  }

  // ===== Reconnection Logic =====

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

  // ===== Event Subscription API =====

  on<T = unknown>(event: string, callback: EventCallback<T>): void {
    this.emitter.on(event, callback);
  }

  off<T = unknown>(event: string, callback: EventCallback<T>): void {
    this.emitter.off(event, callback);
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

export const streamManager = new StreamManager();
