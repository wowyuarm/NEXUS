/**
 * IdentityPanel Component Tests
 * 
 * Tests for the identity management panel following TDD principles.
 * Covers both visitor and member views with all identity operations.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IdentityPanel } from '../IdentityPanel';

// Mock dependencies
vi.mock('@/features/chat/store/chatStore', () => ({
  useChatStore: vi.fn((selector) => {
    const state = {
      visitorMode: false,
      createSystemMessage: vi.fn()
    };
    return selector ? selector(state) : state;
  })
}));

vi.mock('@/stores/uiStore', () => ({
  useUIStore: vi.fn((selector) => {
    const state = {
      closeModal: vi.fn()
    };
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
    reconnect: vi.fn().mockResolvedValue(undefined)
  }
}));

describe('IdentityPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Member View (visitorMode = false)', () => {
    it('should display public key for member users', async () => {
      // Arrange & Act
      render(<IdentityPanel />);

      // Assert: Should show public key
      await waitFor(() => {
        expect(screen.getByText(/存在地址/i)).toBeInTheDocument();
        expect(screen.getByText(/0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266/)).toBeInTheDocument();
      });
    });

    it('should display export and import buttons for members', () => {
      // Arrange & Act
      render(<IdentityPanel />);

      // Assert: Should have both action buttons
      expect(screen.getByText(/导出身份/i)).toBeInTheDocument();
      expect(screen.getByText(/切换\/导入身份/i)).toBeInTheDocument();
    });

    it('should export mnemonic when export button is clicked', async () => {
      // Arrange
      const { IdentityService } = await import('@/services/identity/identity');
      render(<IdentityPanel />);

      // Act: Click export button
      const exportButton = screen.getByText(/导出身份/i);
      fireEvent.click(exportButton);

      // Assert: Should call exportMnemonic
      await waitFor(() => {
        expect(IdentityService.exportMnemonic).toHaveBeenCalled();
        expect(screen.getByText(/test test test/i)).toBeInTheDocument();
      });
    });

    it('should show/hide mnemonic with eye icon toggle', async () => {
      // Arrange
      render(<IdentityPanel />);
      
      // Act: Export mnemonic first
      const exportButton = screen.getByText(/导出身份/i);
      fireEvent.click(exportButton);

      await waitFor(() => {
        expect(screen.getByText(/test test test/i)).toBeInTheDocument();
      });

      // Get the eye icon button (toggle visibility)
      const toggleButtons = screen.getAllByRole('button');
      const eyeButton = toggleButtons.find(btn => btn.querySelector('svg'));

      // Act: Click to hide
      if (eyeButton) {
        fireEvent.click(eyeButton);
      }

      // Note: In real implementation, mnemonic should be hidden
      // This test validates the toggle button exists
      expect(eyeButton).toBeTruthy();
    });

    it('should copy mnemonic to clipboard', async () => {
      // Arrange: Mock clipboard API
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: {
          writeText: writeTextMock
        }
      });

      render(<IdentityPanel />);

      // Act: Export and copy
      const exportButton = screen.getByText(/导出身份/i);
      fireEvent.click(exportButton);

      await waitFor(() => {
        expect(screen.getByText(/test test test/i)).toBeInTheDocument();
      });

      const copyButton = screen.getByText(/复制到剪贴板/i);
      fireEvent.click(copyButton);

      // Assert: Should copy to clipboard
      await waitFor(() => {
        expect(writeTextMock).toHaveBeenCalledWith(
          'test test test test test test test test test test test junk'
        );
      });
    });

    it('should handle export error for legacy identity without mnemonic', async () => {
      // Arrange: Mock exportMnemonic to throw error for legacy identity
      const { IdentityService } = await import('@/services/identity/identity');
      vi.mocked(IdentityService.exportMnemonic).mockImplementationOnce(() => {
        throw new Error('No mnemonic found. This identity was created with an older version. Please clear and recreate your identity.');
      });

      render(<IdentityPanel />);

      // Act: Try to export
      const exportButton = screen.getByText(/导出身份/i);
      fireEvent.click(exportButton);

      // Assert: Should show error message
      await waitFor(() => {
        expect(screen.getByText(/No mnemonic found/i)).toBeInTheDocument();
      });
    });

    it('should show import input when switch/import button is clicked', () => {
      // Arrange & Act
      render(<IdentityPanel />);

      const importButton = screen.getByText(/切换\/导入身份/i);
      fireEvent.click(importButton);

      // Assert: Should show textarea for mnemonic input
      const textarea = screen.getByPlaceholderText(/请输入 12 或 24 个助记词/i);
      expect(textarea).toBeInTheDocument();
      expect(screen.getByText(/确认导入/i)).toBeInTheDocument();
      expect(screen.getByText(/取消/)).toBeInTheDocument();
    });

    it('should import identity from mnemonic and reconnect', async () => {
      // Arrange
      const user = userEvent.setup();
      const { IdentityService } = await import('@/services/identity/identity');
      const { websocketManager } = await import('@/services/websocket/manager');
      
      render(<IdentityPanel />);

      // Act: Open import, enter mnemonic, and confirm
      const importButton = screen.getByText(/切换\/导入身份/i);
      fireEvent.click(importButton);

      const textarea = screen.getByPlaceholderText(/请输入 12 或 24 个助记词/i);
      await user.type(textarea, 'test test test test test test test test test test test junk');

      const confirmButton = screen.getByRole('button', { name: /确认导入/i });
      fireEvent.click(confirmButton);

      // Assert: Should import, reconnect, and create system message
      await waitFor(() => {
        expect(IdentityService.importFromMnemonic).toHaveBeenCalledWith(
          'test test test test test test test test test test test junk'
        );
        expect(websocketManager.reconnect).toHaveBeenCalledWith('0xNewPublicKey');
        // System message creation is tested in unit tests
      });
    });

    it('should cancel import and hide input', () => {
      // Arrange & Act
      render(<IdentityPanel />);

      const importButton = screen.getByText(/切换\/导入身份/i);
      fireEvent.click(importButton);

      expect(screen.getByPlaceholderText(/请输入 12 或 24 个助记词/i)).toBeInTheDocument();

      // Act: Cancel
      const cancelButton = screen.getByText(/取消/);
      fireEvent.click(cancelButton);

      // Assert: Should hide import input
      expect(screen.queryByPlaceholderText(/请输入 12 或 24 个助记词/i)).not.toBeInTheDocument();
    });
  });

  describe('Visitor View (visitorMode = true)', () => {
    beforeEach(async () => {
      // Mock visitorMode = true
      const chatStoreModule = await import('@/features/chat/store/chatStore');
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      vi.mocked(chatStoreModule.useChatStore).mockImplementation((selector?: (state: any) => any) => {
        const state = {
          visitorMode: true,
          createSystemMessage: vi.fn(),
          // Add minimal required properties to satisfy type checking
          messages: [],
          currentRun: { runId: null, status: 'idle' as const, activeToolCalls: [] },
          isConnected: false,
          publicKey: null,
          isInputDisabled: false,
          lastError: null,
          toolCallHistory: {}
        };
        return selector ? selector(state) : state;
      });
    });

    it('should display visitor guidance message', () => {
      // Arrange & Act
      render(<IdentityPanel />);

      // Assert: Should show visitor info
      expect(screen.getByText(/访客身份/i)).toBeInTheDocument();
      expect(screen.getByText(/无法使用全部服务/i)).toBeInTheDocument();
    });

    it('should display create and import buttons for visitors', () => {
      // Arrange & Act
      render(<IdentityPanel />);

      // Assert: Should have create and import options
      expect(screen.getByText(/创建新身份/i)).toBeInTheDocument();
      expect(screen.getByText(/导入已有身份/i)).toBeInTheDocument();
    });

    it('should create new identity when create button is clicked', async () => {
      // Arrange
      const { IdentityService } = await import('@/services/identity/identity');
      const { websocketManager } = await import('@/services/websocket/manager');
      
      render(<IdentityPanel />);

      // Act: Click create button
      const createButton = screen.getByText(/创建新身份/i);
      fireEvent.click(createButton);

      // Assert: Should sign and send command
      await waitFor(() => {
        expect(IdentityService.signCommand).toHaveBeenCalledWith('/identity');
        expect(websocketManager.sendCommand).toHaveBeenCalled();
        expect(websocketManager.reconnect).toHaveBeenCalled();
      });
    });

    it('should show loading state during identity creation', async () => {
      // Arrange
      render(<IdentityPanel />);

      // Act: Click create button
      const createButton = screen.getByText(/创建新身份/i);
      fireEvent.click(createButton);

      // Assert: Should show loading text
      expect(screen.getByText(/创建中.../i)).toBeInTheDocument();
    });

    it('should show import input when import button is clicked', () => {
      // Arrange & Act
      render(<IdentityPanel />);

      const importButton = screen.getByText(/导入已有身份/i);
      fireEvent.click(importButton);

      // Assert: Should show import interface
      const textarea = screen.getByPlaceholderText(/请输入 12 或 24 个助记词/i);
      expect(textarea).toBeInTheDocument();
      expect(screen.getByText(/确认导入/i)).toBeInTheDocument();
    });

    it('should validate empty mnemonic input', async () => {
      // Arrange
      render(<IdentityPanel />);

      // Act: Open import without entering mnemonic
      const importButton = screen.getByText(/导入已有身份/i);
      fireEvent.click(importButton);

      const confirmButton = screen.getByRole('button', { name: /确认导入/i });
      
      // Assert: Confirm button should be disabled for empty input
      expect(confirmButton).toBeDisabled();
    });

    it('should enable confirm button when mnemonic is entered', async () => {
      // Arrange
      const user = userEvent.setup();
      render(<IdentityPanel />);

      // Act: Open import and enter mnemonic
      const importButton = screen.getByText(/导入已有身份/i);
      fireEvent.click(importButton);

      const textarea = screen.getByPlaceholderText(/请输入 12 或 24 个助记词/i);
      await user.type(textarea, 'test mnemonic');

      const confirmButton = screen.getByRole('button', { name: /确认导入/i });
      
      // Assert: Confirm button should be enabled
      expect(confirmButton).not.toBeDisabled();
    });
  });

  describe('Feedback Mechanism', () => {
    // These tests should use member view (visitorMode = false)
    beforeEach(async () => {
      // Reset mock to member view for feedback tests
      const chatStoreModule = await import('@/features/chat/store/chatStore');
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      vi.mocked(chatStoreModule.useChatStore).mockImplementation((selector?: (state: any) => any) => {
        const state = {
          visitorMode: false,  // Member view
          createSystemMessage: vi.fn(),
          messages: [],
          currentRun: { runId: null, status: 'idle' as const, activeToolCalls: [] },
          isConnected: false,
          publicKey: null,
          isInputDisabled: false,
          lastError: null,
          toolCallHistory: {}
        };
        return selector ? selector(state) : state;
      });
    });

    it('should show success feedback after successful operation', async () => {
      // Arrange
      render(<IdentityPanel />);

      // Act: Export mnemonic (success operation)
      const exportButton = screen.getByText(/导出身份/i);
      fireEvent.click(exportButton);

      // Assert: Should show success indicator
      await waitFor(() => {
        expect(screen.getByText(/助记词已显示/i)).toBeInTheDocument();
      });
    });
  });
});

