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
import { Check, Copy, Download, Upload, UserPlus, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui';
import { useChatStore } from '@/features/chat/store/chatStore';
import { useUIStore } from '@/stores/uiStore';
import { IdentityService } from '@/services/identity/identity';
import { websocketManager } from '@/services/websocket/manager';

type FeedbackState = 'idle' | 'loading' | 'success' | 'error';

interface ActionFeedback {
  state: FeedbackState;
  message?: string;
}

export const IdentityPanel: React.FC = () => {
  const visitorMode = useChatStore((state) => state.visitorMode);
  const createSystemMessage = useChatStore((state) => state.createSystemMessage);
  const closeModal = useUIStore((state) => state.closeModal);
  
  const [publicKey, setPublicKey] = useState<string>('');
  const [mnemonicInput, setMnemonicInput] = useState<string>('');
  const [exportedMnemonic, setExportedMnemonic] = useState<string | null>(null);
  const [showMnemonic, setShowMnemonic] = useState<boolean>(false);
  const [showImportInput, setShowImportInput] = useState<boolean>(false);
  
  const [createFeedback, setCreateFeedback] = useState<ActionFeedback>({ state: 'idle' });
  const [importFeedback, setImportFeedback] = useState<ActionFeedback>({ state: 'idle' });
  const [exportFeedback, setExportFeedback] = useState<ActionFeedback>({ state: 'idle' });

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

  /**
   * Create new identity via WebSocket /identity command
   */
  const handleCreateIdentity = async () => {
    setCreateFeedback({ state: 'loading' });
    
    try {
      // Sign and send /identity command to backend
      const auth = await IdentityService.signCommand('/identity');
      
      // Send command via WebSocket (bypassing GUI routing)
      websocketManager.sendCommand('/identity', auth);
      
      // Wait for backend response via WebSocket event
      // The chatStore will handle the command_result event and update visitorMode
      
      // Show success feedback
      setCreateFeedback({ 
        state: 'success', 
        message: '身份已创建！' 
      });
      
      // Reconnect WebSocket to establish member session
      await websocketManager.reconnect();
      
      // Create system message for permanent record
      createSystemMessage('/identity', '新的主权身份已成功锚定。');
      
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
      
      // Show success feedback
      setImportFeedback({ 
        state: 'success', 
        message: '身份已导入！' 
      });
      
      // Reconnect WebSocket with new identity
      await websocketManager.reconnect(newPublicKey);
      
      // Create system message for permanent record
      createSystemMessage('/identity', `身份已导入。存在地址：${newPublicKey.slice(0, 10)}...${newPublicKey.slice(-8)}`);
      
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
      
      if (!mnemonic) {
        setExportFeedback({ 
          state: 'error', 
          message: '此身份无助记词（旧版本创建）' 
        });
        return;
      }
      
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
        message: '助记词已复制到剪贴板！' 
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
            className="w-full"
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
              className="w-full"
            >
              导入已有身份
            </Button>
          ) : (
            <div className="space-y-3">
              <textarea
                value={mnemonicInput}
                onChange={(e) => setMnemonicInput(e.target.value)}
                placeholder="请输入 12 或 24 个助记词，用空格分隔..."
                className="w-full h-24 px-3 py-2 bg-background border border-border rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
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
          className="w-full"
        >
          {exportFeedback.state === 'loading' ? '导出中...' : '导出身份（备份）'}
        </Button>
        
        {exportedMnemonic && (
          <div className="space-y-3 p-4 bg-muted/30 rounded-lg border border-border/40">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">助记词</span>
              <button
                onClick={() => setShowMnemonic(!showMnemonic)}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {showMnemonic ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
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
                  className="w-full"
                >
                  复制到剪贴板
                </Button>
                
                <p className="text-xs text-red-500">
                  ⚠️ 请妥善保管助记词，切勿泄露。助记词是恢复身份的唯一凭证。
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
            className="w-full"
          >
            切换/导入身份
          </Button>
        ) : (
          <div className="space-y-3">
            <textarea
              value={mnemonicInput}
              onChange={(e) => setMnemonicInput(e.target.value)}
              placeholder="请输入 12 或 24 个助记词，用空格分隔..."
              className="w-full h-24 px-3 py-2 bg-background border border-border rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
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
};

