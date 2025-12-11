/**
 * CommandPalette Component Tests
 * 
 * Tests for the CommandPalette component's filtering, selection, and interaction logic
 * Verifies command filtering, keyboard navigation, and execution
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CommandPalette } from '../CommandPalette';
import type { Command } from '../../command.types';

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: React.ComponentProps<'div'>) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: React.ComponentProps<'button'>) => <button {...props}>{children}</button>
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => children
}));

// Mock utils
vi.mock('@/lib/utils', () => ({
  cn: (...classes: (string | undefined | null | false)[]) => classes.filter(Boolean).join(' ')
}));

// Helper function to create test commands
const createTestCommands = (): Command[] => [
  { name: 'ping', description: 'Check connection to the NEXUS core.', usage: '/ping', handler: 'server', examples: ['/ping'] },
  { name: 'help', description: 'Display information about available commands.', usage: '/help', handler: 'server', examples: ['/help'] },
  { name: 'identity', description: 'Manage your user identity.', usage: '/identity', handler: 'server', examples: ['/identity'] }
];

// Helper function to create default props for testing
const createTestProps = (overrides = {}) => ({
  isOpen: true,
  query: '',
  availableCommands: createTestCommands(),
  selectedIndex: 0,
  onClose: vi.fn(),
  onExecute: vi.fn(),
  onSelectIndex: vi.fn(),
  ...overrides
});

describe('CommandPalette', () => {
  const mockOnClose = vi.fn();
  const mockOnExecute = vi.fn();
  const mockOnSelectIndex = vi.fn();
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    mockOnClose.mockClear();
    mockOnExecute.mockClear();
    mockOnSelectIndex.mockClear();
    user = userEvent.setup();
  });

  describe('Rendering', () => {
    it('renders nothing when isOpen is false', () => {
      const props = createTestProps({ isOpen: false });
      const { container } = render(<CommandPalette {...props} />);
      expect(container.firstChild).toBeNull();
    });

    it('renders basic command palette', () => {
      const props = createTestProps();
      render(<CommandPalette {...props} />);
      expect(screen.getByText('/ping')).toBeInTheDocument();
      expect(screen.getByText('/help')).toBeInTheDocument();
    });
  });

  describe('Command Filtering', () => {
    it('shows all commands when query is empty', () => {
      const props = createTestProps({ query: '' });
      render(<CommandPalette {...props} />);
      
      expect(screen.getByText('/ping')).toBeInTheDocument();
      expect(screen.getByText('/help')).toBeInTheDocument();
      expect(screen.getByText('/identity')).toBeInTheDocument();
    });

    it('filters commands by query (case insensitive)', () => {
      const props = createTestProps({ query: 'h' });
      render(<CommandPalette {...props} />);
      
      expect(screen.getByText('/help')).toBeInTheDocument();
      expect(screen.queryByText('/ping')).not.toBeInTheDocument();
      expect(screen.queryByText('/identity')).not.toBeInTheDocument();
    });

    it('filters commands by query (case insensitive) - uppercase', () => {
      const props = createTestProps({ query: 'H' });
      render(<CommandPalette {...props} />);
      
      expect(screen.getByText('/help')).toBeInTheDocument();
      expect(screen.queryByText('/ping')).not.toBeInTheDocument();
      expect(screen.queryByText('/identity')).not.toBeInTheDocument();
    });

    it('shows no commands when query matches nothing', () => {
      const props = createTestProps({ query: 'xyz' });
      render(<CommandPalette {...props} />);
      
      expect(screen.queryByText('/ping')).not.toBeInTheDocument();
      expect(screen.queryByText('/help')).not.toBeInTheDocument();
      expect(screen.queryByText('/identity')).not.toBeInTheDocument();
    });

    it('shows empty state when no commands match', () => {
      const props = createTestProps({ query: 'xyz' });
      const { container } = render(<CommandPalette {...props} />);
      
      // Should render empty div with height
      const emptyDiv = container.querySelector('.h-12');
      expect(emptyDiv).toBeInTheDocument();
    });
  });

  describe('Command Selection', () => {
    it('highlights selected command', () => {
      const props = createTestProps({ selectedIndex: 1 });
      render(<CommandPalette {...props} />);
      
      const helpButton = screen.getByText('/help').closest('button');
      expect(helpButton).toHaveClass('bg-accent/30');
    });

    it('does not highlight non-selected commands', () => {
      const props = createTestProps({ selectedIndex: 1 });
      render(<CommandPalette {...props} />);
      
      const pingButton = screen.getByText('/ping').closest('button');
      const identityButton = screen.getByText('/identity').closest('button');
      
      expect(pingButton).not.toHaveClass('bg-accent/30');
      expect(identityButton).not.toHaveClass('bg-accent/30');
    });

    it('updates selection on mouse enter', async () => {
      const props = createTestProps({ onSelectIndex: mockOnSelectIndex });
      render(<CommandPalette {...props} />);
      
      const helpButton = screen.getByText('/help').closest('button');
      await user.hover(helpButton!);
      
      expect(mockOnSelectIndex).toHaveBeenCalledWith(1);
    });
  });

  describe('Command Execution', () => {
    it('executes command on click', async () => {
      const props = createTestProps({ onExecute: mockOnExecute });
      render(<CommandPalette {...props} />);
      
      const helpButton = screen.getByText('/help').closest('button');
      await user.click(helpButton!);
      
      expect(mockOnExecute).toHaveBeenCalledWith('/help');
    });

    it('executes different commands correctly', async () => {
      const props = createTestProps({ onExecute: mockOnExecute });
      render(<CommandPalette {...props} />);
      
      const pingButton = screen.getByText('/ping').closest('button');
      await user.click(pingButton!);
      
      expect(mockOnExecute).toHaveBeenCalledWith('/ping');
    });
  });

  describe('Filtered Commands Selection', () => {
    it('correctly highlights selected command in filtered list', () => {
      const props = createTestProps({ 
        query: 'h', 
        selectedIndex: 0 // First (and only) command in filtered list
      });
      render(<CommandPalette {...props} />);
      
      const helpButton = screen.getByText('/help').closest('button');
      expect(helpButton).toHaveClass('bg-accent/30');
    });

    it('handles selection index correctly with filtered commands', () => {
      const props = createTestProps({ 
        query: 'i', 
        selectedIndex: 0 // First command in filtered list (identity)
      });
      render(<CommandPalette {...props} />);
      
      const identityButton = screen.getByText('/identity').closest('button');
      expect(identityButton).toHaveClass('bg-accent/30');
    });
  });

  describe('Accessibility', () => {
    it('renders buttons with role', () => {
      const props = createTestProps();
      render(<CommandPalette {...props} />);
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  describe('Edge Cases', () => {
    it('handles empty commands array', () => {
      const props = createTestProps({ availableCommands: [] });
      const { container } = render(<CommandPalette {...props} />);
      
      const emptyDiv = container.querySelector('.h-12');
      expect(emptyDiv).toBeInTheDocument();
    });

    it('handles selectedIndex out of bounds', () => {
      const props = createTestProps({ selectedIndex: 999 });
      render(<CommandPalette {...props} />);
      
      // Should not crash and no command should be highlighted
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).not.toHaveClass('bg-accent/30');
      });
    });

    it('handles negative selectedIndex', () => {
      const props = createTestProps({ selectedIndex: -1 });
      render(<CommandPalette {...props} />);
      
      // Should not crash and no command should be highlighted
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).not.toHaveClass('bg-accent/30');
      });
    });
  });

  describe('Animation and Styling', () => {
    it('mounts without motion errors', () => {
      const props = createTestProps();
      render(<CommandPalette {...props} />);
      expect(screen.getByText('/ping')).toBeInTheDocument();
    });
  });
});

