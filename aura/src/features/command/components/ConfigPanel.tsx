/**
 * ConfigPanel Component - Runtime Configuration GUI
 * 
 * Backend-driven configuration panel that dynamically generates form controls
 * based on metadata returned from GET /api/v1/config.
 * 
 * Design Standards (matching IdentityPanel):
 * - Fixed height: 360px
 * - Grayscale only (no color emphasis)
 * - Smooth animations with FRAMER.reveal
 * - Consistent spacing and padding
 */

import { useState, useEffect, useMemo } from 'react';
import { Loader2, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
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
        setErrorMessage(error instanceof Error ? error.message : '加载失败');
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

      // 6. Verify auth publicKey matches identity (防止时序问题)
      if (auth.publicKey.toLowerCase() !== identity.publicKey.toLowerCase()) {
        throw new Error('Identity mismatch during signing');
      }

      // 7. Save to backend
      const result = await saveConfig(changes, auth);

      // 4. Show success feedback
      setSaveState('success');

      // 5. Add SYSTEM message to chat
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

      // 6. Close modal after brief delay
      setTimeout(() => {
        closeModal();
      }, 1000);
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
                {fieldOption.label}
              </label>
              <span className="text-sm font-mono text-foreground">{value as number}</span>
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
              value={value as number}
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
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 size={20} className="animate-spin" />
        <span className="text-sm">加载中...</span>
      </div>
    </div>
  );

  const renderError = () => (
    <div className="flex items-center justify-center h-full">
      <div className="px-4 py-3 bg-foreground/[0.02] rounded-lg border border-border/40">
        <p className="text-sm text-foreground/70 text-center">
          加载失败。请稍后重试。
        </p>
      </div>
    </div>
  );

  const renderForm = () => {
    if (!configData) return null;

    const configFields = configData.editable_fields.filter((f) =>
      f.startsWith('config.')
    );

    return (
      <div className="space-y-4">
        {configFields.map((fieldPath) => renderField(fieldPath))}
      </div>
    );
  };

  // ============================================================================
  // Main Render
  // ============================================================================

  return (
    <div className="w-full">
      {/* Fixed height container */}
      <div className="relative overflow-hidden h-[360px] flex flex-col">
        <AnimatePresence mode="wait">
          <motion.div
            key={loadingState}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={FRAMER.reveal}
            className="flex-1 overflow-y-auto px-7 py-4"
          >
            {loadingState === 'loading' && renderLoading()}
            {loadingState === 'error' && renderError()}
            {loadingState === 'success' && renderForm()}
          </motion.div>
        </AnimatePresence>

        {/* Footer with Save button */}
        {loadingState === 'success' && (
          <div className="px-7 py-4 border-t border-border shrink-0">
            <div className="flex items-center justify-between gap-3">
              <div className="text-xs text-muted-foreground">
                {hasChanges ? '有未保存的更改' : '无更改'}
              </div>
              <div className="flex items-center gap-2">
                {saveState === 'success' && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0 }}
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

        {/* Error Toast */}
        <AnimatePresence>
          {errorMessage && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              transition={FRAMER.transition}
              className="absolute bottom-4 left-7 right-7 px-4 py-2.5 bg-foreground/5 rounded-lg border border-border/40"
            >
              <p className="text-sm text-foreground/70 text-center">{errorMessage}</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};
