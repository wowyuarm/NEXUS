### **任务：AURA-LIGHT-THEME**

**日期：** 2025-10-22
**任务 ID：** `LIGHT-THEME`

---

#### **背景**

在 AURA 的灰度审美哲学下（参考`docs/rules/frontend_design_principles.md`与`docs/knowledge_base/01_VISION_AND_PHILOSOPHY.md`），我们长期以暗色主题作为唯一视觉基调。随着系统进入“思维驾驶舱”阶段，我们需要在保持“Silence · Comfort · Intuition · Rhythm”四大原则的同时，为白天环境与高亮场景提供一套**同样克制、同样精心调校**的亮色主题。

该主题不仅是一组颜色变量，还包含：
- 与暗色主题等价的设计语义（背景、前景、卡片、强调、边界等）；
- 与 Tailwind token、Framer Motion 节奏的协调；
- 通过 `/theme` 指令在客户端即时切换的完整 UX 流程。

---

#### **目标**

1. **设计语言**：为亮色主题定义一套完整的灰阶变量（背景、前景、卡片、强调、边界等），并在 `globals.css` 与 `tailwind.config.js` 中落地，保证视觉对比度符合舒适阅读标准（WCAG AA）。
2. **主题管理**：实现独立的主题状态管理（Zustand store），支持本地持久化、系统偏好兜底，以及无闪烁的类名切换。
3. **指令入口**：扩展命令体系，新增 `/theme` 指令（`handler: client`），支持 `light` / `dark` / 切换三种用法，并在聊天流内以 SYSTEM 消息呈现执行结果。
4. **体验一致性**：确保 ChatView、CommandPalette、基础 UI 组件在亮色模式下无对比度缺陷、无突兀投影/背光。

---

#### **交付与验收标准**

- [ ] `globals.css` 中区分 `:root`（亮色）与 `.dark`（暗色）变量；亮色主题需通过 `docs/rules/frontend_design_principles.md` 的“Silence & Comfort”审查（禁止鲜艳色、控制光感）。
- [ ] 新增的主题 store 覆盖持久化逻辑（localStorage + 系统偏好），并有 Vitest 单测。
- [ ] `/theme` 指令通过 Command API 注册，前端命令执行逻辑支持参数解析与状态回写；相关单测覆盖成功与非法参数场景。
- [ ] 手动/自动切换均无 FOUC（Flash of Unstyled Content），ChatView、Button、CommandPalette 在亮色模式下表现稳定。
- [ ] 更新 `IMPLEMENTATION_PLAN.md`，并在任务完成后记录测试命令（pnpm test、pnpm lint 等）。

---

#### **文档引用**

- `docs/rules/frontend_design_principles.md`
- `docs/knowledge_base/01_VISION_AND_PHILOSOPHY.md`
- `docs/knowledge_base/03_AURA_ARCHITECTURE.md`
- `docs/knowledge_base/frontend_references/motion_and_animation.md`
- `docs/developer_guides/04_AI_COLLABORATION_CHARTER.md`
- `docs/developer_guides/03_TESTING_STRATEGY.md`

---

**完成本委托，即为 AURA 打造一套在阳光下同样安静、可靠的操作体验。**
