import { describe, it, expect, beforeEach } from 'vitest';
import { useUIStore } from '../uiStore';

describe('uiStore', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useUIStore.setState({ activeModal: null });
  });

  describe('Initial state', () => {
    it('should have null as initial activeModal', () => {
      const state = useUIStore.getState();
      expect(state.activeModal).toBeNull();
    });
  });

  describe('openModal action', () => {
    it('should set activeModal to identity', () => {
      const store = useUIStore.getState();
      store.openModal('identity');
      
      const state = useUIStore.getState();
      expect(state.activeModal).toBe('identity');
    });

    it('should set activeModal to config', () => {
      const store = useUIStore.getState();
      store.openModal('config');
      
      const state = useUIStore.getState();
      expect(state.activeModal).toBe('config');
    });

    it('should set activeModal to prompt', () => {
      const store = useUIStore.getState();
      store.openModal('prompt');
      
      const state = useUIStore.getState();
      expect(state.activeModal).toBe('prompt');
    });

    it('should override previous modal when opening a new one', () => {
      const store = useUIStore.getState();
      
      store.openModal('identity');
      expect(useUIStore.getState().activeModal).toBe('identity');
      
      store.openModal('config');
      expect(useUIStore.getState().activeModal).toBe('config');
    });
  });

  describe('closeModal action', () => {
    it('should set activeModal to null', () => {
      const store = useUIStore.getState();
      
      // Open a modal first
      store.openModal('identity');
      expect(useUIStore.getState().activeModal).toBe('identity');
      
      // Close it
      store.closeModal();
      expect(useUIStore.getState().activeModal).toBeNull();
    });

    it('should work even when no modal is open', () => {
      const store = useUIStore.getState();
      
      expect(useUIStore.getState().activeModal).toBeNull();
      
      // Should not throw
      store.closeModal();
      expect(useUIStore.getState().activeModal).toBeNull();
    });
  });
});

