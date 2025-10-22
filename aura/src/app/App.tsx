import { ChatView } from "@/features/chat";
import { useThemeManager } from "@/hooks/useThemeManager";
import { Modal, Panel } from "@/components/common";
import { useUIStore } from "@/stores/uiStore";
import { IdentityPanel } from "@/features/command/components/IdentityPanel";

function App() {
  useThemeManager();
  const activeModal = useUIStore((state) => state.activeModal);
  const closeModal = useUIStore((state) => state.closeModal);

  return (
    <>
      <ChatView />
      
      {/* Identity Management Modal */}
      <Modal isOpen={activeModal === 'identity'} onClose={closeModal}>
        <Panel title="身份管理 (Identity Management)" onClose={closeModal}>
          <IdentityPanel />
        </Panel>
      </Modal>
      
      {/* Future modals can be added here:
          - Config panel: activeModal === 'config'
          - Prompt panel: activeModal === 'prompt'
      */}
    </>
  );
}

export default App;