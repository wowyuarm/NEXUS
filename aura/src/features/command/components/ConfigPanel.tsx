/**
 * ConfigPanel Component - Runtime Configuration GUI
 * 
 * Backend-driven configuration panel that dynamically generates form controls
 * based on metadata returned from GET /api/v1/config.
 * 
 * Design Standards (matching IdentityPanel):
 * - Fixed height: 360px
 * - Consistent padding: px-7 py-4
 * - Section spacing: space-y-3 (compact layout)
 * - Help button inline with first label for space efficiency
 * - Grayscale only (no color emphasis)
 * - Smooth page transitions with FRAMER.reveal (350ms slide animation)
 * - Footer integrated within fixed container
 */

import { useState, useEffect, useMemo } from 'react';
import { Loader2, Check, HelpCircle, ArrowLeft } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button, Select, Slider, Input } from '@/components/ui';
import { useUIStore } from '@/stores/uiStore';
import { fetchConfig, saveConfig, type ConfigResponse } from '@/features/command/api';
import { IdentityService } from '@/services/identity/identity';
import { useChatStore } from '@/features/chat/store/chatStore';
import { v4 as uuidv4 } from 'uuid';
import { FRAMER } from '@/lib/motion';
import type { Message } from '@/features/chat/types';

// ============================================================================
// Types
// ============================================================================

type LoadingState = 'idle' | 'loading' | 'success' | 'error';
type PanelMode = 'main' | 'help';

interface FieldOption {
  type: 'select' | 'slider' | 'number' | 'text';
  label: string;
  options?: string[];
  min?: number;
  max?: number;
  step?: number;
  description?: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format number for display based on step size
 * 
 * @param value - The number to format
 * @param step - The step size (determines decimal places)
 * @returns Formatted number string
 */
function formatNumberValue(value: number, step: number = 0.01): string {
  if (Number.isInteger(value)) {
    return value.toString();
  }
  
  // Determine decimal places based on step
  // step >= 0.1 → 1 decimal (e.g., temperature: 0.8)
  // step < 0.1  → 2 decimals (e.g., top_p: 0.95)
  const decimals = step >= 0.1 ? 1 : 2;
  return value.toFixed(decimals);
}

/**
 * Canonicalize JSON for signing (matches backend format)
 * 
 * Produces deterministic JSON string matching Python's:
 * json.dumps(data, separators=(',', ':'), sort_keys=True)
 * 
 * Critical for signature verification - any difference in whitespace
 * or key order will cause signature mismatch.
 * 
 * @param obj - Object to serialize
 * @returns Canonical JSON string (compact, sorted keys)
 */
function canonicalizeJSON(obj: unknown): string {
  if (obj === null) return 'null';
  if (typeof obj !== 'object') return JSON.stringify(obj);
  if (Array.isArray(obj)) {
    return '[' + obj.map(canonicalizeJSON).join(',') + ']';
  }
  
  // Sort keys alphabetically for deterministic output
  const keys = Object.keys(obj).sort();
  const pairs = keys.map(key => `"${key}":${canonicalizeJSON(obj[key as keyof typeof obj])}`);
  return '{' + pairs.join(',') + '}';
}

// ============================================================================
// Component
// ============================================================================

export const ConfigPanel: React.FC = () => {
  const closeModal = useUIStore((state) => state.closeModal);

  // ============================================================================
  // State
  // ============================================================================

  const [mode, setMode] = useState<PanelMode>('main');
  const [loadingState, setLoadingState] = useState<LoadingState>('loading');
  const [configData, setConfigData] = useState<ConfigResponse | null>(null);
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const [initialValues, setInitialValues] = useState<Record<string, unknown>>({});
  const [saveState, setSaveState] = useState<LoadingState>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');

  // ============================================================================
  // Data Loading
  // ============================================================================

  useEffect(() => {
    const loadConfig = async () => {
      try {
        setLoadingState('loading');
        const data = await fetchConfig();
        setConfigData(data);

        // Initialize form values from effective_config
        const initialFormValues: Record<string, unknown> = {};
        data.editable_fields.forEach((fieldPath) => {
          if (fieldPath.startsWith('config.')) {
            const key = fieldPath.replace('config.', '');
            initialFormValues[key] = data.effective_config[key];
          }
        });

        setFormValues(initialFormValues);
        setInitialValues(initialFormValues);
        setLoadingState('success');
      } catch (error) {
        console.error('Failed to load config:', error);
        // Set error state only - don't use errorMessage toast for initial load failures
        setLoadingState('error');
      }
    };

    loadConfig();
  }, []);

  // Auto-clear errors
  useEffect(() => {
    if (errorMessage) {
      const timer = setTimeout(() => setErrorMessage(''), 3000);
      return () => clearTimeout(timer);
    }
  }, [errorMessage]);

  // ============================================================================
  // Change Detection
  // ============================================================================

  const hasChanges = useMemo(() => {
    return Object.keys(formValues).some(
      (key) => formValues[key] !== initialValues[key]
    );
  }, [formValues, initialValues]);

  const calculateDiff = (): Record<string, unknown> => {
    const diff: Record<string, unknown> = {};
    Object.keys(formValues).forEach((key) => {
      if (formValues[key] !== initialValues[key]) {
        diff[key] = formValues[key];
      }
    });
    return diff;
  };

  // ============================================================================
  // Save Handler
  // ============================================================================

  const handleSave = async () => {
    if (!hasChanges) return;

    setSaveState('loading');

    try {
      // 1. Get identity (single source of truth)
      const identity = await IdentityService.getIdentity();

      // 2. Calculate diff
      const changes = calculateDiff();

      // 3. Build request body payload (without auth)
      const requestPayload = { overrides: changes };
      
      // 4. Canonicalize payload (match backend: sort_keys=True, separators=(',', ':'))
      const payloadString = canonicalizeJSON(requestPayload);

      // 5. Sign the payload (not the command string!)
      const auth = await IdentityService.signData(payloadString);

      // 6. Verify auth publicKey matches identity (prevent timing issues)
      if (auth.publicKey.toLowerCase() !== identity.publicKey.toLowerCase()) {
        throw new Error('Identity mismatch during signing');
      }

      // 7. Save to backend
      const result = await saveConfig(changes, auth);

      // 8. Show success feedback
      setSaveState('success');

      // 9. Add SYSTEM message to chat
      const systemMsg: Message = {
        id: uuidv4(),
        role: 'SYSTEM',
        content: {
          command: '/config',
          result: '配置已成功更新。',
        },
        timestamp: new Date(),
        metadata: {
          status: 'completed',
          commandResult: {
            status: 'success',
            message: result.message,
            data: { updated_fields: Object.keys(changes) },
          },
        },
      };

      useChatStore.setState((state) => ({
        messages: [...state.messages, systemMsg],
      }));

      // 10. Close modal after brief delay (Scene Change duration + buffer for user to see success)
      setTimeout(() => {
        closeModal();
      }, FRAMER.scene.duration * 1000 + 200);
    } catch (error) {
      console.error('Failed to save config:', error);
      setErrorMessage(error instanceof Error ? error.message : '保存失败');
      setSaveState('error');
      setTimeout(() => setSaveState('idle'), 2000);
    }
  };

  // ============================================================================
  // Dynamic Field Rendering
  // ============================================================================

  const renderField = (fieldPath: string) => {
    if (!configData) return null;

    const fieldOption = configData.field_options[fieldPath] as FieldOption | undefined;
    if (!fieldOption) return null;

    const key = fieldPath.replace('config.', '');
    const value = formValues[key];

    const handleChange = (newValue: unknown) => {
      setFormValues((prev) => ({ ...prev, [key]: newValue }));
    };

    switch (fieldOption.type) {
      case 'select':
        return (
          <div key={fieldPath} className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide block">
              {fieldOption.label}
            </label>
            <Select
              value={(value as string) || ''}
              onValueChange={handleChange}
              options={(fieldOption.options || []).map((opt) => ({
                value: opt,
                label: opt,
              }))}
              placeholder="Select..."
            />
            {fieldOption.description && (
              <p className="text-xs text-muted-foreground/70">{fieldOption.description}</p>
            )}
          </div>
        );

      case 'slider':
        return (
          <div key={fieldPath} className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                {fieldOption.label || key}
              </label>
              <span className="text-sm font-mono text-foreground">
                {typeof value === 'number' 
                  ? formatNumberValue(value, fieldOption.step ?? 0.01)
                  : String(value ?? '')}
              </span>
            </div>
            <Slider
              value={[value as number]}
              onValueChange={([newValue]) => handleChange(newValue)}
              min={fieldOption.min ?? 0}
              max={fieldOption.max ?? 1}
              step={fieldOption.step ?? 0.01}
            />
            {fieldOption.description && (
              <p className="text-xs text-muted-foreground/70">{fieldOption.description}</p>
            )}
          </div>
        );

      case 'number':
        return (
          <div key={fieldPath} className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide block">
              {fieldOption.label}
            </label>
            <Input
              type="number"
              value={(value as number) ?? ''}
              onChange={(e) => handleChange(Number(e.target.value))}
              min={fieldOption.min}
              max={fieldOption.max}
              step={fieldOption.step}
            />
            {fieldOption.description && (
              <p className="text-xs text-muted-foreground/70">{fieldOption.description}</p>
            )}
          </div>
        );

      default:
        return (
          <div key={fieldPath} className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide block">
              {fieldOption.label}
            </label>
            <Input
              type="text"
              value={value as string}
              onChange={(e) => handleChange(e.target.value)}
            />
          </div>
        );
    }
  };

  // ============================================================================
  // Render States
  // ============================================================================

  const renderLoading = () => (
    <div className="flex items-center justify-center h-full">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={FRAMER.transition}
        className="flex items-center gap-2 text-muted-foreground"
      >
        <Loader2 size={20} className="animate-spin" />
        <span className="text-sm">正在加载配置...</span>
      </motion.div>
    </div>
  );

  const renderError = () => (
    <div className="flex items-center justify-center h-full">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={FRAMER.transition}
        className="space-y-4 text-center"
      >
        <div className="px-4 py-3 bg-foreground/[0.02] rounded-lg border border-border/40">
          <p className="text-sm text-foreground/70">
            无法加载配置。请检查网络连接。
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => window.location.reload()}
        >
          重试
        </Button>
      </motion.div>
    </div>
  );

  const renderMainMode = () => {
    if (!configData) return null;

    const configFields = configData.editable_fields.filter((f) =>
      f.startsWith('config.')
    );

    // Separate model field from other fields
    const modelFieldPath = 'config.model';
    const hasModelField = configFields.includes(modelFieldPath);
    const otherFields = configFields.filter((f) => f !== modelFieldPath);

    return (
      <div className="space-y-3">
        {/* Model Selection with Help Button */}
        {hasModelField && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                MODEL
              </label>
              <button
                onClick={() => setMode('help')}
                className="text-muted-foreground hover:text-foreground transition-colors duration-150"
                aria-label="配置说明"
              >
                <HelpCircle size={16} />
              </button>
            </div>
            <Select
              value={(formValues.model as string) || ''}
              onValueChange={(newValue) => setFormValues((prev) => ({ ...prev, model: newValue }))}
              options={((configData.field_options[modelFieldPath] as FieldOption)?.options || []).map((opt) => ({
                value: opt,
                label: opt,
              }))}
              placeholder="Select model..."
            />
          </div>
        )}

        {/* Other Config Fields */}
        <div className="space-y-3">
          {otherFields.map((fieldPath) => renderField(fieldPath))}
        </div>
      </div>
    );
  };

  const renderHelpMode = () => (
    <div className="space-y-3.5">
      {/* Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setMode('main')}
          className="text-muted-foreground hover:text-foreground transition-colors duration-150"
          aria-label="返回"
        >
          <ArrowLeft size={18} />
        </button>
        <h3 className="text-base font-medium text-foreground">配置说明</h3>
        <div className="w-[18px]" /> {/* Spacer for centering */}
      </div>

      {/* Help content uses larger spacing (space-y-5) for better readability of documentation sections */}
      <div className="space-y-5">
        {/* Model */}
        <div className="space-y-2">
          <h4 className="text-sm font-bold text-foreground uppercase tracking-wide">
            模型选择 (Model)
          </h4>
          <p className="text-sm text-muted-foreground leading-relaxed">
            选择 AI 对话使用的<span className="font-medium text-foreground">语言模型</span>。
            不同模型在速度、成本和能力上有所差异。
          </p>
        </div>

        {/* Temperature */}
        <div className="space-y-2">
          <h4 className="text-sm font-bold text-foreground uppercase tracking-wide">
            温度 (Temperature)
          </h4>
          <p className="text-sm text-muted-foreground leading-relaxed">
            控制 AI 回复的<span className="font-medium text-foreground">创造性</span>。
            较低值（0.0-0.5）输出更稳定、事实性更强；
            较高值（0.8-2.0）输出更多样、更有创意。推荐值：0.7-1.0。
          </p>
        </div>

        {/* Max Tokens */}
        <div className="space-y-2">
          <h4 className="text-sm font-bold text-foreground uppercase tracking-wide">
            最大令牌数 (Max Tokens)
          </h4>
          <p className="text-sm text-muted-foreground leading-relaxed">
            单次回复的<span className="font-medium text-foreground">最大长度</span>（以 token 计）。
            1 token ≈ 0.75 个英文单词或 0.5 个中文字。
            过高会增加成本和延迟，过低可能导致回复被截断。
          </p>
        </div>

        {/* History Context Size */}
        <div className="space-y-2">
          <h4 className="text-sm font-bold text-foreground uppercase tracking-wide">
            短期记忆 (History Context Size)
          </h4>
          <p className="text-sm text-muted-foreground leading-relaxed">
            控制对话历史的<span className="font-medium text-foreground">长度</span>。
            值越大，AI 能记住越长的对话历史，但会增加成本和延迟。
          </p>
        </div>

        {/* Best Practice */}
        <div className="px-4 py-3 bg-muted/20 rounded-lg border border-border/30">
          <p className="text-xs text-muted-foreground leading-relaxed">
            ✓ 默认配置适用于大多数场景<br/>
            ✓ 编程/技术问题：温度 0.3-0.5<br/>
            ✓ 创意写作：温度 0.8-1.2<br/>
            ✓ 修改后需点击"保存"生效
          </p>
        </div>
      </div>
    </div>
  );

  // ============================================================================
  // Main Render
  // ============================================================================

  return (
    <div className="w-full">
      {/* Fixed height container - prevents layout shifts */}
      <div className="relative overflow-hidden h-[360px]">
        <AnimatePresence mode="wait">
          <motion.div
            key={mode}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={FRAMER.reveal}
            className="absolute inset-0 flex flex-col"
          >
            {/* Scrollable Content Area */}
            <div className={cn(
              "flex-1 overflow-y-auto",
              // Mobile: px-4 py-3 (reduced inner padding)
              "px-4 py-3",
              // Desktop: restore px-7 py-4
              "md:px-7 md:py-4"
            )}>
              {loadingState === 'loading' && renderLoading()}
              {loadingState === 'error' && renderError()}
              {loadingState === 'success' && mode === 'main' && renderMainMode()}
              {loadingState === 'success' && mode === 'help' && renderHelpMode()}
            </div>

            {/* Footer with Save button - Fixed at bottom (only in main mode) */}
            {loadingState === 'success' && mode === 'main' && (
              <div className="px-7 py-4 border-t border-border shrink-0">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-xs text-muted-foreground">
                    {hasChanges ? '有未保存的更改' : '无更改'}
                  </div>
                  <div className="flex items-center gap-2">
                    {saveState === 'success' && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={FRAMER.transition}
                        className="flex items-center gap-1 text-sm text-foreground/70"
                      >
                        <Check size={16} />
                        <span>已保存</span>
                      </motion.div>
                    )}
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleSave}
                      disabled={!hasChanges || saveState === 'loading'}
                      icon={saveState === 'loading' && <Loader2 size={16} className="animate-spin" />}
                    >
                      {saveState === 'loading' ? '保存中...' : '保存'}
                    </Button>
                  </div>
                </div>
              </div>
            )}
            {/* Error Toast - Floating at bottom */}
            <AnimatePresence>
              {errorMessage && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  transition={{
                    duration: FRAMER.reveal.duration,
                    ease: FRAMER.reveal.ease,
                  }}
                  className="mx-7 mb-4 px-4 py-2.5 bg-foreground/5 rounded-lg border border-border/40"
                >
                  <p className="text-sm text-foreground/70 text-center">{errorMessage}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};
