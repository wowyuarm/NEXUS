/**
 * Global UI State Store
 * 
 * Manages application-wide UI state, particularly the modal interaction system.
 * This store serves as the central hub for controlling which modal is currently active,
 * enabling a unified and consistent modal management approach across the application.
 * 
 * Design Philosophy:
 * - Single source of truth for modal state
 * - Simple, predictable API (open/close)
 * - Type-safe modal routing
 */

import { create } from 'zustand';

/**
 * Valid modal types that can be displayed in the application.
 * Each modal type corresponds to a specific control panel or interaction mode.
 * 
 * - 'identity': Identity management panel
 * - 'config': System configuration panel
 * - 'prompt': Prompt engineering panel
 * - null: No modal is currently active
 */
export type ModalType = 'identity' | 'config' | 'prompt' | null;

/**
 * UI state shape
 */
interface UIState {
  /** Currently active modal, or null if no modal is open */
  activeModal: ModalType;
}

/**
 * UI actions for state manipulation
 */
interface UIActions {
  /** 
   * Open a specific modal by type.
   * Opening a new modal while one is already open will replace the current modal.
   */
  openModal: (modalType: Exclude<ModalType, null>) => void;
  
  /** 
   * Close the currently active modal.
   * Safe to call even when no modal is open.
   */
  closeModal: () => void;
}

/**
 * Complete UI store type
 */
export type UIStore = UIState & UIActions;

/**
 * Global UI state store
 * 
 * @example
 * ```tsx
 * // Open a modal
 * const { openModal } = useUIStore();
 * openModal('identity');
 * 
 * // Close the active modal
 * const { closeModal } = useUIStore();
 * closeModal();
 * 
 * // Check which modal is active
 * const { activeModal } = useUIStore();
 * const isIdentityOpen = activeModal === 'identity';
 * ```
 */
export const useUIStore = create<UIStore>((set) => ({
  // Initial state
  activeModal: null,

  // Actions
  openModal: (modalType) => {
    set({ activeModal: modalType });
  },

  closeModal: () => {
    set({ activeModal: null });
  },
}));

