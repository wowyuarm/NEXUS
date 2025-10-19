/**
 * IdentityPanel Component - Command Panel Design Standard v1.0
 *
 * Design Principles (applicable to all command panels: /identity, /config, /prompt):
 * 
 * 1. **Layout Standard**
 *    - Fixed height: 360px (unified for all modes)
 *    - Consistent padding: px-7 py-4
 *    - Section spacing: space-y-3.5
 *    - Centered titles for better visual hierarchy
 *
 * 2. **State Machine**
 *    - Clear mode separation: main | import | export | reset | help
 *    - Single actionState: idle | loading | success | error
 *    - Smooth transitions with FRAMER.reveal (350ms)
 *
 * 3. **Visual Hierarchy**
 *    - Title: text-sm font-medium, centered
 *    - Body: text-sm, comfortable line-height
 *    - Labels: text-xs uppercase tracking-wide
 *
 * 4. **Navigation**
 *    - Back button: Icon-only (ArrowLeft), top-left
 *    - Help button: Icon-only (HelpCircle), top-right
 *    - Minimal text, maximum clarity
 *
 * 5. **Grayscale Moderation**
 *    - No color emphasis (no red warnings)
 *    - Use opacity, weight, and spacing for hierarchy
 *    - Danger actions: subtle opacity reduction
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
    ArrowLeft,
    HelpCircle,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button, Textarea } from "@/components/ui";
import { useChatStore } from "@/features/chat/store/chatStore";
import { useUIStore } from "@/stores/uiStore";
import { IdentityService } from "@/services/identity/identity";
import { websocketManager } from "@/services/websocket/manager";
import { v4 as uuidv4 } from "uuid";
import { FRAMER } from "@/lib/motion";
import type { Message } from "@/features/chat/types";

// ============================================================================
// State Machine: One Mode at a Time
// ============================================================================

type PanelMode =
    | "main" // 主界面
    | "import" // 导入身份
    | "export" // 导出助记词
    | "reset" // 重置确认
    | "help"; // 帮助说明

type ActionState = "idle" | "loading" | "success" | "error";

export const IdentityPanel: React.FC = () => {
    const visitorMode = useChatStore((state) => state.visitorMode);
    const closeModal = useUIStore((state) => state.closeModal);

    // ============================================================================
    // Core State
    // ============================================================================
    
    const [publicKey, setPublicKey] = useState<string>("");
    const [mode, setMode] = useState<PanelMode>("main");
    const [actionState, setActionState] = useState<ActionState>("idle");
    
    // Form data
    const [mnemonicInput, setMnemonicInput] = useState<string>("");
    const [exportedMnemonic, setExportedMnemonic] = useState<string | null>(null);
    const [showMnemonic, setShowMnemonic] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [isCopied, setIsCopied] = useState<boolean>(false);

    // ============================================================================
    // Lifecycle
    // ============================================================================

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

    // Auto-clear errors after 3 seconds
    useEffect(() => {
        if (errorMessage) {
            const timer = setTimeout(() => setErrorMessage(""), 3000);
            return () => clearTimeout(timer);
        }
    }, [errorMessage]);

    // ============================================================================
    // Actions
    // ============================================================================

    const handleCreateIdentity = async () => {
        setActionState("loading");

        try {
            if (visitorMode && IdentityService.hasIdentity()) {
                IdentityService.clearIdentity();
            }

            await IdentityService.getIdentity();
            
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

            const auth = await IdentityService.signCommand("/identity");
            websocketManager.sendCommand("/identity", auth);

            await websocketManager.reconnect();
            
            setActionState("success");
            setTimeout(() => closeModal(), 1000);
        } catch (error) {
            console.error("Failed to create identity:", error);
            setErrorMessage("创建失败，请重试");
            setActionState("error");
        }
    };

    const handleImportIdentity = async () => {
        if (!mnemonicInput.trim()) {
            setErrorMessage("请输入助记词");
            return;
        }

        setActionState("loading");

        try {
            const newPublicKey = await IdentityService.importFromMnemonic(mnemonicInput);
            await websocketManager.reconnect(newPublicKey);

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

            setActionState("success");
            setTimeout(() => {
                closeModal();
                setMnemonicInput("");
                setMode("main");
            }, 1000);
        } catch (error) {
            console.error("Failed to import identity:", error);
            setErrorMessage(error instanceof Error ? error.message : "导入失败");
            setActionState("error");
        }
    };

    const handleExportMnemonic = () => {
        setActionState("loading");

        try {
            const mnemonic = IdentityService.exportMnemonic();
            setExportedMnemonic(mnemonic);
            setShowMnemonic(true);
            setIsCopied(false); // 重置复制状态
            setActionState("success");
        } catch (error) {
            console.error("Failed to export mnemonic:", error);
            setErrorMessage(error instanceof Error ? error.message : "导出失败");
            setActionState("error");
            setMode("main");
        }
    };

    const handleCopyMnemonic = useCallback(async () => {
        if (!exportedMnemonic) return;

        try {
            await navigator.clipboard.writeText(exportedMnemonic);
            setIsCopied(true);
            setTimeout(() => setIsCopied(false), 2000);
        } catch (error) {
            console.error("Failed to copy mnemonic:", error);
            setErrorMessage("复制失败");
        }
    }, [exportedMnemonic]);

    const handleResetIdentity = async () => {
        // 二次确认
        const confirmed = window.confirm(
            "⚠️ 最后确认\n\n" +
            "此操作将永久删除本地密钥。\n" +
            "如果您没有备份助记词，将无法恢复此身份。\n\n" +
            "确定要继续吗？"
        );

        if (!confirmed) {
            return;
        }

        setActionState("loading");

        try {
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

            const auth = await IdentityService.signCommand("/identity/delete");
            websocketManager.sendCommand("/identity/delete", auth);

            await new Promise((resolve) => setTimeout(resolve, 300));

            IdentityService.clearIdentity();
            closeModal();
            websocketManager.disconnect();

            setTimeout(() => {
                window.location.reload();
            }, 500);
        } catch (error) {
            console.error("Failed to reset identity:", error);
            setErrorMessage("重置失败");
            setActionState("error");
        }
    };

    // ============================================================================
    // Navigation Helpers
    // ============================================================================

    const navigateBack = () => {
        setMode("main");
        setActionState("idle");
        setMnemonicInput("");
        setExportedMnemonic(null);
        setShowMnemonic(false);
        setErrorMessage("");
        setIsCopied(false);
    };

    // ============================================================================
    // Render Functions
    // ============================================================================

    const renderVisitorMain = () => (
        <div className="space-y-3.5">
            {/* Help Button - Top Right */}
            <div className="flex justify-end -mb-0.5">
                <button
                    onClick={() => setMode("help")}
                    className="text-muted-foreground hover:text-foreground transition-colors duration-150"
                    aria-label="身份系统说明"
                >
                    <HelpCircle size={18} />
                </button>
            </div>

            {/* Guidance */}
            <div className="px-4 py-2.5 bg-muted/20 rounded-xl border border-border/30">
                <p className="text-sm text-muted-foreground leading-relaxed text-center">
                    您当前为<span className="font-medium text-foreground">访客身份</span>，
                    无法使用全部服务。创建或导入身份后，您将获得完整的服务能力。
                </p>
            </div>

            {/* Actions */}
            <div className="space-y-2.5 pt-0.5">
                <Button
                    variant="primary"
                    icon={actionState === "loading" ? (
                        <Loader2 size={18} className="animate-spin" />
                    ) : (
                        <UserPlus size={18} />
                    )}
                    onClick={handleCreateIdentity}
                    disabled={actionState === "loading"}
                    fullWidth
                >
                    {actionState === "loading" ? "创建中..." : "创建新身份"}
                </Button>

                <Button
                    variant="outline"
                    icon={<Upload size={18} />}
                    onClick={() => setMode("import")}
                    fullWidth
                >
                    导入已有身份
                </Button>
            </div>
        </div>
    );

    const renderImportMode = () => (
        <div className="space-y-4">
            {/* Navigation */}
            <div className="flex items-center justify-between">
                <button
                    onClick={navigateBack}
                    className="text-muted-foreground hover:text-foreground transition-colors duration-150"
                    aria-label="返回"
                >
                    <ArrowLeft size={18} />
                </button>
                <h3 className="text-sm font-medium text-foreground">导入身份</h3>
                <div className="w-[18px]" /> {/* Spacer for centering */}
            </div>

            <div className="space-y-4">
                <Textarea
                    value={mnemonicInput}
                    onChange={(e) => setMnemonicInput(e.target.value)}
                    placeholder="请输入助记词（12或24个单词，空格分隔）"
                    minRows={4}
                    className="text-sm font-mono"
                    autoFocus
                />

                <Button
                    variant="primary"
                    icon={actionState === "loading" && (
                        <Loader2 size={18} className="animate-spin" />
                    )}
                    onClick={handleImportIdentity}
                    disabled={actionState === "loading" || !mnemonicInput.trim()}
                    fullWidth
                >
                    {actionState === "loading" ? "导入中..." : "确认导入"}
                </Button>
            </div>
        </div>
    );

    const renderMemberMain = () => (
        <div className="space-y-3.5">
            {/* Help Button - Top Right */}
            <div className="flex justify-end -mb-0.5">
                <button
                    onClick={() => setMode("help")}
                    className="text-muted-foreground hover:text-foreground transition-colors duration-150"
                    aria-label="身份系统说明"
                >
                    <HelpCircle size={18} />
                </button>
            </div>

            {/* Public Key Display */}
            <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide text-center block">
                    存在地址
                </label>
                <div className="px-4 py-2.5 bg-muted/10 rounded-lg border border-border/20">
                    <code className="text-xs text-foreground/90 font-mono block text-center break-all leading-relaxed">
                        {publicKey || "加载中..."}
                    </code>
                </div>
            </div>

            {/* Primary Actions */}
            <div className="flex gap-2.5">
                <Button
                    variant="outline"
                    icon={<Download size={18} />}
                    onClick={() => {
                        setMode("export");
                        handleExportMnemonic();
                    }}
                    className="flex-1"
                >
                    备份身份
                </Button>

                <Button
                    variant="outline"
                    icon={<Upload size={18} />}
                    onClick={() => setMode("import")}
                    className="flex-1"
                >
                    切换身份
                </Button>
            </div>

            {/* Danger Zone - Subtle, no red */}
            <div className="pt-4 mt-4 border-t border-border/30">
                <Button
                    variant="ghost"
                    icon={<Trash2 size={16} />}
                    onClick={() => setMode("reset")}
                    fullWidth
                    className="text-muted-foreground/60 hover:text-foreground/80"
                >
                    清除当前身份
                </Button>
            </div>
        </div>
    );

    const renderExportMode = () => (
        <div className="space-y-4">
            {/* Navigation */}
            <div className="flex items-center justify-between">
                <button
                    onClick={navigateBack}
                    className="text-muted-foreground hover:text-foreground transition-colors duration-150"
                    aria-label="返回"
                >
                    <ArrowLeft size={18} />
                </button>
                <h3 className="text-sm font-medium text-foreground">助记词</h3>
                <Button
                    variant="ghost"
                    size="sm"
                    icon={showMnemonic ? <EyeOff size={16} /> : <Eye size={16} />}
                    iconOnly
                    onClick={() => setShowMnemonic(!showMnemonic)}
                    aria-label={showMnemonic ? "隐藏助记词" : "显示助记词"}
                />
            </div>

            {showMnemonic && exportedMnemonic && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={FRAMER.reveal}
                    className="space-y-4"
                >
                    <div className="px-4 py-3.5 bg-background/60 rounded-lg border border-border/30">
                        <p className="text-sm text-foreground/90 font-mono break-all leading-relaxed text-center">
                            {exportedMnemonic}
                        </p>
                    </div>

                    <Button
                        variant="primary"
                        icon={isCopied ? (
                            <Check size={18} />
                        ) : (
                            <Copy size={18} />
                        )}
                        onClick={handleCopyMnemonic}
                        disabled={isCopied}
                        fullWidth
                    >
                        {isCopied ? "已复制" : "复制"}
                    </Button>

                    <p className="text-xs text-muted-foreground/80 leading-relaxed text-center">
                        请妥善保管助记词，切勿泄露。助记词是恢复身份的唯一凭证。
                    </p>
                </motion.div>
            )}
        </div>
    );

    const renderResetMode = () => (
        <div className="space-y-4">
            {/* Navigation */}
            <div className="flex items-center justify-between">
                <button
                    onClick={navigateBack}
                    className="text-muted-foreground hover:text-foreground transition-colors duration-150"
                    aria-label="返回"
                >
                    <ArrowLeft size={18} />
                </button>
                <h3 className="text-sm font-medium text-foreground">清除当前身份</h3>
                <div className="w-[18px]" /> {/* Spacer for centering */}
            </div>

            <div className="space-y-4">
                {/* Warning - Grayscale only, use opacity and background */}
                <div className="px-4 py-3 bg-foreground/[0.02] rounded-lg border border-border/40">
                    <p className="text-sm text-foreground/70 leading-relaxed text-center">
                        此操作将删除本地存储的密钥。如果您没有备份助记词，将
                        <span className="font-semibold text-foreground">永久丢失</span>
                        此身份。
                    </p>
                </div>

                <Button
                    variant="outline"
                    icon={actionState === "loading" && (
                        <Loader2 size={18} className="animate-spin" />
                    )}
                    onClick={handleResetIdentity}
                    disabled={actionState === "loading"}
                    fullWidth
                    className="border-foreground/20 hover:bg-foreground/[0.03] hover:border-foreground/30"
                >
                    {actionState === "loading" ? "清除中..." : "确认清除"}
                </Button>
            </div>
        </div>
    );

    const renderHelpMode = () => (
        <div className="space-y-4">
            {/* Navigation */}
            <div className="flex items-center justify-between">
                <button
                    onClick={navigateBack}
                    className="text-muted-foreground hover:text-foreground transition-colors duration-150"
                    aria-label="返回"
                >
                    <ArrowLeft size={18} />
                </button>
                <h3 className="text-sm font-medium text-foreground">关于身份系统</h3>
                <div className="w-[18px]" /> {/* Spacer for centering */}
            </div>

            <div className="space-y-5">
                {/* 核心概念 */}
                <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-foreground uppercase tracking-wide">
                        不同于传统账号
                    </h4>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                        NEXUS 使用<span className="font-medium text-foreground">加密身份</span>，
                        无需注册、无密码。私钥仅存本地，服务器只验证签名。
                    </p>
                </div>

                {/* 公钥与私钥 */}
                <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-foreground uppercase tracking-wide">
                        公钥 & 私钥
                    </h4>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                        <span className="font-medium text-foreground">公钥</span>是您的身份地址，服务器存储用于验证。
                        <span className="font-medium text-foreground">私钥</span>仅存本地浏览器，绝不上传。
                    </p>
                </div>

                {/* 助记词 */}
                <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-foreground uppercase tracking-wide">
                        助记词
                    </h4>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                        12或24个单词组成的<span className="font-medium text-foreground">恢复短语</span>。
                        丢失助记词 = 永久失去身份。请务必备份并妥善保管。
                    </p>
                </div>

                {/* 优势 */}
                <div className="px-4 py-3 bg-muted/20 rounded-lg border border-border/30">
                    <p className="text-xs text-muted-foreground leading-relaxed">
                        ✓ 无需注册，即刻创建<br/>
                        ✓ 私钥本地，服务器不存<br/>
                        ✓ 跨设备导入，随时切换<br/>
                        ✓ 加密签名，安全验证
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
                        key={visitorMode ? `visitor-${mode}` : `member-${mode}`}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={FRAMER.reveal}
                        className="absolute inset-0 flex flex-col"
                    >
                        <div className="flex-1 overflow-y-auto px-7 py-4">
                            {visitorMode ? (
                                mode === "main" ? renderVisitorMain() :
                                mode === "import" ? renderImportMode() :
                                mode === "help" ? renderHelpMode() : null
                            ) : (
                                mode === "main" ? renderMemberMain() :
                                mode === "import" ? renderImportMode() :
                                mode === "export" ? renderExportMode() :
                                mode === "reset" ? renderResetMode() :
                                mode === "help" ? renderHelpMode() : null
                            )}
                        </div>

                        {/* Error Toast - Floating at bottom */}
                        <AnimatePresence>
                            {errorMessage && (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: 10 }}
                                    transition={FRAMER.transition}
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

