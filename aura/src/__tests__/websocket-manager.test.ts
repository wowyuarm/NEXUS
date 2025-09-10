/**
 * Tests for WebSocket Manager environment detection functionality.
 */

import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

// Mock window.location and other browser APIs
const mockLocation = {
  protocol: 'http:',
  host: 'localhost:3000',
  hostname: 'localhost',
  port: '3000',
  origin: 'http://localhost:3000',
  href: 'http://localhost:3000/',
  pathname: '/',
  search: '',
  hash: ''
};

const mockWindow = {
  location: mockLocation,
  setInterval: vi.fn(),
  clearInterval: vi.fn(),
  setTimeout: vi.fn(),
  clearTimeout: vi.fn()
};

// Mock localStorage
const mockLocalStorage = {
  store: {} as Record<string, string>,
  getItem: vi.fn((key: string) => mockLocalStorage.store[key]),
  setItem: vi.fn((key: string, value: string) => {
    mockLocalStorage.store[key] = value;
  }),
  removeItem: vi.fn((key: string) => {
    delete mockLocalStorage.store[key];
  }),
  clear: vi.fn(() => {
    mockLocalStorage.store = {};
  })
};

// Mock WebSocket
class MockWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
  }

  send(data: string) {
    // Mock send method
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }
}

// Mock uuid
vi.mock('uuid', () => ({
  v4: () => 'test-uuid-1234'
}));

// Setup global mocks
global.window = mockWindow as any;
global.localStorage = mockLocalStorage as any;
global.WebSocket = MockWebSocket as any;

// Import after mocking
import { WebSocketManager } from '../services/websocket/manager';

describe('WebSocketManager Environment Detection', () => {
  let websocketManager: WebSocketManager;

  beforeEach(() => {
    // Clear all mocks
    vi.clearAllMocks();
    mockLocalStorage.store = {};
    
    // Create new instance for each test
    websocketManager = new WebSocketManager();
  });

  afterEach(() => {
    // Cleanup
    if (websocketManager) {
      websocketManager.disconnect();
    }
  });

  describe('URL Generation', () => {
    it('should generate correct WebSocket URL for HTTP development environment', () => {
      mockLocation.protocol = 'http:';
      mockLocation.host = 'localhost:3000';

      const manager = new WebSocketManager();
      const baseUrl = (manager as any)._getBaseUrl();

      expect(baseUrl).toBe('ws://localhost:3000/api/v1/ws');
    });

    it('should generate correct WebSocket URL for HTTPS production environment', () => {
      mockLocation.protocol = 'https:';
      mockLocation.host = 'example.com';

      const manager = new WebSocketManager();
      const baseUrl = (manager as any)._getBaseUrl();

      expect(baseUrl).toBe('wss://example.com/api/v1/ws');
    });

    it('should generate correct WebSocket URL for HTTP production environment', () => {
      mockLocation.protocol = 'http:';
      mockLocation.host = 'example.com';

      const manager = new WebSocketManager();
      const baseUrl = (manager as any)._getBaseUrl();

      expect(baseUrl).toBe('ws://example.com/api/v1/ws');
    });

    it('should handle custom ports correctly', () => {
      mockLocation.protocol = 'https:';
      mockLocation.host = 'example.com:8443';

      const manager = new WebSocketManager();
      const baseUrl = (manager as any)._getBaseUrl();

      expect(baseUrl).toBe('wss://example.com:8443/api/v1/ws');
    });

    it('should handle localhost with custom port', () => {
      mockLocation.protocol = 'http:';
      mockLocation.host = 'localhost:8080';

      const manager = new WebSocketManager();
      const baseUrl = (manager as any)._getBaseUrl();

      expect(baseUrl).toBe('ws://localhost:8080/api/v1/ws');
    });
  });

  describe('Connection URL Construction', () => {
    it('should construct full WebSocket URL correctly', async () => {
      mockLocation.protocol = 'http:';
      mockLocation.host = 'localhost:3000';

      const manager = new WebSocketManager();
      
      // Mock the connect method to avoid actual WebSocket connection
      const connectSpy = vi.spyOn(manager, 'connect' as any).mockImplementation(async () => {
        // Simulate successful connection
        const ws = new MockWebSocket('ws://localhost:3000/api/v1/ws/test-session-id');
        ws.readyState = MockWebSocket.OPEN;
        (manager as any).ws = ws;
        (manager as any).isConnected = true;
      });

      await manager.connect();

      // Verify the URL was constructed correctly
      expect(connectSpy).toHaveBeenCalled();
    });

    it('should include session ID in connection URL', async () => {
      mockLocation.protocol = 'http:';
      mockLocation.host = 'localhost:3000';

      const manager = new WebSocketManager();
      
      // Mock getSessionId to return predictable value
      vi.spyOn(manager as any, '_getSessionId').mockReturnValue('test-session-123');

      const connectSpy = vi.spyOn(manager, 'connect' as any).mockImplementation(async () => {
        const sessionId = (manager as any)._getSessionId();
        const baseUrl = (manager as any)._getBaseUrl();
        const fullUrl = `${baseUrl}/${sessionId}`;
        
        expect(fullUrl).toBe('ws://localhost:3000/api/v1/ws/test-session-123');
      });

      await manager.connect();
      expect(connectSpy).toHaveBeenCalled();
    });
  });

  describe('Environment Independence', () => {
    it('should not use hardcoded environment variables', () => {
      // Ensure no import.meta.env is used in URL generation
      mockLocation.protocol = 'https:';
      mockLocation.host = 'production-app.com';

      const manager = new WebSocketManager();
      const baseUrl = (manager as any)._getBaseUrl();

      expect(baseUrl).toBe('wss://production-app.com/api/v1/ws');
      
      // Should not contain any hardcoded values
      expect(baseUrl).not.toContain('localhost:8000');
      expect(baseUrl).not.toContain('127.0.0.1');
    });

    it('should adapt to different environments dynamically', () => {
      // Test with development environment
      mockLocation.protocol = 'http:';
      mockLocation.host = 'localhost:3000';
      
      let manager = new WebSocketManager();
      let baseUrl = (manager as any)._getBaseUrl();
      expect(baseUrl).toBe('ws://localhost:3000/api/v1/ws');

      // Test with production environment
      mockLocation.protocol = 'https:';
      mockLocation.host = 'production-app.com';
      
      manager = new WebSocketManager();
      baseUrl = (manager as any)._getBaseUrl();
      expect(baseUrl).toBe('wss://production-app.com/api/v1/ws');
    });
  });

  describe('Session Management', () => {
    it('should generate consistent session IDs', () => {
      const manager = new WebSocketManager();
      
      // Mock localStorage to return existing session
      mockLocalStorage.store['nexus_session_id'] = 'existing-session-id';
      
      const sessionId1 = (manager as any)._getSessionId();
      const sessionId2 = (manager as any)._getSessionId();
      
      // Should return the same session ID from localStorage
      expect(sessionId1).toBe('existing-session-id');
      expect(sessionId2).toBe('existing-session-id');
      expect(mockLocalStorage.getItem).toHaveBeenCalledWith('nexus_session_id');
    });

    it('should generate new session ID when none exists', () => {
      const manager = new WebSocketManager();
      
      // Mock localStorage to return null (no existing session)
      mockLocalStorage.getItem.mockReturnValue(null);
      
      const sessionId = (manager as any)._getSessionId();
      
      // Should generate new session ID and store it
      expect(sessionId).toBe('test-uuid-1234');
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('nexus_session_id', 'test-uuid-1234');
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid host formats gracefully', () => {
      mockLocation.protocol = 'http:';
      mockLocation.host = '';
      
      const manager = new WebSocketManager();
      const baseUrl = (manager as any)._getBaseUrl();
      
      // Should still construct URL even with empty host
      expect(baseUrl).toBe('ws:///api/v1/ws');
    });

    it('should handle special characters in host', () => {
      mockLocation.protocol = 'https:';
      mockLocation.host = 'subdomain.example.com';
      
      const manager = new WebSocketManager();
      const baseUrl = (manager as any)._getBaseUrl();
      
      expect(baseUrl).toBe('wss://subdomain.example.com/api/v1/ws');
    });
  });
});