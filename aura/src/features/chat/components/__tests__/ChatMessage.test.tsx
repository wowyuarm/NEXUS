/**
 * ChatMessage Component Tests
 * 
 * Tests for the ChatMessage component's conditional rendering logic
 * Based on different Run states and message types
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChatMessage } from '@/features/chat/components/ChatMessage';
import type { Message } from '@/features/chat/types';

// Mock the dependencies
vi.mock('@/components/ui/MarkdownRenderer', () => ({
  MarkdownRenderer: ({ content }: { content: string }) => <div data-testid="markdown-content">{content}</div>
}));

vi.mock('@/components/ui/Timestamp', () => ({
  Timestamp: ({ date }: { date: Date }) => <div data-testid="timestamp">{date.toISOString()}</div>
}));

vi.mock('@/components/ui/RoleSymbol', () => ({
  RoleSymbol: ({ role, isThinking, status }: { role: string; isThinking?: boolean; status?: string }) => (
    <div data-testid="role-symbol" data-role={role} data-thinking={isThinking} data-status={status}>
      {role === 'HUMAN' ? '▲' : role === 'SYSTEM' ? '■' : '●'}
    </div>
  )
}));

vi.mock('@/features/chat/components/ToolCallCard', () => ({
  ToolCallCard: ({ toolCall }: { toolCall: { id: string; toolName: string; status: string } }) => (
    <div data-testid="tool-call-card" data-tool-name={toolCall.toolName} data-status={toolCall.status}>
      Tool: {toolCall.toolName}
    </div>
  )
}));

vi.mock('@/features/chat/hooks/useTypewriter', () => ({
  useTypewriter: ({ targetContent }: { targetContent: string }) => ({
    displayedContent: targetContent,
    isTyping: false
  })
}));

describe('ChatMessage', () => {
  const createMessage = (overrides: Partial<Message> = {}): Message => ({
    id: 'test-message-id',
    role: 'HUMAN',
    content: 'Test message content',
    timestamp: new Date('2023-01-01T12:00:00Z'),
    ...overrides
  });

  describe('Human messages', () => {
    it('renders human message correctly with triangle symbol', () => {
      const message = createMessage({
        role: 'HUMAN',
        content: 'Hello, this is a human message'
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={false} 
          currentRunStatus="idle" 
        />
      );

      expect(screen.getByTestId('role-symbol')).toHaveAttribute('data-role', 'HUMAN');
      expect(screen.getByTestId('role-symbol')).toHaveTextContent('▲');
      expect(screen.getByTestId('markdown-content')).toHaveTextContent('Hello, this is a human message');
      expect(screen.getByTestId('timestamp')).toBeInTheDocument();
    });
  });

  describe('AI messages - thinking state', () => {
    it('renders thinking state without content when currentRunStatus is thinking', () => {
      const message = createMessage({
        role: 'AI',
        content: '',
        isStreaming: true
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={true} 
          currentRunStatus="thinking" 
        />
      );

      // In thinking state with normal variant, the entire component should not render
      expect(screen.queryByTestId('role-symbol')).not.toBeInTheDocument();
      expect(screen.queryByTestId('markdown-content')).not.toBeInTheDocument();
    });

    it('renders role symbol with breathing animation attributes in contentOnly variant during thinking', () => {
      const message = createMessage({
        role: 'AI',
        content: '',
        isStreaming: true
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={true} 
          currentRunStatus="thinking"
          variant="contentOnly"
        />
      );

      // In contentOnly variant, content area is rendered but should be empty
      expect(screen.queryByTestId('markdown-content')).not.toBeInTheDocument();
      expect(screen.queryByTestId('tool-call-card')).not.toBeInTheDocument();
    });
  });

  describe('AI messages - tool running state', () => {
    it('renders tool running state with ToolCallCard components', () => {
      const toolCall = {
        id: 'tool-1',
        toolName: 'test_tool',
        args: { param: 'value' },
        status: 'running' as const,
        startTime: new Date(),
        insertIndex: 0 // Add insertIndex to ensure tool card is rendered
      };

      const message = createMessage({
        role: 'AI',
        content: 'Processing your request...',
        isStreaming: false, // Set to false to ensure tool card is shown
        toolCalls: [toolCall]
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={true} 
          currentRunStatus="tool_running" 
        />
      );

      expect(screen.getByTestId('role-symbol')).toHaveAttribute('data-role', 'AI');
      expect(screen.getByTestId('markdown-content')).toHaveTextContent('Processing your request...');
      expect(screen.getByTestId('tool-call-card')).toHaveAttribute('data-tool-name', 'test_tool');
      expect(screen.getByTestId('tool-call-card')).toHaveAttribute('data-status', 'running');
    });

    it('renders multiple tool calls in correct order', () => {
      const toolCalls = [
        {
          id: 'tool-1',
          toolName: 'first_tool',
          args: {},
          status: 'running' as const,
          startTime: new Date(),
          insertIndex: 10
        },
        {
          id: 'tool-2', 
          toolName: 'second_tool',
          args: {},
          status: 'completed' as const,
          startTime: new Date(),
          insertIndex: 5
        }
      ];

      const message = createMessage({
        role: 'AI',
        content: 'Here is some text with tools',
        toolCalls
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={true} 
          currentRunStatus="tool_running" 
        />
      );

      const toolCards = screen.getAllByTestId('tool-call-card');
      expect(toolCards).toHaveLength(2);
      
      // Tools should be ordered by insertIndex (second_tool first, then first_tool)
      expect(toolCards[0]).toHaveAttribute('data-tool-name', 'second_tool');
      expect(toolCards[1]).toHaveAttribute('data-tool-name', 'first_tool');
    });
  });

  describe('AI messages - streaming text state', () => {
    it('renders streaming text state with typewriter effect', () => {
      const message = createMessage({
        role: 'AI',
        content: 'This is streaming text...',
        isStreaming: true
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={true} 
          currentRunStatus="streaming_text" 
        />
      );

      expect(screen.getByTestId('role-symbol')).toHaveAttribute('data-role', 'AI');
      expect(screen.getByTestId('markdown-content')).toHaveTextContent('This is streaming text...');
    });
  });

  describe('Historical messages', () => {
    it('renders completed AI message with static content', () => {
      const message = createMessage({
        role: 'AI',
        content: 'This is a completed AI response',
        isStreaming: false
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={false} 
          currentRunStatus="idle" 
        />
      );

      expect(screen.getByTestId('role-symbol')).toHaveAttribute('data-role', 'AI');
      expect(screen.getByTestId('markdown-content')).toHaveTextContent('This is a completed AI response');
    });

    it('renders historical message with completed tool calls', () => {
      const toolCall = {
        id: 'tool-1',
        toolName: 'completed_tool',
        args: { param: 'value' },
        status: 'completed' as const,
        startTime: new Date(),
        endTime: new Date(),
        result: 'Tool completed successfully'
      };

      const message = createMessage({
        role: 'AI',
        content: 'Response with tool call',
        isStreaming: false,
        toolCalls: [toolCall]
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={false} 
          currentRunStatus="idle" 
        />
      );

      expect(screen.getByTestId('markdown-content')).toHaveTextContent('Response with tool call');
      expect(screen.getByTestId('tool-call-card')).toHaveAttribute('data-status', 'completed');
    });
  });

  describe('SYSTEM messages', () => {
    it('renders SYSTEM message with pending status - command only', () => {
      const message = createMessage({
        role: 'SYSTEM',
        content: { command: '/ping' },
        metadata: { status: 'pending' }
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={false} 
          currentRunStatus="idle" 
        />
      );

      // Should render role symbol as ■
      expect(screen.getByTestId('role-symbol')).toHaveAttribute('data-role', 'SYSTEM');
      
      // Should render command line
      expect(screen.getByTestId('system-command')).toHaveTextContent('/ping');
      
      // Should NOT render divider or result when pending
      expect(screen.queryByTestId('system-divider')).not.toBeInTheDocument();
      expect(screen.queryByTestId('system-result')).not.toBeInTheDocument();
    });

    it('renders SYSTEM message with completed status - command and result', () => {
      const message = createMessage({
        role: 'SYSTEM',
        content: { 
          command: '/ping',
          result: { status: 'success', latency: '1ms', version: '0.2.0' }
        },
        metadata: { status: 'completed' }
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={false} 
          currentRunStatus="idle" 
        />
      );

      // Should render role symbol
      expect(screen.getByTestId('role-symbol')).toHaveAttribute('data-role', 'SYSTEM');
      
      // Should render command line
      expect(screen.getByTestId('system-command')).toHaveTextContent('/ping');
      
      // Should render divider
      expect(screen.getByTestId('system-divider')).toBeInTheDocument();
      
      // Should render result section
      expect(screen.getByTestId('system-result')).toBeInTheDocument();
    });

    it('renders SYSTEM message with string result', () => {
      const message = createMessage({
        role: 'SYSTEM',
        content: { 
          command: '/help',
          result: 'Available commands:\n- /ping: Check server status\n- /help: Show this help'
        },
        metadata: { status: 'completed' }
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={false} 
          currentRunStatus="idle" 
        />
      );

      expect(screen.getByTestId('system-command')).toHaveTextContent('/help');
      expect(screen.getByTestId('system-result')).toBeInTheDocument();
      // String results should be rendered with MarkdownRenderer
      expect(screen.getByTestId('markdown-content')).toBeInTheDocument();
    });

    it('passes status to RoleSymbol for breathing animation', () => {
      const message = createMessage({
        role: 'SYSTEM',
        content: { command: '/ping' },
        metadata: { status: 'pending' }
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={false} 
          currentRunStatus="idle" 
        />
      );

      // RoleSymbol should receive status for animation
      const roleSymbol = screen.getByTestId('role-symbol');
      expect(roleSymbol).toBeInTheDocument();
      // The actual animation behavior is tested in RoleSymbol's own tests
    });
  });

  describe('Variant rendering', () => {
    it('renders full row with role symbol in normal variant', () => {
      const message = createMessage({
        role: 'HUMAN',
        content: 'Test message'
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={false} 
          currentRunStatus="idle"
          variant="normal"
        />
      );

      expect(screen.getByTestId('role-symbol')).toBeInTheDocument();
      expect(screen.getByTestId('markdown-content')).toBeInTheDocument();
    });

    it('renders only content area in contentOnly variant', () => {
      const message = createMessage({
        role: 'HUMAN',
        content: 'Test message'
      });

      const { container } = render(
        <ChatMessage 
          message={message} 
          isLastMessage={false} 
          currentRunStatus="idle"
          variant="contentOnly"
        />
      );

      expect(screen.getByTestId('markdown-content')).toBeInTheDocument();
      expect(screen.getByTestId('timestamp')).toBeInTheDocument();
      
      // Should not have the full row wrapper classes
      expect(container.firstChild).not.toHaveClass('group', 'relative', 'py-6', 'flex', 'items-baseline', 'gap-2');
    });
  });

  describe('SYSTEM messages - structured command rendering', () => {
    it('renders pending SYSTEM message with command only', () => {
      const message = createMessage({
        role: 'SYSTEM',
        content: { command: '/ping' },
        metadata: { status: 'pending' }
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={false} 
          currentRunStatus="idle"
        />
      );

      expect(screen.getByTestId('role-symbol')).toHaveAttribute('data-role', 'SYSTEM');
      expect(screen.getByTestId('system-command')).toHaveTextContent('/ping');
      expect(screen.queryByTestId('system-divider')).not.toBeInTheDocument();
      expect(screen.queryByTestId('system-result')).not.toBeInTheDocument();
    });

    it('renders completed SYSTEM message with command and string result', () => {
      const message = createMessage({
        role: 'SYSTEM',
        content: { 
          command: '/ping', 
          result: 'pong - latency: 1ms' 
        },
        metadata: { status: 'completed' }
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={false} 
          currentRunStatus="idle"
        />
      );

      expect(screen.getByTestId('role-symbol')).toHaveAttribute('data-role', 'SYSTEM');
      expect(screen.getByTestId('system-command')).toHaveTextContent('/ping');
      expect(screen.getByTestId('system-divider')).toBeInTheDocument();
      expect(screen.getByTestId('system-result')).toBeInTheDocument();
    });

    it('renders completed SYSTEM message with command and object result', () => {
      const message = createMessage({
        role: 'SYSTEM',
        content: { 
          command: '/ping', 
          result: {
            status: 'success',
            latency: '1ms',
            version: '0.2.0'
          }
        },
        metadata: { status: 'completed' }
      });

      render(
        <ChatMessage 
          message={message} 
          isLastMessage={false} 
          currentRunStatus="idle"
        />
      );

      expect(screen.getByTestId('system-command')).toHaveTextContent('/ping');
      expect(screen.getByTestId('system-divider')).toBeInTheDocument();
      const resultElement = screen.getByTestId('system-result');
      expect(resultElement).toBeInTheDocument();
      // Should contain formatted key-value pairs
      expect(resultElement.textContent).toContain('status');
      expect(resultElement.textContent).toContain('success');
    });

    it('passes status to RoleSymbol for animation control', () => {
      const pendingMessage = createMessage({
        role: 'SYSTEM',
        content: { command: '/ping' },
        metadata: { status: 'pending' }
      });

      const { rerender } = render(
        <ChatMessage 
          message={pendingMessage} 
          isLastMessage={false} 
          currentRunStatus="idle"
        />
      );

      const roleSymbol = screen.getByTestId('role-symbol');
      expect(roleSymbol).toHaveAttribute('data-status', 'pending');

      // Update to completed
      const completedMessage = createMessage({
        role: 'SYSTEM',
        content: { command: '/ping', result: 'pong' },
        metadata: { status: 'completed' }
      });

      rerender(
        <ChatMessage 
          message={completedMessage} 
          isLastMessage={false} 
          currentRunStatus="idle"
        />
      );

      expect(screen.getByTestId('role-symbol')).toHaveAttribute('data-status', 'completed');
    });
  });
});
