/**
 * ChatInput Component Tests
 * 
 * Tests for the ChatInput component's user interaction logic
 * Verifies input handling, submission, and disabled states
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatInput } from '@/features/chat/components/ChatInput';

// Helper function to create default props for testing
const createTestProps = (overrides = {}) => ({
  onSendMessage: vi.fn(),
  isCommandListOpen: false,
  commandQuery: '',
  availableCommands: [],
  selectedCommandIndex: 0,
  onOpenCommandList: vi.fn(),
  onCloseCommandList: vi.fn(),
  onSetCommandQuery: vi.fn(),
  onSetSelectedCommandIndex: vi.fn(),
  onExecuteCommand: vi.fn(),
  ...overrides
});

// Mock the UI components
vi.mock('@/components/ui', () => ({
  Button: ({ children, disabled, onClick, type, className, icon, iconOnly, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { icon?: React.ReactNode; iconOnly?: boolean }) => (
    <button 
      type={type}
      disabled={disabled} 
      onClick={onClick}
      className={className}
      data-testid="send-button"
      {...props}
    >
      {iconOnly && icon ? icon : children}
    </button>
  ),
  AutoResizeTextarea: React.forwardRef(({
    value,
    onChange,
    onKeyDown,
    onCompositionStart,
    onCompositionEnd,
    disabled,
    placeholder,
    className,
    ...props
  }: React.TextareaHTMLAttributes<HTMLTextAreaElement>, ref: React.Ref<HTMLTextAreaElement>) => {
    React.useImperativeHandle(ref, () => ({
      ...document.createElement('textarea'),
      resetHeight: vi.fn()
    }));
    
    return (
      <textarea
        ref={ref}
        value={value}
        onChange={onChange}
        onKeyDown={onKeyDown}
        onCompositionStart={onCompositionStart}
        onCompositionEnd={onCompositionEnd}
        disabled={disabled}
        placeholder={placeholder}
        className={className}
        data-testid="message-input"
        {...props}
      />
    );
  })
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
  ArrowUp: ({ size }: { size?: number }) => (
    <div data-testid="arrow-up-icon" data-size={size}>↑</div>
  )
}));

// Mock utils
vi.mock('@/lib/utils', () => ({
  cn: (...classes: (string | undefined | null | false)[]) => classes.filter(Boolean).join(' ')
}));

describe('ChatInput', () => {
  const mockOnSendMessage = vi.fn();
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    mockOnSendMessage.mockClear();
    user = userEvent.setup();
  });

  describe('Message sending', () => {
    it('sends message on submit when input has content', async () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const input = screen.getByTestId('message-input');
      const sendButton = screen.getByTestId('send-button');

      // Type message
      await user.type(input, 'Hello, this is a test message');
      
      // Click send button
      await user.click(sendButton);

      expect(mockOnSendMessage).toHaveBeenCalledWith('Hello, this is a test message');
      expect(mockOnSendMessage).toHaveBeenCalledTimes(1);
    });

    it('sends message on Enter key press', async () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const input = screen.getByTestId('message-input');

      // Type message and press Enter
      await user.type(input, 'Test message{enter}');

      expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
      expect(mockOnSendMessage).toHaveBeenCalledTimes(1);
    });

    it('does not send message on Shift+Enter', async () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const input = screen.getByTestId('message-input');

      // Type message and press Shift+Enter
      await user.type(input, 'Test message');
      await user.keyboard('{Shift>}{Enter}{/Shift}');

      expect(mockOnSendMessage).not.toHaveBeenCalled();
    });

    it('clears input after sending message', async () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const input = screen.getByTestId('message-input') as HTMLTextAreaElement;
      const sendButton = screen.getByTestId('send-button');

      // Type and send message
      await user.type(input, 'Test message');
      await user.click(sendButton);

      expect(input.value).toBe('');
    });

    it('trims whitespace from message before sending', async () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const input = screen.getByTestId('message-input');
      const sendButton = screen.getByTestId('send-button');

      // Type message with leading/trailing spaces
      await user.type(input, '   Test message with spaces   ');
      await user.click(sendButton);

      expect(mockOnSendMessage).toHaveBeenCalledWith('Test message with spaces');
    });
  });

  describe('Button disabled state', () => {
    it('disables send button when input is empty', () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const sendButton = screen.getByTestId('send-button');
      
      expect(sendButton).toBeDisabled();
    });

    it('enables send button when input has content', async () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const input = screen.getByTestId('message-input');
      const sendButton = screen.getByTestId('send-button');

      await user.type(input, 'Some content');

      expect(sendButton).not.toBeDisabled();
    });

    it('disables send button when input contains only whitespace', async () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const input = screen.getByTestId('message-input');
      const sendButton = screen.getByTestId('send-button');

      await user.type(input, '   ');

      expect(sendButton).toBeDisabled();
    });

    it('re-disables send button after clearing input', async () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const input = screen.getByTestId('message-input');
      const sendButton = screen.getByTestId('send-button');

      // Type content
      await user.type(input, 'Some content');
      expect(sendButton).not.toBeDisabled();

      // Clear content
      await user.clear(input);
      expect(sendButton).toBeDisabled();
    });
  });

  describe('Input disabled state', () => {
    it('disables input and button when disabled prop is true', () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props}  disabled={true} />);

      const input = screen.getByTestId('message-input');
      const sendButton = screen.getByTestId('send-button');

      expect(input).toBeDisabled();
      expect(sendButton).toBeDisabled();
    });

    it('does not send message when disabled', async () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props}  disabled={true} />);

      const input = screen.getByTestId('message-input');

      // Try to type (should not work due to disabled state)
      await user.type(input, 'Test message');
      
      // Try to submit via Enter key
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(mockOnSendMessage).not.toHaveBeenCalled();
    });

    it('prevents submission during composition (IME input)', async () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const input = screen.getByTestId('message-input');

      await user.type(input, 'Test message');

      // Simulate composition start (IME input)
      fireEvent.compositionStart(input);
      
      // Try to submit with Enter during composition
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(mockOnSendMessage).not.toHaveBeenCalled();

      // End composition and try again
      fireEvent.compositionEnd(input);
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
    });
  });

  describe('Form submission', () => {
    it('handles form submission event', async () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const input = screen.getByTestId('message-input');
      const form = input.closest('form')!;

      await user.type(input, 'Form submission test');
      
      fireEvent.submit(form);

      expect(mockOnSendMessage).toHaveBeenCalledWith('Form submission test');
    });

    it('prevents default form submission behavior', async () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const input = screen.getByTestId('message-input');
      const form = input.closest('form')!;

      await user.type(input, 'Test message');

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      const preventDefaultSpy = vi.spyOn(submitEvent, 'preventDefault');
      
      fireEvent(form, submitEvent);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });
  });

  describe('Accessibility and UX', () => {
    it('renders with correct placeholder text', () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const input = screen.getByTestId('message-input');
      
      expect(input).toHaveAttribute('placeholder', '继续探索...');
    });

    it('renders arrow up icon in send button', () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      expect(screen.getByTestId('arrow-up-icon')).toBeInTheDocument();
      expect(screen.getByTestId('arrow-up-icon')).toHaveAttribute('data-size', '18');
    });

    it('applies correct CSS classes for styling', () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      const { container } = render(<ChatInput {...props} />);

      const wrapper = container.querySelector('.w-full.max-w-2xl.mx-auto');
      expect(wrapper).toBeInTheDocument();

      const formWrapper = container.querySelector('.relative.rounded-2xl.border');
      expect(formWrapper).toBeInTheDocument();
    });
  });

  describe('Edge cases', () => {
    it('handles rapid successive submissions', async () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const input = screen.getByTestId('message-input');
      const sendButton = screen.getByTestId('send-button');

      // Type message
      await user.type(input, 'Rapid test');
      
      // Click multiple times rapidly
      await user.click(sendButton);
      await user.click(sendButton);
      await user.click(sendButton);

      // Should only send once since input is cleared after first send
      expect(mockOnSendMessage).toHaveBeenCalledTimes(1);
      expect(mockOnSendMessage).toHaveBeenCalledWith('Rapid test');
    });

    it('handles empty string after trim', async () => {
      const props = createTestProps({ onSendMessage: mockOnSendMessage });
      render(<ChatInput {...props} />);

      const input = screen.getByTestId('message-input');
      const sendButton = screen.getByTestId('send-button');

      // Type only spaces
      await user.type(input, '     ');
      
      // Button should be disabled
      expect(sendButton).toBeDisabled();
      
      // Try to submit anyway
      fireEvent.click(sendButton);

      expect(mockOnSendMessage).not.toHaveBeenCalled();
    });
  });

  describe('Command mode - smart selection', () => {
    it('executes filtered command on Enter prioritizing query over selection', async () => {
      const onExecuteCommand = vi.fn();
      const props = createTestProps({
        isCommandListOpen: true,
        commandQuery: 'help',
        availableCommands: [
          { name: 'ping', description: '' },
          { name: 'help', description: '' },
          { name: 'identity', description: '' }
        ],
        selectedCommandIndex: 0,
        onExecuteCommand
      });
      render(<ChatInput {...props} />);
      const input = screen.getByTestId('message-input');
      await user.click(input);
      await user.keyboard('{Enter}');
      expect(onExecuteCommand).toHaveBeenCalledWith('/help');
    });

    it('navigates within filtered commands length', async () => {
      const onSetSelectedCommandIndex = vi.fn();
      const props = createTestProps({
        isCommandListOpen: true,
        commandQuery: 'h',
        availableCommands: [
          { name: 'ping', description: '' },
          { name: 'help', description: '' },
          { name: 'identity', description: '' }
        ],
        selectedCommandIndex: 0,
        onSetSelectedCommandIndex
      });
      render(<ChatInput {...props} />);
      const input = screen.getByTestId('message-input');
      await user.click(input);
      await user.keyboard('{ArrowDown}');
      expect(onSetSelectedCommandIndex).toHaveBeenCalledWith(0);
      await user.keyboard('{ArrowUp}');
      expect(onSetSelectedCommandIndex).toHaveBeenCalledWith(0);
    });

    it('smart-selects exact match when typing after slash', async () => {
      const onSetSelectedCommandIndex = vi.fn();
      const onOpenCommandList = vi.fn();
      const onSetCommandQuery = vi.fn();
      const props = createTestProps({
        onSetSelectedCommandIndex,
        onOpenCommandList,
        onSetCommandQuery,
        availableCommands: [
          { name: 'ping', description: '' },
          { name: 'help', description: '' },
          { name: 'identity', description: '' }
        ]
      });
      render(<ChatInput {...props} />);
      await user.type(screen.getByTestId('message-input'), '/help');
      expect(onOpenCommandList).toHaveBeenCalled();
      expect(onSetCommandQuery).toHaveBeenCalledWith('help');
      expect(onSetSelectedCommandIndex).toHaveBeenLastCalledWith(0);
    });

    it('sets selection to -1 when no match exists', async () => {
      const onSetSelectedCommandIndex = vi.fn();
      const onOpenCommandList = vi.fn();
      const onSetCommandQuery = vi.fn();
      const props = createTestProps({
        onSetSelectedCommandIndex,
        onOpenCommandList,
        onSetCommandQuery,
        availableCommands: [
          { name: 'ping', description: '' },
          { name: 'help', description: '' },
          { name: 'identity', description: '' }
        ]
      });
      render(<ChatInput {...props} />);
      await user.type(screen.getByTestId('message-input'), '/x');
      expect(onOpenCommandList).toHaveBeenCalled();
      expect(onSetCommandQuery).toHaveBeenCalledWith('x');
      expect(onSetSelectedCommandIndex).toHaveBeenLastCalledWith(-1);
    });
  });
});
