/**
 * IdentityPanel Component
 * 
 * The sovereign identity management interface for YX Nexus.
 * This panel is the physical manifestation of user's "self-sovereignty" -
 * a secure, intuitive tool for managing cryptographic identity.
 * 
 * Design Philosophy:
 * - **Sovereignty Visualization**: This is not just info display, it's ownership incarnate
 * - **State-Driven Clarity**: UI adapts to visitor vs member status with no ambiguity
 * - **Feedback Loop**: Dual feedback - instant in-panel confirmation + permanent chat record
 * 
 * Two Modes:
 * - Visitor Mode: Create or import identity
 * - Member Mode: Export or switch identity
 */

import { useState, useEffect } from 'react';
import { Check, Copy, Download, Upload, UserPlus, Eye, EyeOff, Trash2 } from 'lucide-react';
import { Button, Textarea } from '@/components/ui';
import { useChatStore } from '@/features/chat/store/chatStore';
import { useUIStore } from '@/stores/uiStore';
import { IdentityService } from '@/services/identity/identity';
import { websocketManager } from '@/services/websocket/manager';
import { v4 as uuidv4 } from 'uuid';
import type { Message } from '@/features/chat/types';

type FeedbackState = 'idle' | 'loading' | 'success' | 'error';

interface ActionFeedback {
  state: FeedbackState;
  message?: string;
}

export const IdentityPanel: React.FC = () => {
  const visitorMode = useChatStore((state) => state.visitorMode);
  const closeModal = useUIStore((state) => state.closeModal);
  
  const [publicKey, setPublicKey] = useState<string>('');
  const [mnemonicInput, setMnemonicInput] = useState<string>('');
  const [exportedMnemonic, setExportedMnemonic] = useState<string | null>(null);
  const [showMnemonic, setShowMnemonic] = useState<boolean>(false);
  const [showImportInput, setShowImportInput] = useState<boolean>(false);
  
  const [createFeedback, setCreateFeedback] = useState<ActionFeedback>({ state: 'idle' });
  const [importFeedback, setImportFeedback] = useState<ActionFeedback>({ state: 'idle' });
  const [exportFeedback, setExportFeedback] = useState<ActionFeedback>({ state: 'idle' });
  const [resetFeedback, setResetFeedback] = useState<ActionFeedback>({ state: 'idle' });
  const [showResetConfirm, setShowResetConfirm] = useState<boolean>(false);

  // Load current identity on mount
  useEffect(() => {
    const loadIdentity = async () => {
      try {
        const identity = await IdentityService.getIdentity();
        setPublicKey(identity.publicKey);
      } catch (error) {
        console.error('Failed to load identity:', error);
      }
    };
    loadIdentity();
  }, []);

  // Auto-clear success feedback after 3 seconds
  useEffect(() => {
    if (createFeedback.state === 'success') {
      const timer = setTimeout(() => setCreateFeedback({ state: 'idle' }), 3000);
      return () => clearTimeout(timer);
    }
  }, [createFeedback.state]);

  useEffect(() => {
    if (importFeedback.state === 'success') {
      const timer = setTimeout(() => setImportFeedback({ state: 'idle' }), 3000);
      return () => clearTimeout(timer);
    }
  }, [importFeedback.state]);

  useEffect(() => {
    if (exportFeedback.state === 'success') {
      const timer = setTimeout(() => setExportFeedback({ state: 'idle' }), 3000);
      return () => clearTimeout(timer);
    }
  }, [exportFeedback.state]);

  useEffect(() => {
    if (resetFeedback.state === 'success') {
      const timer = setTimeout(() => setResetFeedback({ state: 'idle' }), 3000);
      return () => clearTimeout(timer);
    }
  }, [resetFeedback.state]);

  /**
   * Create new identity via WebSocket /identity command
   * For visitor mode, this will clear any old identity and create a fresh one with mnemonic
   */
  const handleCreateIdentity = async () => {
    setCreateFeedback({ state: 'loading' });
    
    try {
      // In visitor mode, ensure we create a completely new identity
      // Clear any old/legacy identity from localStorage first
      if (visitorMode && IdentityService.hasIdentity()) {
        console.log('🧹 Clearing old identity before creating new one...');
        IdentityService.clearIdentity();
      }
      
      // Generate new identity with mnemonic support
      // This must be called AFTER clearing old identity to ensure a fresh one is created
      console.log('🔑 Generating new identity with mnemonic support...');
      const newIdentity = await IdentityService.getIdentity();
      console.log('✅ New identity created:', newIdentity.publicKey);
      
      // Create PENDING system message (waiting for backend confirmation)
      // This follows the standard WebSocket command flow: pending → completed
      const pendingMsg: Message = {
        id: uuidv4(),
        role: 'SYSTEM',
        content: { 
          command: '/identity', 
          result: '身份已在 NEXUS 系统中创建...' 
        },
        timestamp: new Date(),
        metadata: { status: 'pending' }
      };
      useChatStore.setState((state) => ({
        messages: [...state.messages, pendingMsg]
      }));
      
      // Sign and send /identity command to backend to register in database
      const auth = await IdentityService.signCommand('/identity');
      websocketManager.sendCommand('/identity', auth);
      
      // Show in-panel success feedback (immediate UI feedback)
      // Note: This is separate from the chat message flow
      setCreateFeedback({ 
        state: 'success', 
        message: '身份已创建！' 
      });
      
      // Reconnect WebSocket to establish member session
      await websocketManager.reconnect();
      
      // handleCommandResult will automatically update the pending message to completed
      // when the backend returns the result
      
      // Close modal after short delay
      setTimeout(() => {
        closeModal();
      }, 1500);
      
    } catch (error) {
      console.error('Failed to create identity:', error);
      setCreateFeedback({ 
        state: 'error', 
        message: error instanceof Error ? error.message : '创建失败' 
      });
    }
  };

  /**
   * Import identity from mnemonic phrase
   */
  const handleImportIdentity = async () => {
    if (!mnemonicInput.trim()) {
      setImportFeedback({ 
        state: 'error', 
        message: '请输入助记词' 
      });
      return;
    }

    setImportFeedback({ state: 'loading' });
    
    try {
      // Import identity from mnemonic (overwrites localStorage)
      const newPublicKey = await IdentityService.importFromMnemonic(mnemonicInput);
      
      // Show in-panel success feedback
      setImportFeedback({ 
        state: 'success', 
        message: '身份已导入！' 
      });
      
      // Reconnect WebSocket with new identity
      await websocketManager.reconnect(newPublicKey);
      
      // Create system message for chat history (permanent record)
      // Note: Import is a pure frontend operation, so we create a completed message directly
      const completedMsg: Message = {
        id: uuidv4(),
        role: 'SYSTEM',
        content: { 
          command: '/identity/import', 
          result: `身份已导入。存在地址：${newPublicKey}`
        },
        timestamp: new Date(),
        metadata: { 
          status: 'completed',
          commandResult: {
            status: 'success',
            data: { public_key: newPublicKey, action: 'import' }
          }
        }
      };
      useChatStore.setState((state) => ({
        messages: [...state.messages, completedMsg]
      }));
      
      // Close modal after short delay
      setTimeout(() => {
        closeModal();
        setMnemonicInput('');
        setShowImportInput(false);
      }, 1500);
      
    } catch (error) {
      console.error('Failed to import identity:', error);
      setImportFeedback({ 
        state: 'error', 
        message: error instanceof Error ? error.message : '导入失败' 
      });
    }
  };

  /**
   * Export mnemonic phrase for backup
   */
  const handleExportMnemonic = () => {
    setExportFeedback({ state: 'loading' });
    
    try {
      const mnemonic = IdentityService.exportMnemonic();
      
      setExportedMnemonic(mnemonic);
      setShowMnemonic(true);
      setExportFeedback({ 
        state: 'success', 
        message: '助记词已显示' 
      });
      
    } catch (error) {
      console.error('Failed to export mnemonic:', error);
      setExportFeedback({ 
        state: 'error', 
        message: error instanceof Error ? error.message : '导出失败' 
      });
    }
  };

  /**
   * Copy mnemonic to clipboard
   */
  const handleCopyMnemonic = async () => {
    if (!exportedMnemonic) return;
    
    try {
      await navigator.clipboard.writeText(exportedMnemonic);
      setExportFeedback({ 
        state: 'success', 
        message: '助记词已复制！' 
      });
    } catch (error) {
      console.error('Failed to copy mnemonic:', error);
      setExportFeedback({ 
        state: 'error', 
        message: '复制失败' 
      });
    }
  };

  /**
   * Clear/Reset current identity
   * This deletes the identity from both backend database and local storage
   */
  const handleResetIdentity = async () => {
    setResetFeedback({ state: 'loading' });
    
    try {
      // Step 1: Create PENDING system message (waiting for backend confirmation)
      // This follows the standard WebSocket command flow: pending → completed
      const pendingMsg: Message = {
        id: uuidv4(),
        role: 'SYSTEM',
        content: { 
          command: '/identity/delete', 
          result: '正在从 NEXUS 系统清除身份...' 
        },
        timestamp: new Date(),
        metadata: { status: 'pending' }
      };
      useChatStore.setState((state) => ({
        messages: [...state.messages, pendingMsg]
      }));
      
      // Step 2: Sign and send delete request to backend (before clearing localStorage)
      console.log('Deleting identity from backend database...');
      const auth = await IdentityService.signCommand('/identity/delete');
      websocketManager.sendCommand('/identity/delete', auth);
      
      // Wait briefly for backend to process
      await new Promise(resolve => setTimeout(resolve, 300));
      
      // Step 3: Clear identity from localStorage (private key + mnemonic)
      console.log('🧹 Clearing local identity data...');
      IdentityService.clearIdentity();
      
      // handleCommandResult will automatically update the pending message to completed
      // when the backend returns the result
      
      // Show in-panel success feedback (immediate UI feedback)
      setResetFeedback({ 
        state: 'success', 
        message: '身份已完全清除' 
      });
      
      // Close modal and cleanup
      closeModal();
      websocketManager.disconnect();
      
      // Reload page to reset to visitor mode
      setTimeout(() => {
        window.location.reload();
      }, 500);
    } catch (error) {
      console.error('Failed to reset identity:', error);
      setResetFeedback({ 
        state: 'error', 
        message: error instanceof Error ? error.message : '清除失败' 
      });
    }
  };

  /**
   * Render feedback indicator
   */
  const renderFeedback = (feedback: ActionFeedback) => {
    if (feedback.state === 'idle') return null;
    
    return (
      <div className="flex items-center gap-2 text-sm">
        {feedback.state === 'success' && (
          <>
            <Check size={16} className="text-green-500" />
            <span className="text-green-500">{feedback.message}</span>
          </>
        )}
        {feedback.state === 'error' && (
          <span className="text-red-500">{feedback.message}</span>
        )}
      </div>
    );
  };

  // Visitor View
  if (visitorMode) {
    return (
      <div className="space-y-6">
        {/* Guidance Text */}
        <div className="p-4 bg-muted/30 rounded-lg border border-border/40">
          <p className="text-sm text-muted-foreground">
            您当前为<span className="font-medium text-foreground">访客身份</span>，无法使用全部服务。
            创建或导入身份后，您将获得完整的服务能力。
          </p>
        </div>

        {/* Create Identity Button */}
        <div className="space-y-2">
          <Button
            variant="primary"
            icon={<UserPlus size={18} />}
            onClick={handleCreateIdentity}
            disabled={createFeedback.state === 'loading'}
            fullWidth
          >
            {createFeedback.state === 'loading' ? '创建中...' : '创建新身份'}
          </Button>
          {renderFeedback(createFeedback)}
        </div>

        {/* Import Identity Section */}
        <div className="space-y-3 pt-4 border-t border-border">
          {!showImportInput ? (
            <Button
              variant="outline"
              icon={<Upload size={18} />}
              onClick={() => setShowImportInput(true)}
              fullWidth
            >
              导入已有身份
            </Button>
          ) : (
            <div className="space-y-3">
              <Textarea
                value={mnemonicInput}
                onChange={(e) => setMnemonicInput(e.target.value)}
                placeholder="请输入助记词"
                minRows={3}
                className="h-24 text-sm"
              />
              <div className="flex gap-2">
                <Button
                  variant="primary"
                  onClick={handleImportIdentity}
                  disabled={importFeedback.state === 'loading' || !mnemonicInput.trim()}
                  className="flex-1"
                >
                  {importFeedback.state === 'loading' ? '导入中...' : '确认导入'}
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setShowImportInput(false);
                    setMnemonicInput('');
                    setImportFeedback({ state: 'idle' });
                  }}
                >
                  取消
                </Button>
              </div>
              {renderFeedback(importFeedback)}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Member View
  return (
    <div className="space-y-6">
      {/* Public Key Display */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-muted-foreground">存在地址 (Public Key)</label>
        <div className="p-3 bg-muted/30 rounded-lg border border-border/40">
          <code className="text-xs text-foreground break-all">
            {publicKey || '加载中...'}
          </code>
        </div>
      </div>

      {/* Export Mnemonic Section */}
      <div className="space-y-3">
        <Button
          variant="primary"
          icon={<Download size={18} />}
          onClick={handleExportMnemonic}
          disabled={exportFeedback.state === 'loading'}
          fullWidth
        >
          {exportFeedback.state === 'loading' ? '导出中...' : '导出身份（备份）'}
        </Button>
        
        {exportedMnemonic && (
          <div className="space-y-3 p-4 bg-muted/30 rounded-lg border border-border/40">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">助记词</span>
              <Button
                variant="ghost"
                size="sm"
                icon={showMnemonic ? <EyeOff size={16} /> : <Eye size={16} />}
                iconOnly
                onClick={() => setShowMnemonic(!showMnemonic)}
                aria-label={showMnemonic ? "隐藏助记词" : "显示助记词"}
              />
            </div>
            
            {showMnemonic && (
              <div className="space-y-3">
                <div className="p-3 bg-background rounded border border-border">
                  <p className="text-sm text-foreground font-mono break-all">
                    {exportedMnemonic}
                  </p>
                </div>
                
                <Button
                  variant="outline"
                  icon={<Copy size={18} />}
                  onClick={handleCopyMnemonic}
                  fullWidth
                >
                  复制到剪贴板
                </Button>
                
                <p className="text-xs text-red-500">
                  ⚠️ 请妥善保管助记词，切勿泄露。助记词是恢复/切换身份的唯一凭证。
                </p>
              </div>
            )}
          </div>
        )}
        
        {renderFeedback(exportFeedback)}
      </div>

      {/* Import/Switch Identity Section */}
      <div className="space-y-3 pt-4 border-t border-border">
        {!showImportInput ? (
          <Button
            variant="outline"
            icon={<Upload size={18} />}
            onClick={() => setShowImportInput(true)}
            fullWidth
          >
            切换/导入身份
          </Button>
        ) : (
          <div className="space-y-3">
            <Textarea
              value={mnemonicInput}
              onChange={(e) => setMnemonicInput(e.target.value)}
              placeholder="请输入助记词"
              minRows={3}
              className="h-24 text-sm"
            />
            <div className="flex gap-2">
              <Button
                variant="primary"
                onClick={handleImportIdentity}
                disabled={importFeedback.state === 'loading' || !mnemonicInput.trim()}
                className="flex-1"
              >
                {importFeedback.state === 'loading' ? '导入中...' : '确认导入'}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setShowImportInput(false);
                  setMnemonicInput('');
                  setImportFeedback({ state: 'idle' });
                }}
              >
                取消
              </Button>
            </div>
            {renderFeedback(importFeedback)}
          </div>
        )}
      </div>

      {/* Reset Identity Section */}
      <div className="space-y-3 pt-4 border-t border-border border-dashed">
        <div className="p-3 bg-muted/20 rounded-lg border border-border/30">
          <p className="text-xs text-muted-foreground mb-3">
            ⚠️ 危险操作：清除当前身份将删除本地存储的密钥。如果您没有备份助记词，将<span className="text-red-500 font-medium">永久丢失</span>此身份！
          </p>
          
          {!showResetConfirm ? (
            <Button
              variant="ghost"
              icon={<Trash2 size={16} />}
              onClick={() => setShowResetConfirm(true)}
              fullWidth
              className="text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20"
            >
              清除当前身份
            </Button>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-red-600 dark:text-red-400 font-medium">
                确认要清除当前身份吗？此操作不可撤销！
              </p>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  onClick={handleResetIdentity}
                  disabled={resetFeedback.state === 'loading'}
                  className="flex-1 bg-red-500 hover:bg-red-600 text-white"
                >
                  {resetFeedback.state === 'loading' ? '清除中...' : '确认清除'}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowResetConfirm(false);
                    setResetFeedback({ state: 'idle' });
                  }}
                  className="flex-1"
                >
                  取消
                </Button>
              </div>
              {renderFeedback(resetFeedback)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

