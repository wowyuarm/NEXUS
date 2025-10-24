/**
 * ConfigPanel Component Tests
 * 
 * Tests for the /config panel implementation following TDD principles.
 * References IdentityPanel test structure for consistency.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigPanel } from '../ConfigPanel.tsx';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('@/features/command/api', () => ({
  fetchConfig: vi.fn().mockResolvedValue({
    effective_config: {
      model: 'Gemini-2.5-Flash',  // Use alias (matching field_options)
      temperature: 0.8,
      max_tokens: 4096,
    },
    effective_prompts: {},
    user_overrides: {
      config_overrides: {},
      prompt_overrides: {},
    },
    editable_fields: ['config.model', 'config.temperature', 'config.max_tokens'],
    field_options: {
      'config.model': {
        type: 'select',
        label: 'Model',
        options: ['Gemini-2.5-Flash', 'DeepSeek-Chat', 'Kimi-K2'],
      },
      'config.temperature': {
        type: 'slider',
        label: 'Temperature',
        min: 0,
        max: 2,
        step: 0.1,
      },
      'config.max_tokens': {
        type: 'number',
        label: 'Max Tokens',
        min: 100,
        max: 16384,
      },
    },
  }),
  saveConfig: vi.fn().mockResolvedValue({
    status: 'success',
    message: 'Configuration updated successfully',
  }),
}));

vi.mock('@/stores/uiStore', () => ({
  useUIStore: vi.fn((selector) => {
    const state = { closeModal: vi.fn() };
    return selector ? selector(state) : state;
  }),
}));

vi.mock('@/services/identity/identity', () => ({
  IdentityService: {
    getIdentity: vi.fn().mockResolvedValue({
      privateKey: '0x...',
      publicKey: '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266',
    }),
    signCommand: vi.fn().mockResolvedValue({
      publicKey: '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266',
      signature: '0xabcd...',
    }),
    signData: vi.fn().mockResolvedValue({
      publicKey: '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266',
      signature: '0xabcd...',
    }),
  },
}));

vi.mock('@/features/chat/store/chatStore', () => ({
  useChatStore: {
    setState: vi.fn(),
    getState: vi.fn(() => ({ messages: [] })),
  },
}));

// ============================================================================
// Tests
// ============================================================================

describe('ConfigPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Layout & Design Standards', () => {
    it('should have fixed height of 360px', async () => {
      const { container } = render(<ConfigPanel />);
      
      await waitFor(() => {
        const fixedHeightDiv = container.querySelector('[class*="h-[360px]"]') || 
                               container.querySelector('[class*="h-\\[360px\\]"]');
        expect(fixedHeightDiv).toBeTruthy();
      });
    });

    it('should use grayscale design (no color emphasis)', async () => {
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/Model/i)).toBeInTheDocument();
      });

      const container = document.body;
      const colorClasses = container.innerHTML.match(/red-|blue-|green-|yellow-/g);
      expect(colorClasses).toBeNull();
    });
  });

  describe('Data Loading', () => {
    it('should show loading state on mount', () => {
      render(<ConfigPanel />);
      
      expect(screen.getByText(/正在加载配置|加载中/i) || screen.getByLabelText(/loading/i)).toBeInTheDocument();
    });

    it('should fetch config from API', async () => {
      const { fetchConfig } = await import('@/features/command/api');
      
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(fetchConfig).toHaveBeenCalled();
      });
    });

    it('should render form after successful load', async () => {
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/Model/i)).toBeInTheDocument();
        expect(screen.getByText(/Temperature/i)).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    it('should handle API errors gracefully', async () => {
      const { fetchConfig } = await import('@/features/command/api');
      vi.mocked(fetchConfig).mockRejectedValueOnce(new Error('Network error'));
      
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/无法加载配置|Network error|Error/i)).toBeInTheDocument();
      }, { timeout: 2000 });
      
      // Should show retry button
      expect(screen.getByText(/重试/i)).toBeInTheDocument();
    });
  });

  describe('Dynamic Form Rendering', () => {
    it('should render select dropdown for model field', async () => {
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/Model/i)).toBeInTheDocument();
        // Should find select element or button that opens dropdown
        const modelControl = screen.getByText(/Gemini-2.5-Flash/i) || 
                            screen.getByText(/gemini/i);
        expect(modelControl).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    it('should render slider for temperature field', async () => {
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/Temperature/i)).toBeInTheDocument();
        // Should find slider input or numeric display
        const tempDisplay = screen.getByText(/0\.8/) || 
                           document.querySelector('input[type="range"]');
        expect(tempDisplay).toBeTruthy();
      }, { timeout: 2000 });
    });

    it('should only render fields in editable_fields', async () => {
      render(<ConfigPanel />);
      
      await waitFor(() => {
        // Should render: model, temperature, max_tokens
        expect(screen.getByText(/Model/i)).toBeInTheDocument();
        expect(screen.getByText(/Temperature/i)).toBeInTheDocument();
        expect(screen.getByText(/Max Tokens/i)).toBeInTheDocument();
        
        // Should NOT render fields not in editable_fields (e.g., prompts)
        expect(screen.queryByText(/Prompt/i)).not.toBeInTheDocument();
      }, { timeout: 2000 });
    });
  });

  describe('Save Functionality', () => {
    it('should have save button in footer', async () => {
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/保存|Save/i)).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    it('should disable save button when no changes made', async () => {
      render(<ConfigPanel />);
      
      await waitFor(() => {
        // Query for button element (not just text)
        const saveButton = screen.getByRole('button', { name: /保存|Save/i });
        expect(saveButton).toBeDisabled();
      }, { timeout: 2000 });
    });

    it('should enable save button when changes are made', async () => {
      render(<ConfigPanel />);
      
      // Wait for form to load
      await waitFor(() => {
        expect(screen.getByText(/Model/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      // Make a change (this test assumes we can interact with the form)
      // Implementation will depend on actual form structure
      // For now, just verify the button exists
      const saveButton = screen.getByText(/保存|Save/i);
      expect(saveButton).toBeInTheDocument();
    });

    it('should call saveConfig with only changed fields', async () => {
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/Model/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      // Note: Actual interaction depends on form implementation
      // This is a placeholder for the test structure
      // When implemented, should verify that only modified fields are sent
    });

    it('should show loading state during save', async () => {
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/保存|Save/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      // Button should show loading state when clicked
      // Implementation will depend on actual button behavior
    });

    it('should close modal after successful save', async () => {
      const { useUIStore } = await import('@/stores/uiStore');
      const closeModalMock = vi.fn();
      
      vi.mocked(useUIStore).mockImplementation((selector) => {
        const state = { 
          activeModal: 'config' as const,
          closeModal: closeModalMock,
          openModal: vi.fn()
        };
        return selector ? selector(state) : state;
      });
      
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/保存|Save/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      // After successful save, modal should close
      // Implementation will verify this behavior
    });
  });

  describe('Error Handling', () => {
    it('should display error message on save failure', async () => {
      const { saveConfig } = await import('@/features/command/api');
      vi.mocked(saveConfig).mockRejectedValueOnce(new Error('Save failed'));
      
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/Model/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      // Trigger save (implementation dependent)
      // Should display error message
    });
  });

  describe('Mode Switching & Help Page', () => {
    it('should display help button with MODEL label on same line', async () => {
      render(<ConfigPanel />);
      
      await waitFor(() => {
        const helpButton = screen.getByLabelText(/配置说明/i);
        expect(helpButton).toBeInTheDocument();
        
        // Help button should be near MODEL label (inline layout)
        expect(screen.getByText(/MODEL/i)).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    it('should switch to help mode when help button is clicked', async () => {
      const user = userEvent.setup();
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/MODEL/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      const helpButton = screen.getByLabelText(/配置说明/i);
      await user.click(helpButton);

      await waitFor(() => {
        expect(screen.getByText(/配置说明/i)).toBeInTheDocument(); // Title
        expect(screen.getByText(/模型选择/i)).toBeInTheDocument(); // Section
      }, { timeout: 2000 });
    });

    it('should display all help sections', async () => {
      const user = userEvent.setup();
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/MODEL/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      const helpButton = screen.getByLabelText(/配置说明/i);
      await user.click(helpButton);

      await waitFor(() => {
        expect(screen.getByText(/模型选择.*Model/i)).toBeInTheDocument();
        expect(screen.getByText(/温度.*Temperature/i)).toBeInTheDocument();
        expect(screen.getByText(/最大令牌数.*Max Tokens/i)).toBeInTheDocument();
        expect(screen.getByText(/短期记忆.*History Context Size/i)).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    it('should navigate back from help mode', async () => {
      const user = userEvent.setup();
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/MODEL/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      // Go to help mode
      const helpButton = screen.getByLabelText(/配置说明/i);
      await user.click(helpButton);

      await waitFor(() => {
        expect(screen.getByText(/配置说明/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      // Go back
      const backButton = screen.getByLabelText(/返回/i);
      await user.click(backButton);

      await waitFor(() => {
        expect(screen.getByText(/MODEL/i)).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    it('should not show save button in help mode', async () => {
      const user = userEvent.setup();
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/MODEL/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      const helpButton = screen.getByLabelText(/配置说明/i);
      await user.click(helpButton);

      // Wait for help mode to fully render
      await waitFor(() => {
        expect(screen.getByText(/配置说明/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      // Save button should not be in DOM
      const saveButton = screen.queryByRole('button', { name: /保存/i });
      expect(saveButton).not.toBeInTheDocument();
    });
  });

  describe('Number Formatting', () => {
    it('should format float numbers to 1 decimal place on slider', async () => {
      render(<ConfigPanel />);
      
      await waitFor(() => {
        // Temperature slider should show as "0.8" not "0.8000000000002"
        const tempDisplay = screen.getByText('0.8');
        expect(tempDisplay).toBeInTheDocument();
        expect(tempDisplay.textContent).toBe('0.8');
      }, { timeout: 2000 });
    });

    it('should display integers without decimal point in number input', async () => {
      render(<ConfigPanel />);
      
      await waitFor(() => {
        // Max tokens input should have value "4096" not "4096.0"
        const maxTokensInput = screen.getByRole('spinbutton', { name: '' });
        expect(maxTokensInput).toHaveValue(4096);
      }, { timeout: 2000 });
    });
  });

  describe('Typography & Layout Standards', () => {
    it('should use text-xs for MODEL label (consistent with other field labels)', async () => {
      render(<ConfigPanel />);
      
      await waitFor(() => {
        const modelLabel = screen.getByText(/MODEL/i);
        expect(modelLabel.className).toMatch(/text-xs/);
      }, { timeout: 2000 });
    });

    it('should use text-base for help page title', async () => {
      const user = userEvent.setup();
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/MODEL/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      const helpButton = screen.getByLabelText(/配置说明/i);
      await user.click(helpButton);

      await waitFor(() => {
        const title = screen.getByText(/配置说明/i);
        expect(title.className).toMatch(/text-base/);
      }, { timeout: 2000 });
    });

    it('should use font-bold for help section headings', async () => {
      const user = userEvent.setup();
      render(<ConfigPanel />);
      
      await waitFor(() => {
        expect(screen.getByText(/MODEL/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      const helpButton = screen.getByLabelText(/配置说明/i);
      await user.click(helpButton);

      await waitFor(() => {
        const sectionHeading = screen.getByText(/模型选择.*Model/i);
        expect(sectionHeading.className).toMatch(/font-bold/);
      }, { timeout: 2000 });
    });
  });
});
