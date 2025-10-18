/**
 * IdentityPanel Component
 *
 * The sovereign identity management interface for YX Nexus.
 * This panel is the physical manifestation of user's "self-sovereignty" -
 * a secure, intuitive tool for managing cryptographic identity.
 *
 * Design Philosophy:
 * - **Unified Size**: Consistent panel dimensions prevent layout shifts
 * - **Minimal Animation**: Direct response, no unnecessary transitions
 * - **State-Driven Feedback**: Icons and subtle visual changes over text messages
 * - **Selective Warning Colors**: Deep red only for critical permanent actions
 */

import { useState, useEffect, useCallback } from "react";
import {
    Check,
    Copy,
    Download,
    Upload,
    UserPlus,
    Eye,
    EyeOff,
    Trash2,
    Loader2,
} from "lucide-react";
import { Button, Textarea } from "@/components/ui";
import { useChatStore } from "@/features/chat/store/chatStore";
import { useUIStore } from "@/stores/uiStore";
import { IdentityService } from "@/services/identity/identity";
import { websocketManager } from "@/services/websocket/manager";
import { v4 as uuidv4 } from "uuid";
import { cn } from "@/lib/utils";
import type { Message } from "@/features/chat/types";

export const IdentityPanel: React.FC = () => {
    const visitorMode = useChatStore((state) => state.visitorMode);
    const closeModal = useUIStore((state) => state.closeModal);

    const [publicKey, setPublicKey] = useState<string>("");
    const [mnemonicInput, setMnemonicInput] = useState<string>("");
    const [exportedMnemonic, setExportedMnemonic] = useState<string | null>(
        null,
    );
    const [showMnemonic, setShowMnemonic] = useState<boolean>(false);
    const [showImportInput, setShowImportInput] = useState<boolean>(false);
    const [showResetConfirm, setShowResetConfirm] = useState<boolean>(false);

    // Loading states for buttons
    const [isCreating, setIsCreating] = useState(false);
    const [isImporting, setIsImporting] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const [isResetting, setIsResetting] = useState(false);
    const [isCopied, setIsCopied] = useState(false);

    // Error states - display briefly then clear
    const [importError, setImportError] = useState<string>("");
    const [exportError, setExportError] = useState<string>("");

    // Load current identity on mount
    useEffect(() => {
        const loadIdentity = async () => {
            try {
                const identity = await IdentityService.getIdentity();
                setPublicKey(identity.publicKey);
            } catch (error) {
                console.error("Failed to load identity:", error);
            }
        };
        loadIdentity();
    }, []);

    // Clear errors after 3 seconds
    useEffect(() => {
        if (importError) {
            const timer = setTimeout(() => setImportError(""), 3000);
            return () => clearTimeout(timer);
        }
    }, [importError]);

    useEffect(() => {
        if (exportError) {
            const timer = setTimeout(() => setExportError(""), 3000);
            return () => clearTimeout(timer);
        }
    }, [exportError]);

    /**
     * Create new identity via WebSocket /identity command
     */
    const handleCreateIdentity = async () => {
        setIsCreating(true);

        try {
            // Clear old identity if in visitor mode
            if (visitorMode && IdentityService.hasIdentity()) {
                console.log(
                    "🧹 Clearing old identity before creating new one...",
                );
                IdentityService.clearIdentity();
            }

            // Generate new identity with mnemonic support
            console.log("🔑 Generating new identity with mnemonic support...");
            const newIdentity = await IdentityService.getIdentity();
            console.log("✅ New identity created:", newIdentity.publicKey);

            // Create PENDING system message
            const pendingMsg: Message = {
                id: uuidv4(),
                role: "SYSTEM",
                content: {
                    command: "/identity",
                    result: "身份已在 NEXUS 系统中创建...",
                },
                timestamp: new Date(),
                metadata: { status: "pending" },
            };
            useChatStore.setState((state) => ({
                messages: [...state.messages, pendingMsg],
            }));

            // Sign and send /identity command to backend
            const auth = await IdentityService.signCommand("/identity");
            websocketManager.sendCommand("/identity", auth);

            // Reconnect WebSocket to establish member session
            await websocketManager.reconnect();

            // Close modal after short delay
            setTimeout(() => {
                closeModal();
            }, 1500);
        } catch (error) {
            console.error("Failed to create identity:", error);
        } finally {
            setIsCreating(false);
        }
    };

    /**
     * Import identity from mnemonic phrase
     */
    const handleImportIdentity = async () => {
        if (!mnemonicInput.trim()) {
            setImportError("请输入助记词");
            return;
        }

        setIsImporting(true);
        setImportError("");

        try {
            // Import identity from mnemonic
            const newPublicKey =
                await IdentityService.importFromMnemonic(mnemonicInput);

            // Reconnect WebSocket with new identity
            await websocketManager.reconnect(newPublicKey);

            // Create system message for chat history
            const completedMsg: Message = {
                id: uuidv4(),
                role: "SYSTEM",
                content: {
                    command: "/identity/import",
                    result: `身份已导入。存在地址：${newPublicKey}`,
                },
                timestamp: new Date(),
                metadata: {
                    status: "completed",
                    commandResult: {
                        status: "success",
                        data: { public_key: newPublicKey, action: "import" },
                    },
                },
            };
            useChatStore.setState((state) => ({
                messages: [...state.messages, completedMsg],
            }));

            // Close modal after short delay
            setTimeout(() => {
                closeModal();
                setMnemonicInput("");
                setShowImportInput(false);
            }, 1500);
        } catch (error) {
            console.error("Failed to import identity:", error);
            setImportError(error instanceof Error ? error.message : "导入失败");
        } finally {
            setIsImporting(false);
        }
    };

    /**
     * Export mnemonic phrase for backup
     */
    const handleExportMnemonic = () => {
        setIsExporting(true);
        setExportError(""); // Clear previous errors

        try {
            const mnemonic = IdentityService.exportMnemonic();
            setExportedMnemonic(mnemonic);
            setShowMnemonic(true);
        } catch (error) {
            console.error("Failed to export mnemonic:", error);
            setExportError(error instanceof Error ? error.message : "导出失败");
        } finally {
            setIsExporting(false);
        }
    };

    /**
     * Copy mnemonic to clipboard with icon feedback
     */
    const handleCopyMnemonic = useCallback(async () => {
        if (!exportedMnemonic || isCopied) return;

        try {
            await navigator.clipboard.writeText(exportedMnemonic);
            setIsCopied(true);

            // Reset after 2 seconds
            setTimeout(() => setIsCopied(false), 2000);
        } catch (error) {
            console.error("Failed to copy mnemonic:", error);
        }
    }, [exportedMnemonic, isCopied]);

    /**
     * Clear/Reset current identity
     */
    const handleResetIdentity = async () => {
        setIsResetting(true);

        try {
            // Create PENDING system message
            const pendingMsg: Message = {
                id: uuidv4(),
                role: "SYSTEM",
                content: {
                    command: "/identity/delete",
                    result: "正在从 NEXUS 系统清除身份...",
                },
                timestamp: new Date(),
                metadata: { status: "pending" },
            };
            useChatStore.setState((state) => ({
                messages: [...state.messages, pendingMsg],
            }));

            // Sign and send delete request to backend
            console.log("Deleting identity from backend database...");
            const auth = await IdentityService.signCommand("/identity/delete");
            websocketManager.sendCommand("/identity/delete", auth);

            // Wait briefly for backend to process
            await new Promise((resolve) => setTimeout(resolve, 300));

            // Clear identity from localStorage
            console.log("🧹 Clearing local identity data...");
            IdentityService.clearIdentity();

            // Close modal and cleanup
            closeModal();
            websocketManager.disconnect();

            // Reload page to reset to visitor mode
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } catch (error) {
            console.error("Failed to reset identity:", error);
        } finally {
            setIsResetting(false);
        }
    };

    // Visitor View - Simplified and centered
    if (visitorMode) {
        return (
            <div className="min-h-[380px] flex flex-col">
                {/* Guidance Text */}
                <div className="p-4 bg-muted/20 rounded-lg border border-border/40 mb-6">
                    <p className="text-sm text-muted-foreground">
                        您当前为
                        <span className="font-medium text-foreground">
                            访客身份
                        </span>
                        ，无法使用全部服务。
                        创建或导入身份后，您将获得完整的服务能力。
                    </p>
                </div>

                {/* Main content area - centered */}
                <div className="flex-1 flex flex-col justify-center space-y-4">
                    {/* Create Identity Button */}
                    <Button
                        variant="primary"
                        icon={
                            isCreating ? (
                                <Loader2 size={18} className="animate-spin" />
                            ) : (
                                <UserPlus size={18} />
                            )
                        }
                        onClick={handleCreateIdentity}
                        disabled={isCreating}
                        fullWidth
                    >
                        {isCreating ? "创建中..." : "创建新身份"}
                    </Button>

                    {/* Import Identity Section - instant toggle */}
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
                                onChange={(e) =>
                                    setMnemonicInput(e.target.value)
                                }
                                placeholder="请输入助记词"
                                minRows={3}
                                className={cn(
                                    "h-24 text-sm",
                                    importError &&
                                        "border-red-950/30 dark:border-red-900/30",
                                )}
                            />
                            {importError && (
                                <p className="text-xs text-muted-foreground">
                                    {importError}
                                </p>
                            )}
                            <div className="flex gap-2">
                                <Button
                                    variant="primary"
                                    icon={
                                        isImporting && (
                                            <Loader2
                                                size={16}
                                                className="animate-spin"
                                            />
                                        )
                                    }
                                    onClick={handleImportIdentity}
                                    disabled={
                                        isImporting || !mnemonicInput.trim()
                                    }
                                    className="flex-1"
                                >
                                    {isImporting ? "导入中..." : "确认导入"}
                                </Button>
                                <Button
                                    variant="ghost"
                                    onClick={() => {
                                        setShowImportInput(false);
                                        setMnemonicInput("");
                                        setImportError("");
                                    }}
                                >
                                    取消
                                </Button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // Member View - Structured with consistent spacing
    return (
        <div className="min-h-[420px] max-h-[500px] flex flex-col">
            <div className="flex-1 space-y-5 overflow-y-auto">
                {/* Public Key Display */}
                <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">
                        存在地址 (Public Key)
                    </label>
                    <div className="p-3 bg-muted/20 rounded-lg border border-border/40">
                        <code className="text-xs text-foreground/80 break-all font-mono">
                            {publicKey || "加载中..."}
                        </code>
                    </div>
                </div>

                {/* Export Mnemonic Section */}
                <div className="space-y-3">
                    <Button
                        variant="primary"
                        icon={
                            isExporting ? (
                                <Loader2 size={18} className="animate-spin" />
                            ) : (
                                <Download size={18} />
                            )
                        }
                        onClick={handleExportMnemonic}
                        disabled={isExporting || exportedMnemonic !== null}
                        fullWidth
                    >
                        {exportedMnemonic ? "助记词已导出" : "导出身份（备份）"}
                    </Button>

                    {exportError && (
                        <div className="p-3 bg-red-950/10 dark:bg-red-900/10 rounded-lg border border-red-950/20 dark:border-red-900/20">
                            <p className="text-sm text-red-950 dark:text-red-900">
                                {exportError}
                            </p>
                        </div>
                    )}

                    {exportedMnemonic && (
                        <div className="space-y-3 p-4 bg-card/50 backdrop-blur-sm rounded-lg border border-border/50">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-foreground">
                                    助记词
                                </span>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    icon={
                                        showMnemonic ? (
                                            <EyeOff size={16} />
                                        ) : (
                                            <Eye size={16} />
                                        )
                                    }
                                    iconOnly
                                    onClick={() =>
                                        setShowMnemonic(!showMnemonic)
                                    }
                                    aria-label={
                                        showMnemonic
                                            ? "隐藏助记词"
                                            : "显示助记词"
                                    }
                                />
                            </div>

                            {showMnemonic && (
                                <div className="space-y-3">
                                    <div className="p-3 bg-background/60 rounded border border-border">
                                        <p className="text-sm text-foreground/90 font-mono break-all leading-relaxed">
                                            {exportedMnemonic}
                                        </p>
                                    </div>

                                    <Button
                                        variant="outline"
                                        icon={
                                            isCopied ? (
                                                <Check size={18} />
                                            ) : (
                                                <Copy size={18} />
                                            )
                                        }
                                        onClick={handleCopyMnemonic}
                                        disabled={isCopied}
                                        fullWidth
                                        className={cn(isCopied && "opacity-60")}
                                    >
                                        {isCopied ? "已复制" : "复制到剪贴板"}
                                    </Button>

                                    <p className="text-xs text-muted-foreground">
                                        ⚠️
                                        请妥善保管助记词，切勿泄露。助记词是恢复身份的唯一凭证。
                                    </p>
                                </div>
                            )}
                        </div>
                    )}
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
                                onChange={(e) =>
                                    setMnemonicInput(e.target.value)
                                }
                                placeholder="请输入助记词"
                                minRows={3}
                                className={cn(
                                    "h-24 text-sm",
                                    importError &&
                                        "border-red-950/30 dark:border-red-900/30",
                                )}
                            />
                            {importError && (
                                <p className="text-xs text-muted-foreground">
                                    {importError}
                                </p>
                            )}
                            <div className="flex gap-2">
                                <Button
                                    variant="primary"
                                    icon={
                                        isImporting && (
                                            <Loader2
                                                size={16}
                                                className="animate-spin"
                                            />
                                        )
                                    }
                                    onClick={handleImportIdentity}
                                    disabled={
                                        isImporting || !mnemonicInput.trim()
                                    }
                                    className="flex-1"
                                >
                                    {isImporting ? "导入中..." : "确认导入"}
                                </Button>
                                <Button
                                    variant="ghost"
                                    onClick={() => {
                                        setShowImportInput(false);
                                        setMnemonicInput("");
                                        setImportError("");
                                    }}
                                >
                                    取消
                                </Button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Reset Identity Section - Danger Zone */}
                <div className="space-y-3 pt-4 border-t border-border border-dashed">
                    <div className="p-3 bg-muted/10 rounded-lg border border-border/20">
                        <p className="text-xs text-muted-foreground mb-3">
                            ⚠️ 危险操作：清除当前身份将删除本地存储的密钥。
                            如果您没有备份助记词，将
                            <span className="text-red-950 dark:text-red-900 font-medium">
                                永久丢失
                            </span>
                            此身份！
                        </p>

                        {!showResetConfirm ? (
                            <Button
                                variant="ghost"
                                icon={<Trash2 size={16} />}
                                onClick={() => setShowResetConfirm(true)}
                                fullWidth
                                className="text-muted-foreground hover:text-red-950 dark:hover:text-red-900"
                            >
                                清除当前身份
                            </Button>
                        ) : (
                            <div className="space-y-2">
                                <p className="text-xs text-red-950 dark:text-red-900 font-medium">
                                    确认要清除当前身份吗？此操作不可撤销！
                                </p>
                                <div className="flex gap-2">
                                    <Button
                                        variant="ghost"
                                        icon={
                                            isResetting && (
                                                <Loader2
                                                    size={16}
                                                    className="animate-spin"
                                                />
                                            )
                                        }
                                        onClick={handleResetIdentity}
                                        disabled={isResetting}
                                        className="flex-1 bg-red-950/10 hover:bg-red-950/20 dark:bg-red-900/10 dark:hover:bg-red-900/20 text-red-950 dark:text-red-900"
                                    >
                                        {isResetting ? "清除中..." : "确认清除"}
                                    </Button>
                                    <Button
                                        variant="outline"
                                        onClick={() =>
                                            setShowResetConfirm(false)
                                        }
                                        className="flex-1"
                                    >
                                        取消
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
