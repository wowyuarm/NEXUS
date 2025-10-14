/**
 * Panel Component - Universal Control Panel Structure
 * 
 * Provides a consistent structural and visual language for all control panels in YX Nexus.
 * This component embodies the "liquid glass" material aesthetic and enforces a unified
 * layout pattern across identity, config, prompt, and future panels.
 * 
 * Design Philosophy:
 * - **Structural Consistency**: All panels share the same layout DNA
 * - **Liquid Glass Material**: Semi-transparent card with backdrop blur effect
 * - **Cognitive Ease**: Familiar structure reduces mental load for users
 * 
 * Responsibilities:
 * - Render header with title and close button
 * - Provide scrollable content area
 * - Optional footer for action buttons
 * - Apply unified liquid glass styling
 */

import { X } from 'lucide-react';
import { Button } from '@/components/ui';

interface PanelProps {
  /** Panel title displayed in the header */
  title: string;
  
  /** Callback invoked when close button is clicked */
  onClose?: () => void;
  
  /** Panel main content */
  children: React.ReactNode;
  
  /** Optional footer content (typically action buttons) */
  footer?: React.ReactNode;
}

/**
 * Panel component with liquid glass material and consistent structure
 * 
 * @example
 * ```tsx
 * <Panel 
 *   title="Identity Management" 
 *   onClose={handleClose}
 *   footer={<Button>Save Changes</Button>}
 * >
 *   <div>Your panel content here...</div>
 * </Panel>
 * ```
 */
export const Panel: React.FC<PanelProps> = ({ title, onClose, children, footer }) => {
  return (
    <div className="bg-card/75 backdrop-blur-xl border border-border shadow-lg shadow-black/20 rounded-2xl max-w-2xl w-full flex flex-col max-h-[80vh]">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border flex items-center justify-between shrink-0">
        <h2 className="text-lg font-medium text-foreground">{title}</h2>
        {onClose && (
          <Button
            variant="ghost"
            size="sm"
            icon={<X size={18} />}
            iconOnly
            onClick={onClose}
            aria-label="Close panel"
          />
        )}
      </div>

      {/* Content area - scrollable */}
      <div className="px-6 py-4 overflow-y-auto flex-1">
        {children}
      </div>

      {/* Optional footer */}
      {footer && (
        <div className="px-6 py-4 border-t border-border shrink-0">
          {footer}
        </div>
      )}
    </div>
  );
};

