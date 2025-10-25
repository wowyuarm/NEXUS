/**
 * IdentityPanel Component - Command Panel Design Standard v1.0
 *
 * Design Principles (applicable to all command panels: /identity, /config, /prompt):
 * 
 * 1. **Layout Standard**
 *    - Fixed height: 360px (unified for all modes)
 *    - Consistent padding: px-7 py-4
 *    - Section spacing: space-y-3 (compact layout)
 *    - Help button inline with first label for space efficiency
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
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/features/chat/store/chatStore";
import { useUIStore } from "@/stores/uiStore";
import { IdentityService } from "@/services/identity/identity";
import { websocketManager } from "@/services/websocket/manager";
import { v4 as uuidv4 } from "uuid";
import { FRAMER } from "@/lib/motion";
import type { Message } from "@/features/chat/types";
import { VisitorMain, ImportMode as ImportView, MemberMain, ExportMode as ExportView, ResetMode as ResetView, HelpMode } from "./IdentityPanelViews";

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
            setTimeout(() => closeModal(), 800);
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
            }, 800);
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

    // =========================================================================
    // Presentational Views (extracted)
    // =========================================================================

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
                        <div className={cn(
                            "flex-1 overflow-y-auto",
                            // Mobile: px-4 py-3 (reduced inner padding)
                            "px-4 py-3",
                            // Desktop: restore px-7 py-4
                            "md:px-7 md:py-4"
                        )}>
                            {visitorMode ? (
                                mode === "main" ? (
                                    <VisitorMain
                                        actionState={actionState}
                                        onCreateIdentity={handleCreateIdentity}
                                        onGoToImport={() => setMode("import")}
                                        onHelp={() => setMode("help")}
                                    />
                                ) : mode === "import" ? (
                                    <ImportView
                                        mnemonicInput={mnemonicInput}
                                        setMnemonicInput={setMnemonicInput}
                                        actionState={actionState}
                                        onImport={handleImportIdentity}
                                        onBack={navigateBack}
                                    />
                                ) : mode === "help" ? (
                                    <HelpMode onBack={navigateBack} />
                                ) : null
                            ) : (
                                mode === "main" ? (
                                    <MemberMain
                                        publicKey={publicKey}
                                        onBackup={() => { setMode("export"); setTimeout(() => handleExportMnemonic(), 0); }}
                                        onSwitch={() => setMode("import")}
                                        onHelp={() => setMode("help")}
                                        onGoToReset={() => setMode("reset")}
                                    />
                                ) : mode === "import" ? (
                                    <ImportView
                                        mnemonicInput={mnemonicInput}
                                        setMnemonicInput={setMnemonicInput}
                                        actionState={actionState}
                                        onImport={handleImportIdentity}
                                        onBack={navigateBack}
                                    />
                                ) : mode === "export" ? (
                                    <ExportView
                                        exportedMnemonic={exportedMnemonic}
                                        showMnemonic={showMnemonic}
                                        setShowMnemonic={setShowMnemonic}
                                        isCopied={isCopied}
                                        onCopy={handleCopyMnemonic}
                                        onBack={navigateBack}
                                    />
                                ) : mode === "reset" ? (
                                    <ResetView
                                        actionState={actionState}
                                        onReset={handleResetIdentity}
                                        onBack={navigateBack}
                                    />
                                ) : mode === "help" ? (
                                    <HelpMode onBack={navigateBack} />
                                ) : null
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
