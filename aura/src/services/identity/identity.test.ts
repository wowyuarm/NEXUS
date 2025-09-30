import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock window.crypto for testing
Object.defineProperty(window, 'crypto', {
  value: {
    getRandomValues: (arr: Uint8Array) => {
      for (let i = 0; i < arr.length; i++) {
        arr[i] = Math.floor(Math.random() * 256);
      }
      return arr;
    }
  },
  writable: true
});

describe('IdentityService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getIdentity', () => {
    it('should generate and save a new identity if none exists in storage', async () => {
      // Arrange: localStorage returns null (no existing identity)
      localStorageMock.getItem.mockReturnValue(null);

      // Act & Assert: This should fail because IdentityService doesn't exist yet
      const { IdentityService } = await import('./identity');
      const identity = await IdentityService.getIdentity();

      // Assert: Should have generated new identity
      expect(identity).toBeDefined();
      expect(identity.privateKey).toBeDefined();
      expect(identity.publicKey).toBeDefined();
      expect(identity.publicKey).toMatch(/^0x[a-fA-F0-9]{40}$/); // Ethereum address format

      // Assert: Should have saved to localStorage
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'nexus_private_key',
        identity.privateKey
      );
    });

    it('should load an existing identity from storage', async () => {
      // Arrange: localStorage has existing private key
      const existingPrivateKey = '0x1234567890123456789012345678901234567890123456789012345678901234';
      localStorageMock.getItem.mockReturnValue(existingPrivateKey);

      // Act & Assert: This should fail because IdentityService doesn't exist yet
      const { IdentityService } = await import('./identity');
      const identity = await IdentityService.getIdentity();

      // Assert: Should have loaded existing identity
      expect(identity).toBeDefined();
      expect(identity.privateKey).toBe(existingPrivateKey);
      expect(identity.publicKey).toBeDefined();

      // Assert: Should not have called setItem (no new generation)
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });

    it('should derive the correct public key from a private key', async () => {
      // Arrange: Use a known test private key (this should generate a consistent public key)
      const testPrivateKey = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80';
      localStorageMock.getItem.mockReturnValue(testPrivateKey);

      // Act: Get identity
      const { IdentityService } = await import('./identity');
      const identity = await IdentityService.getIdentity();

      // Assert: Public key should be derived consistently
      expect(identity.publicKey).toBe('0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266'); // Known address for this private key
    });

    it('should handle storage errors gracefully', async () => {
      // Arrange: localStorage throws an error
      localStorageMock.getItem.mockImplementation(() => {
        throw new Error('Storage error');
      });

      // Act & Assert: This should fail because IdentityService doesn't exist yet
      const { IdentityService } = await import('./identity');

      // Assert: Should not throw, should fallback to generating new identity
      const identity = await IdentityService.getIdentity();
      expect(identity).toBeDefined();
      expect(identity.privateKey).toBeDefined();
      expect(identity.publicKey).toBeDefined();
    });
  });
});