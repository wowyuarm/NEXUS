好的，禹。

**`AURA-TESTS-FOUNDATION`** 任务的完成，标志着我们已经为AURA前端的核心“心智”（`auraStore`）和“骨架”（关键UI组件）构建了坚实的质量保证。

至此，我们项目的**“加固”阶段已全面胜利**。NEXUS后端和AURA前端，现在都拥有了各自的、强大的自动化测试套件。

我们的“思想体现”，不仅形态优美，而且筋骨强健。

---

### **下一步行动：自动化与扩展 (Automation & Expansion)**

我们现在可以充满信心地，进入下一个宏大的篇章。根据我们之前的战略规划，我们的航线非常清晰：

1.  **`CICD-SETUP`**: 将我们刚刚完成的所有测试，安装到自动化的“质量传送带”上。
2.  **`AURA-EXPANSION-COMMANDS`**: 在质量得到保障的前提下，开始扩展AURA的核心交互能力。

**我坚信，我们应该首先完成`CICD-SETUP`。** 这是一个一次性的、高价值的基础设施投资。一旦完成，我们未来所有的扩展工作，都将享受到自动化测试带来的速度与安全感。

---
### **任务委托单：CICD-SETUP-FULL**

**致：** 工程师AI

**发令者：** “枢”，NEXUS项目首席AI架构师

**主题：** 构建NEXUS & AURA的完整、覆盖前后端的CI流水线

**任务ID：** `CICD-SETUP-FULL`

---

**指令头 (Preamble):**
你是一位资深的DevOps工程师，精通使用GitHub Actions构建复杂的自动化工作流。你的任务是为NEXUS & AURA项目创建一个完整的CI（持续集成）流水线。这个流水线必须能够在代码提交时，自动地、并行地对前后端进行全面的质量检查。

---

#### **第一部分：任务目标 (Objective)**

你的任务是创建一个GitHub Actions工作流文件，该文件必须实现以下功能：

1.  **触发机制**: 工作流应在代码被`push`到`main`分支，或者有新的`pull_request`提交到`main`分支时自动触发。
2.  **并行执行**: 后端的测试和前端的测试，应该在两个**并行**的`jobs`中运行，以最大限度地提高效率。
3.  **后端质量检查 (Backend CI Job)**:
    *   设置Python环境。
    *   安装后端依赖。
    *   **运行后端的所有测试**（单元测试 + 集成测试）。
4.  **前端质量检查 (Frontend CI Job)**:
    *   设置Node.js环境。
    *   安装前端依赖。
    *   **运行前端的所有测试**（`pnpm test`）。
    *   （可选但推荐）运行`pnpm build`，以确保前端项目可以被成功构建。
5.  **最终状态**: 只有当**所有**并行的jobs都成功完成后，整个工作流才算成功。任何一个job的失败，都将导致整个工作流失败。

#### **第二部分：文件与核心指令 (Files & Core Instructions)**

你将创建一个新的文件（或修改现有的`manual_deploy.yml`，我建议创建一个新的、专门的`ci.yml`）。

**新文件: `.github/workflows/ci.yml`**

*   **核心指令**:
    *   **`name`**: `NEXUS & AURA CI`
    *   **`on`**:
        ```yaml
        push:
          branches: [ main ]
        pull_request:
          branches: [ main ]
        ```
    *   **`jobs`**:
        *   **`backend-ci` (Job 1)**:
            *   `name`: `Backend CI (Python)`
            *   `runs-on`: `ubuntu-latest`
            *   **`steps`**:
                1.  检出代码 (`actions/checkout@v4`)。
                2.  设置Python 3.11 (`actions/setup-python@v5`)。
                3.  安装依赖 (`pip install -r requirements.txt`)。
                4.  **运行测试**:
                    *   `run`: `pytest tests/nexus/`
                    *   **关键**: 必须为该步骤提供所有必需的环境变量，以便测试能够运行。由于这只是CI，不涉及部署，我们可以使用一些**测试专用的、非敏感的**密钥，或者直接在GitHub Secrets中设置。
        *   **`frontend-ci` (Job 2)**:
            *   `name`: `Frontend CI (Node.js)`
            *   `runs-on`: `ubuntu-latest`
            *   `defaults.run.working-directory`: `aura` (让这个job下的所有命令都在`aura/`目录中运行)。
            *   **`steps`**:
                1.  检出代码 (`actions/checkout@v4`)。
                2.  设置Node.js 18并启用`pnpm`缓存 (`pnpm/action-setup`, `actions/setup-node@v4`)。
                3.  安装依赖 (`pnpm install`)。
                4.  **运行测试**: `run`: `pnpm test`。
                5.  **构建检查**: `run`: `pnpm build`。

---
**交付要求：**
你必须提供`.github/workflows/ci.yml`的完整、可直接使用的代码。工作流必须能够正确地并行执行前后端的质量检查，并将测试失败作为阻塞条件。

**任务开始。**

---
---

创建一个独立的GitHub Actions工作流，该工作流**只能被手动触发**，其唯一职责是将最新的`main`分支代码部署到Render.com。

---

#### **核心指令**

**1. 新文件: `.github/workflows/manual_deploy.yml`**

*   **`name`**: `Manual Deploy to Render`
*   **`on.workflow_dispatch`**:
    *   **必须**只包含这个触发器。
    *   **（可选但推荐）** 可以添加`inputs`，让用户在触发时可以选择是只部署前端、只部署后端，还是全部部署。
        ```yaml
        inputs:
          target:
            description: 'Which service to deploy'
            required: true
            default: 'all'
            type: choice
            options:
              - all
              - backend
              - frontend
        ```
*   **`jobs`**:
    *   **`deploy` (Job)**:
        *   `name`: `Deploy to Render`
        *   `runs-on`: `ubuntu-latest`
        *   **`steps`**:
            1.  **`actions/checkout@v4`**: 检出代码。
            2.  **`Trigger Backend Deploy`**:
                *   添加`if: github.event.inputs.target == 'all' || github.event.inputs.target == 'backend'`条件。
                *   使用`curl`向`secrets.RENDER_DEPLOY_HOOK_BACKEND`发送`POST`请求。
                *   添加一个清晰的`echo`消息，例如`echo "Triggering backend deployment..."`。
            3.  **`Trigger Frontend Deploy`**:
                *   添加`if: github.event.inputs.target == 'all' || github.event.inputs.target == 'frontend'`条件。
                *   使用`curl`向`secrets.RENDER_DEPLOY_HOOK_FRONTEND`发送`POST`请求。
                *   添加一个清晰的`echo`消息。

---
**交付要求：**
你必须提供`.github/workflows/manual_deploy.yml`的完整代码。这个工作流必须：
1.  只能被手动触发。
2.  能够根据用户输入，选择性地或全部地触发Render的部署钩子。
3.  正确地使用GitHub Secrets来获取部署URL。