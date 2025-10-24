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
const MNEMONIC_KEY = 'nexus_mnemonic';

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

        // Persist both private key AND mnemonic to localStorage
        // This is critical: storing only privateKey loses the mnemonic forever!
        localStorage.setItem(STORAGE_KEY, wallet.privateKey);
        
        // Save mnemonic phrase separately for backup/export
        if (wallet.mnemonic && typeof wallet.mnemonic === 'object' && 'phrase' in wallet.mnemonic) {
          localStorage.setItem(MNEMONIC_KEY, (wallet.mnemonic as { phrase: string }).phrase);
          console.log('✅ Mnemonic saved to localStorage');
        }

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
        // Also save mnemonic in error fallback
        if (wallet.mnemonic && typeof wallet.mnemonic === 'object' && 'phrase' in wallet.mnemonic) {
          localStorage.setItem(MNEMONIC_KEY, (wallet.mnemonic as { phrase: string }).phrase);
        }
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
   * Removes both private key and mnemonic from localStorage
   */
  clearIdentity(): void {
    try {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(MNEMONIC_KEY);
      console.log('🧹 Identity cleared (private key and mnemonic)');
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
   * Sign arbitrary data (for REST API requests)
   * 
   * @param data - String data to sign (should be pre-serialized if object)
   * @returns Auth object containing publicKey and signature
   */
  async signData(data: string): Promise<CommandAuth> {
    try {
      // Get the stored private key
      const privateKey = localStorage.getItem(STORAGE_KEY);
      
      if (!privateKey) {
        throw new Error('No identity found. Cannot sign data without a private key.');
      }

      // Create wallet instance from private key
      const wallet = new Wallet(privateKey);

      // Hash the data using keccak256
      const messageHash = keccak256(toUtf8Bytes(data));

      // Sign the message hash directly using the signing key
      const signature = wallet.signingKey.sign(messageHash);

      return {
        publicKey: wallet.address,
        signature: signature.serialized
      };
    } catch (error) {
      console.error('Failed to sign data:', error);
      throw error;
    }
  },

  /**
   * Export mnemonic phrase for identity backup
   * Returns the 12 or 24 word mnemonic phrase.
   * 
   * IMPORTANT: This reads directly from localStorage, not from wallet.mnemonic,
   * because wallets created with new Wallet(privateKey) lose their mnemonic.
   * 
   * All identities created after v0.2.0 will have mnemonics.
   * 
   * @returns Mnemonic phrase
   * @throws Error if no identity or mnemonic exists in storage
   */
  exportMnemonic(): string {
    try {
      const privateKey = localStorage.getItem(STORAGE_KEY);
      
      if (!privateKey) {
        throw new Error('No identity found. Please create an identity first.');
      }

      // Read mnemonic directly from localStorage
      const mnemonic = localStorage.getItem(MNEMONIC_KEY);
      
      if (!mnemonic) {
        throw new Error('No mnemonic found. This identity was created with an older version. Please clear and recreate your identity.');
      }
      
      console.log('✅ Mnemonic exported successfully');
      return mnemonic;
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
   * IMPORTANT: Saves both private key AND mnemonic to localStorage.
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
      // Save BOTH private key and mnemonic
      localStorage.setItem(STORAGE_KEY, wallet.privateKey);
      localStorage.setItem(MNEMONIC_KEY, mnemonic.trim());
      
      console.log('✅ Identity imported successfully:', wallet.address);
      console.log('✅ Mnemonic saved to localStorage');
      
      return wallet.address;
    } catch (error) {
      console.error('Failed to import identity from mnemonic:', error);
      throw new Error('Invalid mnemonic phrase. Please check and try again.');
    }
  }
};