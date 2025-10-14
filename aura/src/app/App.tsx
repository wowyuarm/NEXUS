import { ChatView } from "@/features/chat";
import { Modal, Panel } from "@/components/common";
import { useUIStore } from "@/stores/uiStore";

function App() {
  const activeModal = useUIStore((state) => state.activeModal);
  const closeModal = useUIStore((state) => state.closeModal);

  return (
    <>
      <ChatView />
      
      {/* Identity Management Modal */}
      <Modal isOpen={activeModal === 'identity'} onClose={closeModal}>
        <Panel title="Identity Management" onClose={closeModal}>
          <div className="text-secondary-foreground space-y-4">
            <p className="text-base">
              Identity Panel Content Goes Here...
            </p>
            <p className="text-sm text-muted-foreground">
              This is a placeholder for the full Identity Panel implementation.
              In the next task, this will be replaced with the complete identity
              management interface.
            </p>
            <div className="mt-6 p-4 bg-muted/30 rounded-lg border border-border/40">
              <p className="text-xs text-muted-foreground">
                <strong>Note:</strong> The modal system is now fully operational. 
                This panel will house identity verification, key management, 
                and sovereign identity controls.
              </p>
            </div>
          </div>
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