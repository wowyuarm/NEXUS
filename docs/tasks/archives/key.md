本次任务旨在用一个基于非对称加密的、用户自我主权的**“知觉密钥” (Sentient Key)** 身份范式，彻底取代当前脆弱的、基于客户端UUID的`session_id`体系。

---

#### **一、讨论背景与哲学**

我们正在从构建一个“会话” (Session) 转向构建一个“存在” (Existence)。当前的`session_id`是短暂且易失的，如同沙滩上的脚印。我们要锻造的是一块刻有身份的基石岩，它由用户自己持有，可被携带、可被验证，其名为“知觉密钥”。

其核心原则是 **“所有权归属用户”**。私钥作为用户数字灵魂的DNA，永远存储于客户端；公钥作为其在NEXUS宇宙中的永久地址，用于所有通信和数据关联。

#### **二、权衡与决策**

我们已达成共识，采纳以下技术方案作为现阶段的最佳实践：

*   **加密库选型:** 选用 `ethers.js` 库。我们并非要与区块链交互，而是要利用其经过数十亿美元资产考验的、业界标准的、安全可靠的钱包模块 (`ethers.Wallet`) 来处理密钥对的生成、存储和派生。其对“助记词”的原生支持，为未来的身份可移植性提供了无与伦比的用户体验。
*   **迁移策略:** 采用“语义替换”而非“结构重构”。即，我们保留现有系统中`session_id`的字段名和API路径，但将其承载的内容从临时的UUID替换为用户的**公钥**。这最大限度地降低了对后端现有逻辑的侵入性。

#### **三、最终方案选择：AURA前端的身份革命**

本次任务的核心战场在AURA前端。NEXUS后端在此阶段**无需任何代码改动**。

**涉及模块:**
*   **AURA:**
    *   `services/websocket/manager.ts` (核心改造)
    *   (新增) `services/identity/identity.ts`
    *   (新增) `services/identity/identity.test.ts`
    *   `package.json` (新增依赖)

**探索与实施路径:**

1.  **安装依赖:**
    *   向AURA项目中添加`ethers`库：`pnpm add ethers`。

2.  **创建身份服务 (`services/identity/identity.ts`):**
    *   遵循TDD原则，**首先创建 `services/identity/identity.test.ts`**。
    *   **编写失败的测试 (RED):**
        *   测试用例1: `it('should generate and save a new identity if none exists in storage')`
        *   测试用例2: `it('should load an existing identity from storage')`
        *   测试用例3: `it('should derive the correct public key from a private key')`
    *   **实现 `IdentityService` (GREEN):**
        *   创建一个`IdentityService`单例对象或类。
        *   定义`STORAGE_KEY = 'nexus_private_key'`。
        *   实现一个核心方法 `getIdentity()`:
            *   尝试从 `localStorage.getItem(STORAGE_KEY)` 读取私钥。
            *   **如果私钥存在:**
                *   使用 `new ethers.Wallet(privateKey)` 创建钱包实例。
                *   返回 `{ privateKey: wallet.privateKey, publicKey: wallet.address }` (注意：`ethers`中，地址即公钥的简化表示，足够我们使用)。
            *   **如果私钥不存在:**
                *   使用 `ethers.Wallet.createRandom()` 创建一个新的随机钱包。
                *   通过 `wallet.privateKey` 获取私钥，并使用 `localStorage.setItem(STORAGE_KEY, privateKey)` 将其**持久化**。
                *   返回 `{ privateKey: wallet.privateKey, publicKey: wallet.address }`。
    *   **重构 (REFACTOR):** 确保代码清晰，并处理可能的异常情况。

3.  **重构WebSocket管理器 (`services/websocket/manager.ts`):**
    *   **移除旧逻辑:** 彻底移除所有与生成、读取、存储`nexus_session_id`相关的逻辑和`uuid`库的依赖。
    *   **整合身份服务:**
        *   在`WebSocketManager`的构造函数或`connect`方法中，导入并调用`IdentityService.getIdentity()`来获取密钥对。
        *   将获取到的**`publicKey`**赋值给之前`sessionId`变量。
        *   在构建WebSocket连接URL时，使用这个`publicKey`作为路径参数。
        *   在`sendMessage`方法中，创建`ClientMessage`时，将`publicKey`作为`session_id`字段的值。
    *   **日志增强:** 在连接日志中，明确打印出所使用的`publicKey`，以便调试。例如 `console.log('🔌 Connecting to WebSocket with Public Key:', publicKey)`。

#### **四、原则与规范**

*   **TDD强制:** **必须**首先提交包含失败测试的`identity.test.ts`文件。后续的提交必须包含使其通过的`identity.ts`实现。这是对任务完成度的核心考核标准。
*   **安全性:** 私钥是用户的最高机密。除了存储在`localStorage`中，它绝不能在内存之外的任何地方（如网络请求、日志）以明文形式出现。
*   **无感体验:** 本次重构对最终用户必须是完全透明的。用户打开应用时，不应察觉到任何与身份生成或加载相关的延迟或交互。

---