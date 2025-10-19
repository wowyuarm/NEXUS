/**
 * IdentityPanel Component Tests
 * 
 * Tests for the refactored identity management panel
 * Coverage: state machine, fixed height, grayscale design, user interactions
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IdentityPanel } from '../IdentityPanel';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('@/features/chat/store/chatStore', () => ({
  useChatStore: Object.assign(
    vi.fn((selector) => {
      const state = {
        visitorMode: false,
        messages: [],
      };
      return selector ? selector(state) : state;
    }),
    {
      setState: vi.fn(),
      getState: vi.fn(() => ({ visitorMode: false, messages: [] }))
    }
  )
}));

vi.mock('@/stores/uiStore', () => ({
  useUIStore: vi.fn((selector) => {
    const state = { closeModal: vi.fn() };
    return selector ? selector(state) : state;
  })
}));

vi.mock('@/services/identity/identity', () => ({
  IdentityService: {
    getIdentity: vi.fn().mockResolvedValue({
      privateKey: '0x1234...',
      publicKey: '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266'
    }),
    signCommand: vi.fn().mockResolvedValue({
      publicKey: '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266',
      signature: '0xabcd...'
    }),
    exportMnemonic: vi.fn().mockReturnValue('test test test test test test test test test test test junk'),
    importFromMnemonic: vi.fn().mockResolvedValue('0xNewPublicKey'),
    hasIdentity: vi.fn().mockReturnValue(false),
    clearIdentity: vi.fn()
  }
}));

vi.mock('@/services/websocket/manager', () => ({
  websocketManager: {
    sendCommand: vi.fn(),
    reconnect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn()
  }
}));

// ============================================================================
// Tests
// ============================================================================

describe('IdentityPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Layout & Design Standards', () => {
    it('should have fixed height of 360px', () => {
      const { container } = render(<IdentityPanel />);
      const fixedHeightDiv = container.querySelector('[class*="h-[360px]"]') || 
                             container.querySelector('[class*="h-\\[360px\\]"]');
      expect(fixedHeightDiv).toBeTruthy();
    });

    it('should use grayscale design (no red warnings)', async () => {
      render(<IdentityPanel />);

      await waitFor(() => {
        expect(screen.getByText(/清除当前身份/i)).toBeInTheDocument();
      });

      const clearButton = screen.getByText(/清除当前身份/i);
      expect(clearButton.className).not.toMatch(/red-/);
    });
  });

  describe('Member Mode - Main View', () => {
    it('should display public key', async () => {
      render(<IdentityPanel />);

      await waitFor(() => {
        expect(screen.getByText(/存在地址/i)).toBeInTheDocument();
        expect(screen.getByText(/0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266/)).toBeInTheDocument();
      });
    });

    it('should display help button', () => {
      render(<IdentityPanel />);
      const helpButton = screen.getByLabelText(/身份系统说明/i);
      expect(helpButton).toBeInTheDocument();
    });

    it('should display three action buttons', async () => {
      render(<IdentityPanel />);

      await waitFor(() => {
        expect(screen.getByText(/备份身份/i)).toBeInTheDocument();
      });
      
      expect(screen.getByText(/切换身份/i)).toBeInTheDocument();
      expect(screen.getByText(/清除当前身份/i)).toBeInTheDocument();
    });
  });

  describe('Mode Switching', () => {
    it('should navigate to help mode', async () => {
      const user = userEvent.setup();
      render(<IdentityPanel />);

      const helpButton = screen.getByLabelText(/身份系统说明/i);
      await user.click(helpButton);

      await waitFor(() => {
        expect(screen.getByText(/关于身份系统/i)).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    it('should navigate to import mode', async () => {
      const user = userEvent.setup();
      render(<IdentityPanel />);

      const switchButton = await screen.findByText(/切换身份/i);
      await user.click(switchButton);

      await waitFor(() => {
        expect(screen.getByText(/导入身份/i)).toBeInTheDocument();
      }, { timeout: 2000 });
    });
  });

  describe('Import Functionality', () => {
    it('should enable confirm button when mnemonic is entered', async () => {
      const user = userEvent.setup();
      render(<IdentityPanel />);

      const switchButton = await screen.findByText(/切换身份/i);
      await user.click(switchButton);

      const textarea = await screen.findByPlaceholderText(/请输入助记词/i);
      await user.type(textarea, 'test mnemonic');

      await waitFor(() => {
        const confirmButton = screen.getByText(/确认导入/i);
        expect(confirmButton).not.toBeDisabled();
      }, { timeout: 2000 });
    });
  });

  describe('Export Functionality', () => {
    it('should auto-export mnemonic when entering export mode', async () => {
      const user = userEvent.setup();
      const { IdentityService } = await import('@/services/identity/identity');
      
      render(<IdentityPanel />);

      await waitFor(() => {
        expect(screen.getByText(/备份身份/i)).toBeInTheDocument();
      });

      const backupButton = screen.getByText(/备份身份/i);
      await user.click(backupButton);

      await waitFor(() => {
        expect(IdentityService.exportMnemonic).toHaveBeenCalled();
      }, { timeout: 2000 });
    });

    it('should toggle mnemonic visibility', async () => {
      const user = userEvent.setup();
      render(<IdentityPanel />);

      await waitFor(() => {
        expect(screen.getByText(/备份身份/i)).toBeInTheDocument();
      });

      const backupButton = screen.getByText(/备份身份/i);
      await user.click(backupButton);

      // Wait for mnemonic to appear
      await waitFor(() => {
        expect(screen.getByText(/test test test/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      // Click eye icon to hide
      const eyeButton = screen.getByLabelText(/隐藏助记词/i);
      await user.click(eyeButton);

      await waitFor(() => {
        expect(screen.queryByText(/test test test test test test test test test test test junk/i)).not.toBeInTheDocument();
      }, { timeout: 2000 });
    });
  });

  describe('Visitor Mode', () => {
    beforeEach(async () => {
      const chatStoreModule = await import('@/features/chat/store/chatStore');
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      vi.mocked(chatStoreModule.useChatStore).mockImplementation((selector?: any) => {
        const state = {
          visitorMode: true,
          messages: [],
        };
        return selector ? selector(state) : state;
      });
    });

    it('should display visitor prompt', () => {
      render(<IdentityPanel />);
      expect(screen.getByText(/访客身份/i)).toBeInTheDocument();
    });

    it('should display create and import buttons', () => {
      render(<IdentityPanel />);
      expect(screen.getByText(/创建新身份/i)).toBeInTheDocument();
      expect(screen.getByText(/导入已有身份/i)).toBeInTheDocument();
    });

    it('should display help button', () => {
      render(<IdentityPanel />);
      const helpButton = screen.getByLabelText(/身份系统说明/i);
      expect(helpButton).toBeInTheDocument();
    });
  });

  describe('Reset Functionality', () => {
    beforeEach(async () => {
      // Reset to member mode
      const chatStoreModule = await import('@/features/chat/store/chatStore');
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      vi.mocked(chatStoreModule.useChatStore).mockImplementation((selector?: any) => {
        const state = {
          visitorMode: false,
          messages: [],
        };
        return selector ? selector(state) : state;
      });
    });

    it('should show confirmation dialog', async () => {
      const user = userEvent.setup();
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
      
      render(<IdentityPanel />);

      await waitFor(() => {
        expect(screen.getByText(/清除当前身份/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      const clearButton = screen.getByText(/清除当前身份/i);
      await user.click(clearButton);

      // Should show reset mode
      await waitFor(() => {
        expect(screen.getByText(/确认清除/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      const confirmButton = screen.getByText(/确认清除/i);
      await user.click(confirmButton);

      expect(confirmSpy).toHaveBeenCalled();
      confirmSpy.mockRestore();
    });
  });
});

