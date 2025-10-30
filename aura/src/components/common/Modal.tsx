/**
 * Modal Component - Universal Modal Container
 * 
 * Provides the foundational modal behavior for the NEXUS modal interaction system.
 * This component creates a "focused silence" - a temporary zen space for maintenance tasks,
 * representing the elegant transition from dialogue mode to maintenance mode.
 * 
 * Design Philosophy:
 * - **Focused Silence**: Modal creates an undisturbed space through backdrop blur
 * - **Physical Intuition**: Animations mirror natural movement with bounce-back physics
 * - **Multiple Exit Routes**: Click backdrop or press ESC for graceful dismissal
 * 
 * Responsibilities:
 * - Render backdrop with liquid glass effect
 * - Manage enter/exit animations
 * - Handle close interactions (ESC key, backdrop click)
 * - Prevent body scroll when open
 * - Content-agnostic: only manages modal behavior, not content
 */

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { FRAMER, MOTION_EXIT } from '@/lib/motion';

interface ModalProps {
  /** Whether the modal is currently open */
  isOpen: boolean;
  
  /** Callback invoked when user requests to close the modal */
  onClose: () => void;
  
  /** Modal content (typically a Panel component) */
  children: React.ReactNode;
}

/**
 * Modal component with liquid glass backdrop and smooth animations
 * 
 * @example
 * ```tsx
 * <Modal isOpen={isOpen} onClose={handleClose}>
 *   <Panel title="Settings">
 *     <div>Panel content here...</div>
 *   </Panel>
 * </Modal>
 * ```
 */
export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, children }) => {
  // ESC key handler
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    // Cleanup on unmount
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop with liquid glass effect */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ 
              opacity: 1,
              transition: { duration: FRAMER.scene.duration, ease: FRAMER.scene.ease }
            }}
            exit={{ 
              opacity: 0,
              transition: { duration: MOTION_EXIT.scene, ease: MOTION_EXIT.ease }
            }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-background/80 backdrop-blur-xl"
            aria-hidden="true"
          />

          {/* Modal container */}
          <div className={cn(
            "fixed inset-0 z-50 flex items-center justify-center pointer-events-none",
            // Mobile: p-3 (reduced outer margin)
            "p-3",
            // Desktop: restore p-6
            "md:p-6"
          )}>
            {/* Content wrapper with scale + fade animation */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ 
                opacity: 1, 
                scale: 1,
                transition: FRAMER.scene
              }}
              exit={{ 
                opacity: 0, 
                scale: 0.95,
                transition: { duration: MOTION_EXIT.scene, ease: MOTION_EXIT.ease }
              }}
              className="pointer-events-auto"
              onClick={(e) => e.stopPropagation()} // Prevent backdrop click from bubbling
            >
              {children}
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
};

