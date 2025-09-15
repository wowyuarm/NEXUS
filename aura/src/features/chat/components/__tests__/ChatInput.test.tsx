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

// Mock the UI components
vi.mock('@/components/ui', () => ({
  Button: ({ children, disabled, onClick, type, className, icon, iconOnly, ...props }: any) => (
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
  }: any, ref: any) => {
    React.useImperativeHandle(ref, () => ({
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
  cn: (...classes: any[]) => classes.filter(Boolean).join(' ')
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
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

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
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

      const input = screen.getByTestId('message-input');

      // Type message and press Enter
      await user.type(input, 'Test message{enter}');

      expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
      expect(mockOnSendMessage).toHaveBeenCalledTimes(1);
    });

    it('does not send message on Shift+Enter', async () => {
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

      const input = screen.getByTestId('message-input');

      // Type message and press Shift+Enter
      await user.type(input, 'Test message');
      await user.keyboard('{Shift>}{Enter}{/Shift}');

      expect(mockOnSendMessage).not.toHaveBeenCalled();
    });

    it('clears input after sending message', async () => {
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

      const input = screen.getByTestId('message-input') as HTMLTextAreaElement;
      const sendButton = screen.getByTestId('send-button');

      // Type and send message
      await user.type(input, 'Test message');
      await user.click(sendButton);

      expect(input.value).toBe('');
    });

    it('trims whitespace from message before sending', async () => {
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

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
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

      const sendButton = screen.getByTestId('send-button');
      
      expect(sendButton).toBeDisabled();
    });

    it('enables send button when input has content', async () => {
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

      const input = screen.getByTestId('message-input');
      const sendButton = screen.getByTestId('send-button');

      await user.type(input, 'Some content');

      expect(sendButton).not.toBeDisabled();
    });

    it('disables send button when input contains only whitespace', async () => {
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

      const input = screen.getByTestId('message-input');
      const sendButton = screen.getByTestId('send-button');

      await user.type(input, '   ');

      expect(sendButton).toBeDisabled();
    });

    it('re-disables send button after clearing input', async () => {
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

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
      render(<ChatInput onSendMessage={mockOnSendMessage} disabled={true} />);

      const input = screen.getByTestId('message-input');
      const sendButton = screen.getByTestId('send-button');

      expect(input).toBeDisabled();
      expect(sendButton).toBeDisabled();
    });

    it('does not send message when disabled', async () => {
      render(<ChatInput onSendMessage={mockOnSendMessage} disabled={true} />);

      const input = screen.getByTestId('message-input');

      // Try to type (should not work due to disabled state)
      await user.type(input, 'Test message');
      
      // Try to submit via Enter key
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(mockOnSendMessage).not.toHaveBeenCalled();
    });

    it('prevents submission during composition (IME input)', async () => {
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

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
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

      const input = screen.getByTestId('message-input');
      const form = input.closest('form')!;

      await user.type(input, 'Form submission test');
      
      fireEvent.submit(form);

      expect(mockOnSendMessage).toHaveBeenCalledWith('Form submission test');
    });

    it('prevents default form submission behavior', async () => {
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

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
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

      const input = screen.getByTestId('message-input');
      
      expect(input).toHaveAttribute('placeholder', '继续探索...');
    });

    it('renders arrow up icon in send button', () => {
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

      expect(screen.getByTestId('arrow-up-icon')).toBeInTheDocument();
      expect(screen.getByTestId('arrow-up-icon')).toHaveAttribute('data-size', '18');
    });

    it('applies correct CSS classes for styling', () => {
      const { container } = render(<ChatInput onSendMessage={mockOnSendMessage} />);

      const wrapper = container.querySelector('.w-full.max-w-2xl.mx-auto');
      expect(wrapper).toBeInTheDocument();

      const formWrapper = container.querySelector('.relative.rounded-2xl.border');
      expect(formWrapper).toBeInTheDocument();
    });
  });

  describe('Edge cases', () => {
    it('handles rapid successive submissions', async () => {
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

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
      render(<ChatInput onSendMessage={mockOnSendMessage} />);

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
});
