我们已经完成了指令系统的后端架构和前端逻辑分发。
    *   **本任务目标:** 构建一个通用的、可复用的、符合YX Nexus设计哲学的**模态交互系统**。这个系统将作为未来所有控制面板（`/identity`, `/config`, `/prompt`等）的统一载体。
    *   **核心产出:** 一个新的全局UI状态管理器 (`uiStore`)，以及两个核心的通用UI组件 (`<Modal />`, `<Panel />`)。

---

#### **第一部分：设计哲学与预期效果 (The "Why" & The "What")**

在开始实施之前，你必须首先理解并内化这套系统的设计哲学。我们的目标不是构建一个普通的“弹窗”，而是创造一种**“专注的静默 (Focused Silence)”**。

**1. 核心原则:**
*   **从对话到维护的优雅过渡:** Modal的出现，代表着用户从与AI的“对话 (Dialogue)”模式，切换到了对系统的“维护 (Maintenance)”模式。这个切换过程必须是无缝、平滑、且符合物理直觉的，不能有任何生硬的中断感。
*   **空间即专注:** Modal通过占据视觉中心并模糊背景，为用户创造了一个临时的、不受干扰的“禅定空间”。在这个空间里，用户可以专注于完成一项重要的、非对话性的任务。
*   **结构的一致性:** 所有的控制面板都必须共享一个统一的视觉和结构语言（由`<Panel />`组件提供）。这种一致性降低了用户的认知负荷，并强化了系统的整体感和品牌识别度。

**2. 预期的视觉与交互效果 (The Desired Experience):**
*   **触发:** 当一个需要GUI的指令被执行时。
*   **动画:**
    1.  一个覆盖全屏的、半透明的**背景层**（Backdrop）以`150ms`的速度平滑淡入。这个背景层必须应用我们的“液态玻璃”效果（`backdrop-blur-xl`）。
    2.  几乎同时，**内容面板** (`<Panel />`) 从屏幕中央，以一个带有轻微物理回弹效果的“缩放+淡入”动画出现（`scale`从0.95到1，`opacity`从0到1），时长约`200ms`。
*   **交互:**
    *   用户可以点击半透明的背景层，或者按`ESC`键，来关闭Modal。关闭动画与打开动画应是镜像的。
    *   Modal内部的内容（由`<Panel />`承载）将是交互的核心。
*   **材质与风格:** `<Panel />`组件的材质必须严格遵循我们已有的`CodeBlock`或`ChatInput`的风格：`bg-card/75`，`border`，以及`shadow-lg`，以确保视觉语言的绝对统一。

---

#### **第二部分：架构设计与实施路径 (The "How")**

**Phase 1: 建立全局UI状态中枢 (TDD-First)**

1.  **TDD - 编写失败的测试:**
    *   **路径:** `aura/src/stores/__tests__/uiStore.test.ts` (新建文件和目录)。
    *   **行动:** 编写测试用例，验证`openModal`和`closeModal` actions能正确地改变`activeModal`状态。
2.  **实施 - 创建`uiStore.ts`:**
    *   **路径:** `aura/src/stores/uiStore.ts` (新建文件和目录)。
    *   **行动:** 实现我们在之前讨论中已确定的`uiStore`结构，包含`activeModal: ModalType`状态和`openModal`, `closeModal` actions。

**Phase 2: 搭建通用模态组件骨架 (Component-Driven)**

1.  **创建`<Modal />`组件 (通用模态容器):**
    *   **路径:** `aura/src/components/common/Modal.tsx`。
    *   **Props:** `isOpen: boolean`, `onClose: () => void`, `children: React.ReactNode`。
    *   **实现:**
        *   使用`framer-motion`和`AnimatePresence`来实现我们预期的入场和退场动画。
        *   实现背景覆盖层及其点击关闭逻辑。
        *   实现`ESC`键关闭的`useEffect` Hook。
        *   **注意:** 这个组件**只负责“模态”行为**，完全不关心其`children`的内容和样式。
2.  **创建`<Panel />`组件 (通用面板骨架):**
    *   **路径:** `aura/src/components/common/Panel.tsx`。
    *   **Props:** `title: string`, `children: React.ReactNode`, `footer?: React.ReactNode`。
    *   **实现:**
        *   构建一个包含`header`, `main` (content), 和可选`footer`的flexbox布局。
        *   `<header>`中包含`title`和一个关闭按钮（该按钮调用从`<Modal />`传递下来的`onClose`）。
        *   应用所有必需的Tailwind CSS类，以实现“液态玻璃”材质和统一的视觉风格。

**Phase 3: 集成与编排 (Integration & Orchestration)**

1.  **改造`commandExecutor.ts`:**
    *   **路径:** `aura/src/features/command/commandExecutor.ts`。
    *   **行动:** 修改`executeCommand`函数。当它识别到一个需要GUI的指令时（例如，我们可以暂时硬编码`if (command.name === '/identity')`），它**不再**创建`pending`消息，而是**调用`useUIStore.getState().openModal('identity')`**。
2.  **改造`App.tsx`:**
    *   **路径:** `aura/src/app/App.tsx`。
    *   **行动:**
        *   从`uiStore`中`use`出`activeModal`和`closeModal`状态和方法。
        *   在`return`语句的顶层，实现我们之前讨论的Modal渲染逻辑：
            ```tsx
            <Modal isOpen={activeModal === 'identity'} onClose={closeModal}>
              <Panel title="Identity Management">
                {/* 这是一个临时的占位符内容 */}
                <div>Identity Panel Content Goes Here...</div>
              </Panel>
            </Modal>
            ```
        *   **注意:** 在`Panel`的`children`中，我们暂时只放置一个简单的占位符。具体的面板内容（如`IdentityPanel.tsx`）将在下一个任务中实现。

#### **验收标准**

1.  有对应的、通过的测试文件（`uiStore.test.ts`）。
2.  代码库中必须存在`uiStore.ts`, `Modal.tsx`, `Panel.tsx`三个核心文件，且其实现符合上述规范。
3.  在完成任务后，**端到端行为**必须是：
    *   在AURA中输入`/`，打开`CommandPalette`。
    *   选择`/identity`并回车。
    *   一个带有背景模糊的、内容为“Identity Panel Content Goes Here...”的模态面板，必须以平滑的动画效果从屏幕中央出现。
    *   点击面板外的背景或按`ESC`键，该面板必须以平滑的动画效果消失。
    *   聊天流中**不应**出现任何与`/identity`指令相关的`SYSTEM`消息。
    你可能需要修改identity.py的逻辑，其具体实现我们将在下一个任务中执行，现在显示奠基与准备

    最重要的是你需要内化我们预期的效果与未来实现，做出相关开发与修改。还有，必须详细了解前端实现以对齐设计原则与哲学
---

---
---

    *   `MODAL-SYSTEM-FOUNDATION-1.0`已完成，我们拥有了通用的`<Modal>`和`<Panel>`组件，以及`uiStore`。
    *   后端`DATA-SOVEREIGNTY-1.0`已完成，具备了身份的创建、验证和数据隔离能力。
    *   **本任务目标:** 构建一个功能完备、交互优雅的`IdentityPanel.tsx`，并将其与后端的身份服务深度集成，最终实现用户对“知觉密钥”的完全掌控（创建、备份、恢复）。

---

#### **第一部分：设计哲学与预期效果 (The "Why" & The "What")**

**1. 核心原则:**
*   **主权可视化:** 这个面板是用户“数字主权”的唯一具象化体现。它的设计必须传达出**安全、可靠、尽在掌控**的感觉。
*   **状态驱动:** 面板的形态和功能，必须严格地由用户当前的身份状态（访客 vs. 成员）驱动，为不同状态的用户提供最符合其当前需求的引导和工具。
*   **静默反馈:** 对身份的操作是系统级的“维护”行为，其反馈应在面板内部完成（例如图标、状态文本），**不应**在主聊天流中产生任何新的`SYSTEM`消息，以保持对话的纯粹性。

**2. 预期的视觉与交互效果:**
*   **触发:** 用户执行`/identity`指令，`<Modal>`以我们已定义的动画打开，其中包裹着`<IdentityPanel />`。
*   **面板布局:** 采用简洁、大间距的垂直布局，营造出从容、重要的氛围。所有按钮都应是清晰、有引导性的。
*   **“访客”视图:**
    *   **标题:** `Anchor Your Identity`
    *   **内容:**
        *   一段简短的说明文字，解释创建或恢复身份的重要性。
        *   一个主操作按钮：“**Create New Identity**”。
        *   一个次要操作链接或按钮：“**Restore Existing Identity**”。
*   **“成员”视图:**
    *   **标题:** `Identity Management`
    *   **内容:**
        *   一个标题为`Your Being Address`的区域，清晰地显示用户截断后的公钥（例如`0x1234...abcd`），并提供一个“复制”按钮。
        *   一个标题为`Backup (Export)`的区域，包含“**Show Mnemonic Phrase**”按钮。
        *   一个标题为`Switch (Import)`的区域，包含“**Import from Mnemonic**”按钮。
*   **反馈机制:**
    *   所有操作（创建、恢复）在点击后，按钮应显示加载状态。
    *   操作成功后，按钮旁边出现一个绿色的“√”图标，并可能有简短的成功文本提示（如“Identity Created!”），持续2秒。
    *   **关键:** 身份创建或恢复成功后，**必须**自动触发一次**WebSocket重连**或**页面刷新**，以确保整个应用的状态（特别是`visitorMode`）被正确更新。

---

#### **第二部分：架构与实施路径 (The "How")**

**Phase 1: 专用指令的后端定义 (Backend Command Scaffolding)**

**目标:** 创建专用于面板内部操作的、需要签名的后端指令。

1.  **`nexus/commands/definition/identity_create.py` (新增):**
    *   **`COMMAND_DEFINITION`:** `name: 'identity-create'`, `handler: 'websocket'`, `requiresSignature: True`。**不包含`requiresGUI`**，这是一个纯逻辑指令。
    *   **`execute`函数:** 调用`IdentityService.get_or_create_identity`，并返回成功或失败的结果。
2.  **`nexus/commands/definition/identity.py` (修改):**
    *   它的`COMMAND_DEFINITION`保持`requiresGUI: True`不变。
    *   它的`execute`函数可以被清空或保留为Fallback，因为它的主要职责已由前端`commandExecutor`转移为“打开Modal”。

**Phase 2: 前端面板的构建与逻辑实现 (Frontend Panel Construction)**

1.  **TDD - 编写组件测试:**
    *   **路径:** `aura/src/features/command/components/__tests__/IdentityPanel.test.tsx` (新建)。
    *   **行动:** 编写测试用例，模拟不同的`visitorMode`状态，断言面板渲染出正确的视图（访客 vs. 成员）。模拟按钮点击，断言`commandExecutor`被以正确的参数调用。
2.  **创建`IdentityPanel.tsx`组件:**
    *   **路径:** `aura/src/features/command/components/IdentityPanel.tsx`。
    *   **状态感知:** 组件需要从`chatStore`中`use`出`visitorMode`状态，以决定渲染哪个视图。
    *   **“创建”逻辑:**
        *   “Create New Identity”按钮的`onClick`处理器，应调用`commandExecutor.executeCommand`并传入一个代表`/identity-create`的`Command`对象。
    *   **“导出”逻辑:**
        *   “Show Mnemonic Phrase”按钮的`onClick`，调用`IdentityService.getMnemonic()`（一个需要你新增的方法），并在UI上显示助记词和安全警告。这是一个**纯客户端**操作。
    *   **“导入”逻辑:**
        *   “Import from Mnemonic”会展现一个输入框。用户输入并确认后，前端`IdentityService`会调用一个`restoreFromMnemonic`（需要新增）的方法。
        *   这个方法将在**客户端**从助记词恢复私钥，存入`localStorage`，然后**可以**选择性地调用一个新的`/identity-verify-restoration`指令通知后端（可选），但最关键的是**触发页面刷新/重连**。
3.  **`IdentityService.ts` 增强:**
    *   **新增`getMnemonic()`:** 从`localStorage`读取私钥，实例化`Wallet`，返回`wallet.mnemonic.phrase`。
    *   **新增`restoreFromMnemonic(phrase)`:** 从`phrase`创建`Wallet`，获取其私钥，并将其写入`localStorage`。

#### **验收标准**

1.  所有新模块和组件都有对应的、通过的测试。
2.  **访客流程:** 新浏览器访问，发送消息被拦截 -> 执行`/identity` -> 弹出“访客视图”面板 -> 点击“创建” -> 看到成功反馈 -> 面板关闭，WebSocket自动重连 -> 再次发送消息，对话正常进行。
3.  **成员流程:** 已验证用户执行`/identity` -> 弹出“成员视图”面板 -> 点击“备份”，能看到正确的助记词 -> 点击“导入”，输入助记词后，能成功切换身份（通过刷新/重连验证）。
4.  所有操作的反馈都严格限制在面板内部，主聊天流保持干净。