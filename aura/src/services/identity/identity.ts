import { Wallet } from 'ethers';

export interface Identity {
  privateKey: string;
  publicKey: string;
}

const STORAGE_KEY = 'nexus_private_key';

// Helper function to generate a random private key that works in both browser and Node.js
function generatePrivateKey(): string {
  // Generate 32 random bytes (256 bits) for private key
  const randomBytes = new Uint8Array(32);

  if (typeof window !== 'undefined' && window.crypto) {
    // Browser environment
    window.crypto.getRandomValues(randomBytes);
  } else if (typeof require !== 'undefined') {
    // Node.js environment
    const crypto = require('crypto');
    crypto.randomFillSync(randomBytes);
  } else {
    throw new Error('No crypto API available');
  }

  // Convert to hex string and add 0x prefix
  return '0x' + Array.from(randomBytes)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

export const IdentityService = {
  /**
   * Get or create user identity
   * Returns existing identity from localStorage or generates new one
   */
  getIdentity(): Identity {
    try {
      // Try to get existing private key from localStorage
      const existingPrivateKey = localStorage.getItem(STORAGE_KEY);

      if (existingPrivateKey) {
        // Load existing identity
        const wallet = new Wallet(existingPrivateKey);
        return {
          privateKey: wallet.privateKey,
          publicKey: wallet.address
        };
      } else {
        // Generate new identity
        const privateKey = generatePrivateKey();
        const wallet = new Wallet(privateKey);

        // Persist private key to localStorage
        localStorage.setItem(STORAGE_KEY, privateKey);

        return {
          privateKey: wallet.privateKey,
          publicKey: wallet.address
        };
      }
    } catch (error) {
      // Handle storage errors gracefully by generating new identity
      console.warn('Storage error, generating new identity:', error);
      const privateKey = generatePrivateKey();
      const wallet = new Wallet(privateKey);

      try {
        localStorage.setItem(STORAGE_KEY, privateKey);
      } catch (fallbackError) {
        console.warn('Failed to persist identity to localStorage:', fallbackError);
      }

      return {
        privateKey: wallet.privateKey,
        publicKey: wallet.address
      };
    }
  },

  /**
   * Clear stored identity (for testing or logout)
   */
  clearIdentity(): void {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.warn('Failed to clear identity from localStorage:', error);
    }
  },

  /**
   * Check if identity exists in storage
   */
  hasIdentity(): boolean {
    try {
      return localStorage.getItem(STORAGE_KEY) !== null;
    } catch (error) {
      console.warn('Failed to check identity in localStorage:', error);
      return false;
    }
  }
};