/**
 * ToolCallCard Component Tests
 * 
 * Tests for the ToolCallCard component's status-based visual rendering
 * Verifies different states: running, completed, error
 */

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ToolCallCard } from '@/features/chat/components/ToolCallCard';
import type { ToolCall } from '@/features/chat/types';

// Mock framer-motion to avoid animation complexities in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, className, onClick, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
      <div className={className} onClick={onClick} {...props}>
        {children}
      </div>
    )
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  ChevronDown: ({ className }: { className?: string }) => (
    <div data-testid="chevron-down" className={className}>▼</div>
  ),
  Check: ({ className }: { className?: string }) => (
    <div data-testid="check-icon" className={className}>✓</div>
  ),
  X: ({ className }: { className?: string }) => (
    <div data-testid="x-icon" className={className}>✗</div>
  )
}));

// Mock utils
vi.mock('@/lib/utils', () => ({
  cn: (...classes: (string | undefined | null | false)[]) => classes.filter(Boolean).join(' ')
}));

describe('ToolCallCard', () => {
  const createToolCall = (overrides: Partial<ToolCall> = {}): ToolCall => ({
    id: 'test-tool-id',
    toolName: 'test_tool',
    args: { param: 'value' },
    status: 'running',
    startTime: new Date('2023-01-01T12:00:00Z'),
    ...overrides
  });

  describe('Running state', () => {
    it('renders running state with executing text and loading animation', () => {
      const toolCall = createToolCall({
        status: 'running'
      });

      render(<ToolCallCard toolCall={toolCall} />);

      expect(screen.getByText('test_tool')).toBeInTheDocument();
      expect(screen.getByText('Executing...')).toBeInTheDocument();
      
      // Check for loading spinner structure
      const spinnerContainer = screen.getByText('Executing...').closest('div')?.parentElement;
      expect(spinnerContainer).toBeInTheDocument();
    });

    it('displays tool name and status correctly for running state', () => {
      const toolCall = createToolCall({
        toolName: 'search_database',
        status: 'running'
      });

      render(<ToolCallCard toolCall={toolCall} />);

      expect(screen.getByText('search_database')).toBeInTheDocument();
      expect(screen.getByText('Executing...')).toBeInTheDocument();
    });
  });

  describe('Completed state', () => {
    it('renders completed state with success text and check icon', () => {
      const toolCall = createToolCall({
        status: 'completed',
        result: 'Operation completed successfully',
        endTime: new Date('2023-01-01T12:01:00Z')
      });

      render(<ToolCallCard toolCall={toolCall} />);

      expect(screen.getByText('test_tool')).toBeInTheDocument();
      expect(screen.getByText('Completed')).toBeInTheDocument();
      expect(screen.getByTestId('check-icon')).toBeInTheDocument();
    });

    it('shows result when expanded in completed state', () => {
      const toolCall = createToolCall({
        status: 'completed',
        result: 'Search returned 5 results',
        endTime: new Date('2023-01-01T12:01:00Z')
      });

      render(<ToolCallCard toolCall={toolCall} />);

      // Click to expand
      fireEvent.click(screen.getByText('test_tool').closest('div')!);

      expect(screen.getByText('Result')).toBeInTheDocument();
      expect(screen.getByText('Search returned 5 results')).toBeInTheDocument();
    });
  });

  describe('Error state', () => {
    it('renders error state with failed text and X icon', () => {
      const toolCall = createToolCall({
        status: 'error',
        result: 'Connection timeout',
        endTime: new Date('2023-01-01T12:01:00Z')
      });

      render(<ToolCallCard toolCall={toolCall} />);

      expect(screen.getByText('test_tool')).toBeInTheDocument();
      expect(screen.getByText('Failed')).toBeInTheDocument();
      expect(screen.getByTestId('x-icon')).toBeInTheDocument();
    });

    it('shows error result when expanded', () => {
      const toolCall = createToolCall({
        status: 'error',
        result: 'Database connection failed',
        endTime: new Date('2023-01-01T12:01:00Z')
      });

      render(<ToolCallCard toolCall={toolCall} />);

      // Click to expand
      fireEvent.click(screen.getByText('test_tool').closest('div')!);

      expect(screen.getByText('Result')).toBeInTheDocument();
      expect(screen.getByText('Database connection failed')).toBeInTheDocument();
    });
  });

  describe('Expandable content', () => {
    it('shows arguments when expanded', () => {
      const toolCall = createToolCall({
        args: { 
          query: 'search term',
          limit: 10,
          filters: { category: 'tech' }
        },
        status: 'completed'
      });

      render(<ToolCallCard toolCall={toolCall} />);

      // Initially collapsed
      expect(screen.queryByText('Arguments')).not.toBeInTheDocument();

      // Click to expand
      fireEvent.click(screen.getByText('test_tool').closest('div')!);

      expect(screen.getByText('Arguments')).toBeInTheDocument();
      
      // Check that JSON is displayed
      const argsText = screen.getByText((content, element) => {
        return element?.tagName === 'PRE' && content.includes('"query"');
      });
      expect(argsText).toBeInTheDocument();
    });

    it('shows timing information when expanded', () => {
      const startTime = new Date('2023-01-01T12:00:00Z');
      const endTime = new Date('2023-01-01T12:00:05Z');
      
      const toolCall = createToolCall({
        status: 'completed',
        startTime,
        endTime
      });

      render(<ToolCallCard toolCall={toolCall} />);

      // Click to expand
      fireEvent.click(screen.getByText('test_tool').closest('div')!);

      expect(screen.getByText(/Started:/)).toBeInTheDocument();
      expect(screen.getByText(/Duration: 5s/)).toBeInTheDocument();
    });

    it('does not show duration for running tools', () => {
      const toolCall = createToolCall({
        status: 'running'
      });

      render(<ToolCallCard toolCall={toolCall} />);

      // Click to expand
      fireEvent.click(screen.getByText('test_tool').closest('div')!);

      expect(screen.getByText(/Started:/)).toBeInTheDocument();
      expect(screen.queryByText(/Duration:/)).not.toBeInTheDocument();
    });

    it('toggles expansion state on click', () => {
      const toolCall = createToolCall({
        status: 'completed',
        result: 'Test result'
      });

      render(<ToolCallCard toolCall={toolCall} />);

      const cardElement = screen.getByText('test_tool').closest('div')!;

      // Initially collapsed
      expect(screen.queryByText('Arguments')).not.toBeInTheDocument();

      // Click to expand
      fireEvent.click(cardElement);
      expect(screen.getByText('Arguments')).toBeInTheDocument();

      // Click to collapse
      fireEvent.click(cardElement);
      expect(screen.queryByText('Arguments')).not.toBeInTheDocument();
    });
  });

  describe('Interaction', () => {
    it('calls suppressAutoScroll when expanding', () => {
      const suppressAutoScroll = vi.fn();
      const toolCall = createToolCall({
        status: 'completed'
      });

      render(<ToolCallCard toolCall={toolCall} suppressAutoScroll={suppressAutoScroll} />);

      fireEvent.click(screen.getByText('test_tool').closest('div')!);

      expect(suppressAutoScroll).toHaveBeenCalledWith(450);
    });

    it('handles missing suppressAutoScroll gracefully', () => {
      const toolCall = createToolCall({
        status: 'completed'
      });

      render(<ToolCallCard toolCall={toolCall} />);

      // Should not throw when clicking without suppressAutoScroll
      expect(() => {
        fireEvent.click(screen.getByText('test_tool').closest('div')!);
      }).not.toThrow();
    });
  });

  describe('Edge cases', () => {
    it('handles empty arguments object', () => {
      const toolCall = createToolCall({
        args: {},
        status: 'completed'
      });

      render(<ToolCallCard toolCall={toolCall} />);

      fireEvent.click(screen.getByText('test_tool').closest('div')!);

      // Should not show Arguments section when args is empty
      expect(screen.queryByText('Arguments')).not.toBeInTheDocument();
    });

    it('handles missing result', () => {
      const toolCall = createToolCall({
        status: 'completed'
        // No result field
      });

      render(<ToolCallCard toolCall={toolCall} />);

      fireEvent.click(screen.getByText('test_tool').closest('div')!);

      // Should not show Result section when result is missing
      expect(screen.queryByText('Result')).not.toBeInTheDocument();
    });

    it('renders chevron icon for expansion indicator', () => {
      const toolCall = createToolCall({
        status: 'completed'
      });

      render(<ToolCallCard toolCall={toolCall} />);

      expect(screen.getByTestId('chevron-down')).toBeInTheDocument();
    });
  });
});
