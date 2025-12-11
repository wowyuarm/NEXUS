// Presentational subviews extracted from IdentityPanel.
// Pure UI only: no business logic, no store access. Keep grayscale-only styling and mobile-first responsiveness.
// Pass all actions via props. Safe to reuse across command panels.
import React from "react";
import { motion } from "framer-motion";
import { Button, Textarea } from "@/components/ui";
import { FRAMER } from "@/lib/motion";
import { HelpCircle, ArrowLeft, UserPlus, Upload, Download, Eye, EyeOff, Loader2, Check, Copy, Trash2 } from "lucide-react";

export type ActionState = "idle" | "loading" | "success" | "error";
export const VisitorMain: React.FC<{
  actionState: ActionState;
  onCreateIdentity: () => void | Promise<void>;
  onGoToImport: () => void;
  onHelp: () => void;
}> = ({ actionState, onCreateIdentity, onGoToImport, onHelp }) => (
  <div className="space-y-3">
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          访客模式
        </label>
        <button
          onClick={onHelp}
          className="text-muted-foreground hover:text-foreground transition-colors duration-150"
          aria-label="身份系统说明"
        >
          <HelpCircle size={16} />
        </button>
      </div>
      <div className="px-4 py-2.5 bg-muted/20 rounded-xl border border-border/30">
        <p className="text-sm text-muted-foreground leading-relaxed text-center">
          您当前为<span className="font-medium text-foreground">访客身份</span>，
          无法使用全部服务。创建或导入身份后，您将获得完整的服务能力。
        </p>
      </div>
    </div>

    <div className="space-y-2.5 pt-0.5">
      <Button
        variant="primary"
        icon={actionState === "loading" ? (
          <Loader2 size={18} className="animate-spin" />
        ) : (
          <UserPlus size={18} />
        )}
        onClick={onCreateIdentity}
        disabled={actionState === "loading"}
        fullWidth
      >
        {actionState === "loading" ? "创建中..." : "创建新身份"}
      </Button>

      <Button
        variant="outline"
        icon={<Upload size={18} />}
        onClick={onGoToImport}
        fullWidth
      >
        导入已有身份
      </Button>
    </div>
  </div>
);

// Import Mode View
export const ImportMode: React.FC<{
  mnemonicInput: string;
  setMnemonicInput: (v: string) => void;
  actionState: ActionState;
  onImport: () => void | Promise<void>;
  onBack: () => void;
}> = ({ mnemonicInput, setMnemonicInput, actionState, onImport, onBack }) => (
  <div className="space-y-4">
    <div className="flex items-center justify-between">
      <button
        onClick={onBack}
        className="text-muted-foreground hover:text-foreground transition-colors duration-150"
        aria-label="返回"
      >
        <ArrowLeft size={18} />
      </button>
      <h3 className="text-base font-medium text-foreground">导入身份</h3>
      <div className="w-[18px]" />
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
        onClick={onImport}
        disabled={actionState === "loading" || !mnemonicInput.trim()}
        fullWidth
      >
        {actionState === "loading" ? "导入中..." : "确认导入"}
      </Button>
    </div>
  </div>
);

export const MemberMain: React.FC<{
  publicKey: string;
  onBackup: () => void;
  onSwitch: () => void;
  onHelp: () => void;
  onGoToReset: () => void;
}> = ({ publicKey, onBackup, onSwitch, onHelp, onGoToReset }) => (
  <div className="space-y-3">
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
          存在地址
        </label>
        <button
          onClick={onHelp}
          className="text-muted-foreground hover:text-foreground transition-colors duration-150"
          aria-label="身份系统说明"
        >
          <HelpCircle size={16} />
        </button>
      </div>
      <div className="px-4 py-2 bg-muted/10 rounded-lg border border-border/20">
        <code className="text-sm text-foreground/90 font-mono block text-center break-all leading-relaxed">
          {publicKey || "加载中..."}
        </code>
      </div>
    </div>

    <div className="flex gap-2.5">
      <Button
        variant="outline"
        icon={<Download size={18} />}
        onClick={onBackup}
        className="flex-1"
      >
        备份身份
      </Button>

      <Button
        variant="outline"
        icon={<Upload size={18} />}
        onClick={onSwitch}
        className="flex-1"
      >
        切换身份
      </Button>
    </div>

    <div className="pt-4 mt-4 border-t border-border/30">
      <Button
        variant="ghost"
        icon={<Trash2 size={16} />}
        onClick={onGoToReset}
        fullWidth
        className="text-muted-foreground/60 hover:text-foreground/80"
      >
        清除当前身份
      </Button>
    </div>
  </div>
);

export const ExportMode: React.FC<{
  exportedMnemonic: string | null;
  showMnemonic: boolean;
  setShowMnemonic: (v: boolean) => void;
  isCopied: boolean;
  onCopy: () => void | Promise<void>;
  onBack: () => void;
}> = ({ exportedMnemonic, showMnemonic, setShowMnemonic, isCopied, onCopy, onBack }) => (
  <div className="space-y-4">
    <div className="flex items-center justify-between">
      <button
        onClick={onBack}
        className="text-muted-foreground hover:text-foreground transition-colors duration-150"
        aria-label="返回"
      >
        <ArrowLeft size={18} />
      </button>
      <h3 className="text-base font-medium text-foreground">助记词</h3>
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
          onClick={onCopy}
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

export const ResetMode: React.FC<{
  actionState: ActionState;
  onReset: () => void | Promise<void>;
  onBack: () => void;
}> = ({ actionState, onReset, onBack }) => (
  <div className="space-y-4">
    <div className="flex items-center justify-between">
      <button
        onClick={onBack}
        className="text-muted-foreground hover:text-foreground transition-colors duration-150"
        aria-label="返回"
      >
        <ArrowLeft size={18} />
      </button>
      <h3 className="text-base font-medium text-foreground">重置确认</h3>
      <div className="w-[18px]" />
    </div>

    <div className="space-y-4">
      <div className="space-y-3">
        <div className="px-4 py-3 bg-foreground/[0.02] rounded-lg border border-border/40">
          <p className="text-sm text-foreground/70 leading-relaxed text-center">
            此操作将删除本地存储的密钥。如果您没有备份助记词，将
            <span className="font-semibold text-foreground">永久丢失</span>
            此身份。
          </p>
        </div>

        <div className="px-4 py-2.5 bg-muted/20 rounded-lg border border-border/30">
          <p className="text-xs text-muted-foreground leading-relaxed text-center">
            此操作不可逆。请确保您已备份助记词。
          </p>
        </div>
      </div>

      <div className="flex gap-2.5">
        <Button
          variant="outline"
          onClick={onBack}
          className="flex-1"
        >
          取消
        </Button>
        <Button
          variant="outline"
          icon={actionState === "loading" && (
            <Loader2 size={18} className="animate-spin" />
          )}
          onClick={onReset}
          disabled={actionState === "loading"}
          className="flex-1 border-foreground/20 hover:bg-foreground/[0.03] hover:border-foreground/30"
        >
          {actionState === "loading" ? "清除中..." : "确认清除"}
        </Button>
      </div>
    </div>
  </div>
);

export const HelpMode: React.FC<{ onBack: () => void }> = ({ onBack }) => (
  <div className="space-y-4">
    <div className="flex items-center justify-between">
      <button
        onClick={onBack}
        className="text-muted-foreground hover:text-foreground transition-colors duration-150"
        aria-label="返回"
      >
        <ArrowLeft size={18} />
      </button>
      <h3 className="text-base font-medium text-foreground">关于身份系统</h3>
      <div className="w-[18px]" />
    </div>

    <div className="space-y-5">
      <div className="space-y-2">
        <h4 className="text-sm font-bold text-foreground uppercase tracking-wide">
          不同于传统账号
        </h4>
        <p className="text-sm text-muted-foreground leading-relaxed">
          NEXUS 使用<span className="font-medium text-foreground">加密身份</span>，
          无需注册、无密码。私钥仅存本地，服务器只验证签名。
        </p>
      </div>

      <div className="space-y-2">
        <h4 className="text-sm font-bold text-foreground uppercase tracking-wide">
          公钥 & 私钥
        </h4>
        <p className="text-sm text-muted-foreground leading-relaxed">
          <span className="font-medium text-foreground">公钥</span>是您的身份地址，服务器存储用于验证。
          <span className="font-medium text-foreground">私钥</span>仅存本地浏览器，绝不上传。
        </p>
      </div>

      <div className="space-y-2">
        <h4 className="text-sm font-bold text-foreground uppercase tracking-wide">
          助记词
        </h4>
        <p className="text-sm text-muted-foreground leading-relaxed">
          12或24个单词组成的<span className="font-medium text-foreground">恢复短语</span>。
          丢失助记词 = 永久失去身份。请务必备份并妥善保管。
        </p>
      </div>

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
