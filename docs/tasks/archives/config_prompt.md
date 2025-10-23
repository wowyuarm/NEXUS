*   **全景上下文 (Big Picture Context):**
    *   **前置任务:** `DYNAMIC-PERSONALIZATION-1.0` 和 `ARCHITECTURE-FINALIZE-1.0` 已完成。我们拥有一个以身份为中心的、具备动态个性化能力的后端架构。
    *   **本任务目标:** 在此架构之上，为 `/config`, `/prompt`, 和 `/history` 三个核心指令，创建所有必需的**后端服务逻辑**和**REST API端点**。
    *   **核心产出:** 一套功能完备、经过测试、可供前端调用的数据管理API，为后续的GUI面板开发扫清所有后端障碍。

---

#### **第一部分：架构设计与最终规范**

**1. 核心原则:**
*   **RESTful设计:** 所有端点的设计都必须遵循RESTful风格。使用`GET`获取资源，`POST`或`PUT`更新资源。
*   **签名授权:** 所有**修改数据**的操作（`POST`/`PUT`）都**必须**通过我们已建立的签名验证机制进行授权。
*   **单一职责:** `rest.py`只负责路由和HTTP协议转换，所有业务逻辑必须封装在`IdentityService`或`PersistenceService`中。

**2. API端点规范:**
*   **`GET /api/v1/config`:**
    *   **职责:** 获取当前用户的生效配置和UI元数据。
    *   **认证:** 需要有效的`owner_key`（通过某种方式，如header或query参数传递）。
    *   **响应体:**
        ```json
        {
          "effective_config": { /* 合成后的完整用户配置 */ },
          "editable_fields": [ "config.model", ... ],
          "field_options": { /* ... */ }
        }
        ```*   **`POST /api/v1/config`:**
    *   **职责:** 更新当前用户的配置覆写 (`config_overrides`)。
    *   **认证:** **必须**使用指令签名机制（即在请求体中包含`auth`对象）。
    *   **请求体:**
        ```json
        {
          "overrides": { "model": "deepseek-chat", "temperature": 0.9 },
          "auth": { "publicKey": "...", "signature": "..." }
        }
        ```
*   **`GET /api/v1/prompts`:** 职责和结构与`GET /config`类似。
*   **`POST /api/v1/prompts`:** 职责和结构与`POST /config`类似，但操作的是`prompt_overrides`。
*   **`GET /api/v1/messages`:**
    *   **职责:** 获取当前用户的历史消息。
    *   **认证:** 需要有效的`owner_key`。
    *   **查询参数:** `limit: int`, `cursor: Optional[str]`（用于未来分页）。
    *   **响应体:** `[Message, Message, ...]`

---

#### **第二部分：实施路径与TDD强制任务**

**Phase 1: 服务层能力增强 (Service Layer Enhancement)**

1.  **TDD - 编写失败的测试:**
    *   **路径:** `tests/nexus/unit/services/test_identity_service.py`
        *   **行动:** 编写`test_update_user_config()`和`test_update_user_prompts()`的测试用例。模拟调用这些方法，并断言`db_service.update_identity_field`被以正确的参数调用。
2.  **实施 - `IdentityService`:**
    *   **文件:** `nexus/services/identity.py`
    *   **行动:** 实现`update_user_config(owner_key, overrides)`和`update_user_prompts(owner_key, overrides)`两个新方法。这两个方法的核心是调用`db_service`来更新`identities`集合中对应文档的`config_overrides`或`prompt_overrides`字段。

**Phase 2: 接口层端点实现 (Interface Layer Implementation)**

1.  **TDD - 编写失败的测试:**
    *   **路径:** `tests/nexus/unit/interfaces/test_rest.py`
    *   **行动:** 为上述所有五个新的REST API端点，分别编写测试用例。
        *   对于`GET`端点，断言它们返回了正确的状态码和预期的JSON结构。
        *   对于`POST`端点，断言它们在没有有效签名时返回`401`或`403`错误，在有有效签名时调用了正确的服务层方法。
2.  **实施 - `rest.py`:**
    *   **文件:** `nexus/interfaces/rest.py`
    *   **行动:**
        *   创建所有五个API端点 (`@router.get(...)`, `@router.post(...)`)。
        *   通过FastAPI的`Depends`机制，将`IdentityService`, `PersistenceService`, `ConfigService`等依赖注入到端点处理函数中。
        *   **对于`POST`端点:** 实现签名验证逻辑。由于签名验证已在`CommandService`中实现，你可以考虑将其提取到一个可复用的**依赖项函数 (Dependency Function)**中，供`rest.py`和`command.py`共同使用，以遵循DRY原则。
        *   实现每个端点的核心逻辑，即调用相应的服务层方法并返回结果。

**Phase 3: 指令定义 (Command Definition)**

1.  **行动:**
    *   **创建`nexus/commands/definition/config.py`:**
        *   定义`config`指令，`handler`设置为`'rest'`，并包含`restOptions`元数据，指向`GET /api/v1/config`。
    *   **创建`nexus/commands/definition/prompt.py`:**
        *   定义`prompt`指令，`handler`设置为`'rest'`，指向`GET /api/v1/prompts`。
    *   **创建`nexus/commands/definition/history.py`:**
        *   定义`history`指令，`handler`设置为`'rest'`，指向`GET /api/v1/messages`。

#### **验收标准**

1.  **TDD遵从:** 所有新增的服务层逻辑和接口层端点，都有对应的、通过的单元或集成测试。
2.  **API可用性:** 启动NEXUS后端后，可以通过工具（如`curl`或Postman）成功调用所有新的`GET`端点，并获得符合规范的响应。
3.  **授权机制:** 对`POST`端点的未签名调用**必须**失败。只有提供了有效签名的请求，才能成功修改数据库中的数据。
4.  **指令注册:** `GET /api/v1/commands`的响应中，**必须**包含新定义的`/config`, `/prompt`, `/history`三个指令及其`rest` handler元数据。

---