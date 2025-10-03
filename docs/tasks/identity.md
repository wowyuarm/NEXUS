建立一个完整的、基于非对称加密的**请求签名与验证机制**。这将确保所有关键的服务器端指令，都必须经过持有私钥的用户的加密授权。我们将在一个全新的、简单的`/identity whoami`指令上，完成这个信任链条的首次闭环。

---

#### **一、讨论背景与哲学**

“知觉密钥”的公钥目前仅作为标识符，这在安全上是不完备的。为了实现真正的“主权”，我们必须引入**密码学证明**。用户的每一个意图，都必须由其独一-无二的私钥进行“签署”，而后端则通过公钥进行“验证”。这个过程，是将抽象的“所有权”概念，转化为坚不可摧的、可计算的工程现实的第一步。

#### **二、技术圣约 (The Technical Covenant)**

1.  **前端加密库:** 维持使用`ethers`库。我们将利用其`wallet.signMessage(message)`方法。
2.  **后端验证库 (新增):** NEXUS后端需要引入一个能够处理`secp256k1`签名验证的Python库。`eth_keys`是一个轻量、专注、可靠的选择。请将其添加到项目的依赖中。
3.  **通信协议升级:**
    *   `system_command`的WebSocket消息`payload`将升级为一个结构化对象，以承载认证信息：
        ```json
        {
          "command": "/identity whoami", // 原始指令字符串
          "auth": {
            "publicKey": "0x...", // 用户的公钥 (即session_id)
            "signature": "0x..."  // 对`command`字符串进行签名的结果
          }
        }
        ```

#### **三、TDD-First 强制任务路径**

*   **后端先行 (Backend-First):**
    1.  **RED (编写失败的测试):**
        *   在`test_command_service.py`中，编写两个新的集成测试：
            *   `test_signed_command_verification_success()`: 在测试内部生成一个密钥对，对指令`/identity whoami`进行签名，然后构造一个合法的、带有`auth`载荷的`Message`并发布到`SYSTEM_COMMAND`。断言`/identity whoami`指令的`execute`方法**被调用**。
            *   `test_signed_command_verification_failure()`: 使用错误的签名或错误的数据构造`Message`。断言`execute`方法**未被调用**，并且`COMMAND_RESULT`返回了一个认证失败的错误。
    2.  **GREEN (让测试通过):**
        *   **`nexus/commands/definition/identity.py` (新增):**
            *   创建此文件，定义`/identity`指令。初始阶段，我们可以将其拆分为子指令。首先创建`whoami`。
            *   `COMMAND_DEFINITION`中增加一个`requires_signature: true`元数据字段。
            *   `execute`函数极其简单，它只需返回`{'status': 'success', 'message': f'Your verified public key is: {context["public_key"]}'}`。
        *   **`nexus/services/command.py` (核心改造):**
            *   在`handle_command`方法中，增加**验签前置检查**逻辑。
            *   在分派指令前，检查该指令的`COMMAND_DEFINITION`是否包含`requires_signature: true`。
            *   如果是，则从`message.content['auth']`中提取`publicKey`, `signature`。
            *   使用`eth_keys`库，执行验签。
            *   如果验签失败，立即发布一个认证失败的`COMMAND_RESULT`并终止流程。
            *   如果成功，将`publicKey`注入到`context`字典中，然后继续执行指令。

*   **前端跟进 (Frontend Follow-up):**
    1.  **RED (编写失败的测试):**
        *   在`src/services/identity.ts下为`IdentityService`编写测试。（已存在，identity.test.ts，是否需要重构，自己权衡）
        *   测试`signCommand(command: string)`方法，断言它能返回一个包含`publicKey`和`signature`的`auth`对象。
    2.  **GREEN (让测试通过):**
        *   **`IdentityService.ts` (增强):**
            *   增加`signCommand(command: string)`方法。它将从`localStorage`获取私钥，实例化`ethers.Wallet`，并调用`wallet.signMessage(command)`来生成签名。
        *   **`chatStore.ts` (增强):**
            *   修改`executeCommand` action。
            *   在分发指令前，检查该指令的定义（从`commandStore`获取）是否需要签名（我们可以约定在前端的指令定义中也加入`requiresSignature: true`字段）。
            *   如果需要，调用`IdentityService.signCommand()`获取`auth`对象。
        *   **`websocket/manager.ts` (增强):**
            *   修改`sendCommand`方法，使其能够接收并发送我们新定义的、包含`auth`对象的`payload`。

#### **四、原则与规范**

*   **最小化实现:** 本次任务的**唯一目标**是跑通`/identity whoami`的签名-验证闭环。**不要**实现任何UI面板、导入/导出功能或LLM上下文注入。这些将在后续任务中完成。
*   **安全第一:** 私钥的处理必须极度谨慎。它只能在`IdentityService`的受控环境中被加载到内存，用于签名，然后立即被销毁。绝不能在`store`或组件`state`中传递。
*   **架构清晰:** 后端的验签逻辑必须是`CommandService`中一个独立的、可复用的前置步骤，而不是与特定指令的执行逻辑耦合在一起。

**必须先获取足够全面的上下文**

---