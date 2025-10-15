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
        // Generate new identity with mnemonic support
        const wallet = Wallet.createRandom();

        // Persist private key to localStorage
        localStorage.setItem(STORAGE_KEY, wallet.privateKey);

        return {
          privateKey: wallet.privateKey,
          publicKey: wallet.address
        };
      }
    } catch (error) {
      // Handle storage errors gracefully by generating new identity with mnemonic
      console.warn('Storage error, generating new identity:', error);
      const wallet = Wallet.createRandom();

      try {
        localStorage.setItem(STORAGE_KEY, wallet.privateKey);
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
  },

  /**
   * Export mnemonic phrase for identity backup
   * Returns the 12 or 24 word mnemonic phrase if the identity was created with one.
   * For legacy identities created without mnemonic, returns null.
   * 
   * @returns Mnemonic phrase or null if identity doesn't have one
   * @throws Error if no identity exists in storage
   */
  exportMnemonic(): string | null {
    try {
      const privateKey = localStorage.getItem(STORAGE_KEY);
      
      if (!privateKey) {
        throw new Error('No identity found. Please create an identity first.');
      }

      // Create wallet instance from private key
      const wallet = new Wallet(privateKey);
      
      // Check if wallet is an HDNodeWallet (has mnemonic)
      // Only wallets created with Wallet.createRandom() or Wallet.fromPhrase() have mnemonics
      if ('mnemonic' in wallet && wallet.mnemonic && typeof wallet.mnemonic === 'object' && 'phrase' in wallet.mnemonic) {
        return (wallet.mnemonic as { phrase: string }).phrase;
      }
      
      // Return null for legacy identities without mnemonic
      return null;
    } catch (error) {
      console.error('Failed to export mnemonic:', error);
      throw error;
    }
  },

  /**
   * Import identity from mnemonic phrase
   * Validates the mnemonic and overwrites the current identity.
   * This enables identity restoration and cross-device identity portability.
   * 
   * @param mnemonic - 12 or 24 word mnemonic phrase
   * @returns The public key (address) of the imported identity
   * @throws Error if mnemonic is invalid
   */
  async importFromMnemonic(mnemonic: string): Promise<string> {
    try {
      // Validate and create wallet from mnemonic
      // This will throw if mnemonic is invalid
      const wallet = Wallet.fromPhrase(mnemonic.trim());
      
      // Overwrite existing identity with new one
      localStorage.setItem(STORAGE_KEY, wallet.privateKey);
      
      console.log('✅ Identity imported successfully:', wallet.address);
      
      return wallet.address;
    } catch (error) {
      console.error('Failed to import identity from mnemonic:', error);
      throw new Error('Invalid mnemonic phrase. Please check and try again.');
    }
  }
};