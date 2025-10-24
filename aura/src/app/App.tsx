import { ChatView } from "@/features/chat";
import { useThemeManager } from "@/hooks/useThemeManager";
import { Modal, Panel } from "@/components/common";
import { useUIStore } from "@/stores/uiStore";
import { IdentityPanel } from "@/features/command/components/IdentityPanel";
import { ConfigPanel } from "@/features/command/components/ConfigPanel";

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
      
      {/* Config Management Modal */}
      <Modal isOpen={activeModal === 'config'} onClose={closeModal}>
        <Panel title="系统配置 (System Configuration)" onClose={closeModal}>
          <ConfigPanel />
        </Panel>
      </Modal>
      
      {/* Future modals can be added here:
          - Prompt panel: activeModal === 'prompt'
      */}
    </>
  );
}

export default App;