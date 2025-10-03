import { Wallet, keccak256, toUtf8Bytes } from 'ethers';

export interface Identity {
  privateKey: string;
  publicKey: string;
}

export interface CommandAuth {
  publicKey: string;
  signature: string;
}

const STORAGE_KEY = 'nexus_private_key';

// Helper function to generate a random private key that works in both browser and Node.js
async function generatePrivateKey(): Promise<string> {
  // Generate 32 random bytes (256 bits) for private key
  const randomBytes = new Uint8Array(32);

  if (typeof window !== 'undefined' && window.crypto) {
    // Browser environment
    window.crypto.getRandomValues(randomBytes);
  } else {
    // Node.js environment - use dynamic import instead of require
    const crypto = await import('crypto');
    crypto.randomFillSync(randomBytes);
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
  async getIdentity(): Promise<Identity> {
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
        const privateKey = await generatePrivateKey();
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
      const privateKey = await generatePrivateKey();
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
  },

  /**
   * Sign a command string using the stored private key
   * This creates a cryptographic signature proving ownership of the identity
   * 
   * IMPORTANT: This uses raw keccak256 hashing without Ethereum's message prefix
   * to match the backend verification logic.
   * 
   * @param command - The command string to sign (e.g., "/identity")
   * @returns Auth object containing publicKey and signature
   * @throws Error if no identity exists in storage
   */
  async signCommand(command: string): Promise<CommandAuth> {
    try {
      // Get the stored private key
      const privateKey = localStorage.getItem(STORAGE_KEY);
      
      if (!privateKey) {
        throw new Error('No identity found. Cannot sign command without a private key.');
      }

      // Create wallet instance from private key
      const wallet = new Wallet(privateKey);

      // Hash the command using keccak256 (same as backend)
      // This is a RAW hash without Ethereum's "\x19Ethereum Signed Message:\n" prefix
      const messageHash = keccak256(toUtf8Bytes(command));

      // Sign the message hash directly using the signing key
      // We use signingKey.sign() instead of signMessage() to avoid the Ethereum prefix
      const signature = wallet.signingKey.sign(messageHash);

      return {
        publicKey: wallet.address,
        signature: signature.serialized  // Get the serialized signature in hex format
      };
    } catch (error) {
      console.error('Failed to sign command:', error);
      throw error;
    }
  }
};