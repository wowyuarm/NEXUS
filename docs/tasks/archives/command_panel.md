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

 `MODAL-SYSTEM-FOUNDATION-1.0`已完成。我们拥有一个通用的模态交互系统 (`<Modal>`, `<Panel>`, `uiStore`)。（你需要了解清楚，有足够全面上下文）
    *   **本任务目标:** 在此模态系统之上，构建一个功能完备、体验优雅的`/identity` GUI面板。这个面板是用户行使其“自我主权”的核心工具，必须做到安全、直观、且反馈清晰。

---

#### **第一部分：设计哲学与预期效果 (The "Why" & The "What")**

**1. 核心原则:**
*   **主权可视化:** 这个面板不是一个简单的信息展示，它是用户“知觉密钥”所有权的**物理化身**。它的设计必须传达出安全、私密和掌控感。
*   **状态驱动的清晰度:** 面板的形态和可执行的操作，必须严格根据用户当前的身份状态（“访客”或“成员”）进行变化，为用户提供清晰、无歧义的引导。
*   **反馈闭环:** 用户的每一个关键操作，都必须得到**双重反馈**：面板内的**即时反馈**（用于即时确认），和对话流中的**永久记录**（用于事后追溯）。

**2. 预期的视觉与交互效果:**
*   **触发:** 用户在`CommandPalette`中选择并执行`/identity`指令。
*   **呈现:** 一个标题为“身份管理 (Identity Management)”的`<Panel />`在`<Modal />`中平滑出现。
*   **条件化UI:**
    *   **如果用户是“访客” (`visitorMode === true`):**
        *   面板将显示引导性文本，如“您当前为访客身份，对话历史不会被保存。”
        *   提供两个核心按钮：“**创建新身份**”和“**导入已有身份**”。
    *   **如果用户是“成员” (`visitorMode === false`):**
        *   面板将显示用户的“存在地址”（公钥）。
        *   提供两个核心按钮：“**导出身份 (备份)**”和“**切换/导入身份**”。
*   **交互反馈:**
    *   **点击“创建/导入/导出”后:** 按钮进入加载状态。操作成功后，按钮旁出现一个绿色的“✓”图标和简短的成功提示文本（例如“身份已创建！”、“助记词已复制到剪贴板！”），持续2-3秒后消失。
    *   **关闭面板后:** 对话流中出现一条`SYSTEM`消息，记录本次操作的结果，例如`■ /identity (created)`，结果区显示“新的主权身份已成功锚定。”

---

#### **第二部分：架构与实施路径 (The "How")**

**Phase 1: 前端能力增强 (Frontend Capability Enhancement)**

1.  **`aura/src/services/identity/identity.ts` (核心能力):**
    *   **TDD先行:** 为即将新增的方法编写测试。
    *   **新增`exportMnemonic()`:**
        *   从`localStorage`读取私钥。
        *   实例化`ethers.Wallet`。
        *   返回`wallet.mnemonic.phrase`。
    *   **新增`importFromMnemonic(mnemonic: string)`:**
        *   使用`ethers.Wallet.fromPhrase(mnemonic)`验证助记词并创建钱包实例。
        *   获取其`privateKey`和`publicKey`。
        *   用新的`privateKey`**覆写**`localStorage`中的`nexus_private_key`。
        *   返回新的`publicKey`。
2.  **`aura/src/features/chat/store/chatStore.ts`:**
    *   **新增`setVisitorMode(isVisitor: boolean)` action**，用于控制访客状态。
    *   **新增`createFinalSystemMessage(command: string, result: string)` action**，用于在前端直接创建一条`status: 'completed'`的`SYSTEM`消息。

**Phase 2: 后端指令适配 (Backend Command Adaptation)**

1.  **`nexus/commands/definition/identity.py`:**
    *   **简化与聚焦:** 我们不再需要复杂的子指令。`/identity`本身的核心职责，在GUI模式下，就是**创建身份**。
    *   **重构`execute`函数:** 它的功能保持不变（调用`identity_service.get_or_create_identity`），但返回的成功消息应更专注于“创建/验证成功”这一点。
    *   **移除`requiresGUI: True`:** 这个元数据现在由前端的`commandExecutor`来决定。后端的`/identity`指令应该是一个纯粹的、可被调用的`websocket`指令。

**Phase 3: GUI面板的构建与集成 (The Main Event)**

1.  **`aura/src/features/command/components/IdentityPanel.tsx` (新建):**
    *   **TDD/Component-Testing先行:** 使用`@testing-library/react`编写组件测试。
    *   **状态获取:** 从`chatStore`中`use`出`visitorMode`状态，从`identityStore`获取`publicKey`。
    *   **条件渲染:** 使用`visitorMode`来渲染“访客”或“成员”的UI视图。
    *   **按钮逻辑 - “创建新身份”:**
        1.  调用`commandExecutor.executeCommand('/identity')`。这是一个`websocket`指令。
        2.  在Promise的`.then()`中，显示成功的即时反馈，并触发WebSocket重连（或页面刷新），让后端“门禁”重新验证新成员身份。
        3.  在`.finally()`中，调用`uiStore.closeModal()`。
    *   **按钮逻辑 - “导出身份”:**
        1.  调用`IdentityService.exportMnemonic()`。
        2.  将返回的助记词安全地展示给用户（例如，在一个需要用户确认才能显示的区域），并提供“复制到剪贴板”的功能。
        3.  显示成功的即时反馈。
    *   **按钮逻辑 - “导入身份”:**
        1.  从输入框获取助记词。
        2.  调用`IdentityService.importFromMnemonic(mnemonic)`。
        3.  成功后，用返回的新`publicKey`**立即触发WebSocket重连** (`websocketManager.reconnect(newPublicKey)`)。
        4.  显示成功的即时反馈，关闭Modal。
2.  **`aura/src/app/App.tsx`:**
    *   将`<IdentityPanel />`的占位符，替换为真正的组件实例。
3.  **`aura/src/features/command/commandExecutor.ts`:**
    *   修改`executeCommand`函数：
        *   对于`/identity`指令，不再直接发送WebSocket请求，而是调用`uiStore.getState().openModal('identity')`。

#### **验收标准**

1.  **访客流程:** 新浏览器访问，输入`/identity`，弹出的面板**必须**显示“创建”和“导入”按钮。
    *   点击“创建”，操作成功后，关闭面板，对话流中出现一条记录消息。再次打开面板，**必须**切换到“成员”视图。
2.  **成员流程:** 已有身份的浏览器访问，输入`/identity`，弹出的面板**必须**显示公钥和“导出”、“切换/导入”按钮。
    *   点击“导出”，**必须**能正确显示并复制助记词。
3.  **恢复流程:** 在访客状态下，点击“导入”，粘贴从成员流程中导出的助记词，操作成功后，关闭面板，**必须**能看到之前的对话历史被无缝加载回来。
4.  **反馈闭环:** 所有关键操作（创建、导入）成功并关闭面板后，对话流中**必须**留下一条对应的、格式正确的`SYSTEM`消息记录。