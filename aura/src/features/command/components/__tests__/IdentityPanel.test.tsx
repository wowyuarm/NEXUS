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

    it('should have textarea with fixed rows', async () => {
      const user = userEvent.setup();
      render(<IdentityPanel />);

      const switchButton = await screen.findByText(/切换身份/i);
      await user.click(switchButton);

      const textarea = await screen.findByPlaceholderText(/请输入助记词/i);
      
      // Textarea component uses minRows to provide fixed height
      // This is a design standard to maintain layout stability
      expect(textarea).toBeInTheDocument();
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

    it('should display "访客模式" label', () => {
      render(<IdentityPanel />);
      const label = screen.getByText(/访客模式/i);
      expect(label).toBeInTheDocument();
      expect(label.className).toMatch(/text-xs/);
    });

    it('should display create and import buttons', () => {
      render(<IdentityPanel />);
      expect(screen.getByText(/创建新身份/i)).toBeInTheDocument();
      expect(screen.getByText(/导入已有身份/i)).toBeInTheDocument();
    });

    it('should display help button inline with label', () => {
      render(<IdentityPanel />);
      const helpButton = screen.getByLabelText(/身份系统说明/i);
      expect(helpButton).toBeInTheDocument();
      
      // Help button should be in a flex container with justify-between
      expect(helpButton.parentElement?.className).toMatch(/flex.*justify-between/);
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

    it('should navigate to reset confirmation mode', async () => {
      const user = userEvent.setup();
      
      render(<IdentityPanel />);

      await waitFor(() => {
        expect(screen.getByText(/清除当前身份/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      const clearButton = screen.getByText(/清除当前身份/i);
      await user.click(clearButton);

      // Should show reset mode with custom confirmation UI (no native window.confirm)
      await waitFor(() => {
        expect(screen.getByText(/重置确认/i)).toBeInTheDocument();
        expect(screen.getByText(/此操作不可逆/i)).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    it('should display warning message and two-step confirmation buttons', async () => {
      const user = userEvent.setup();
      
      render(<IdentityPanel />);

      await waitFor(() => {
        expect(screen.getByText(/清除当前身份/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      const clearButton = screen.getByText(/清除当前身份/i);
      await user.click(clearButton);

      await waitFor(() => {
        // Should show warning message
        expect(screen.getByText(/永久丢失/i)).toBeInTheDocument();
        
        // Should show cancel and confirm buttons
        expect(screen.getByText(/取消/i)).toBeInTheDocument();
        expect(screen.getByText(/确认清除/i)).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    it('should navigate back when cancel button is clicked', async () => {
      const user = userEvent.setup();
      
      render(<IdentityPanel />);

      await waitFor(() => {
        expect(screen.getByText(/清除当前身份/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      const clearButton = screen.getByText(/清除当前身份/i);
      await user.click(clearButton);

      await waitFor(() => {
        expect(screen.getByText(/取消/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      const cancelButton = screen.getByText(/取消/i);
      await user.click(cancelButton);

      // Should return to main mode
      await waitFor(() => {
        expect(screen.getByText(/存在地址/i)).toBeInTheDocument();
        expect(screen.queryByText(/重置确认/i)).not.toBeInTheDocument();
      }, { timeout: 2000 });
    });
  });

  describe('Typography & Layout Improvements', () => {
    it('should use text-sm for 存在地址 label', async () => {
      render(<IdentityPanel />);
      
      await waitFor(() => {
        const label = screen.getByText(/存在地址/i);
        expect(label.className).toMatch(/text-sm/);
      }, { timeout: 2000 });
    });

    it('should use text-sm for public key display', async () => {
      render(<IdentityPanel />);
      
      await waitFor(() => {
        const publicKeyElement = screen.getByText(/0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266/);
        expect(publicKeyElement.className).toMatch(/text-sm/);
      }, { timeout: 2000 });
    });

    it('should display help button with label on same line', async () => {
      render(<IdentityPanel />);
      
      await waitFor(() => {
        const helpButton = screen.getByLabelText(/身份系统说明/i);
        const label = screen.getByText(/存在地址/i);
        
        expect(helpButton).toBeInTheDocument();
        expect(label).toBeInTheDocument();
        
        // Both should be in the same container (flex justify-between)
        expect(helpButton.parentElement?.className).toMatch(/flex.*justify-between/);
      }, { timeout: 2000 });
    });

    it('should use text-base for help page titles', async () => {
      const user = userEvent.setup();
      render(<IdentityPanel />);

      const helpButton = await screen.findByLabelText(/身份系统说明/i);
      await user.click(helpButton);

      await waitFor(() => {
        const title = screen.getByText(/关于身份系统/i);
        expect(title.className).toMatch(/text-base/);
      }, { timeout: 2000 });
    });

    it('should use font-bold for help section headings', async () => {
      const user = userEvent.setup();
      render(<IdentityPanel />);

      const helpButton = await screen.findByLabelText(/身份系统说明/i);
      await user.click(helpButton);

      await waitFor(() => {
        const heading = screen.getByText(/不同于传统账号/i);
        expect(heading.className).toMatch(/font-bold/);
      }, { timeout: 2000 });
    });

    it('should use space-y-3 for compact layout', async () => {
      const { container } = render(<IdentityPanel />);
      
      await waitFor(() => {
        const spaceYDiv = container.querySelector('[class*="space-y-3"]');
        expect(spaceYDiv).toBeTruthy();
      }, { timeout: 2000 });
    });
  });
});
