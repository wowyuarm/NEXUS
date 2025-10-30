为NEXUS后端与AURA前端创建生产级的Dockerfile 为NEXUS后端和AURA前端分别编写一个优化的、生产就绪的`Dockerfile`。这些文件必须能够构建出最小化、安全且高效的Docker镜像。

---

#### **第一部分：NEXUS后端容器化**

**1. 文件路径**:
*   `NEXUS/Dockerfile` (在项目根目录下创建新文件)

**2. 核心指令**:
*   **使用多阶段构建 (Multi-Stage Build)**: 以减小最终镜像的体积并提高安全性。
*   **第一阶段 (`builder`)**:
    *   **基础镜像**: 使用官方的`python:3.11-slim-bullseye`作为基础。
    *   **设置工作目录**: `/app`。
    *   **优化依赖缓存**:
        1.  **首先**只复制`requirements.txt`文件。
        2.  **然后**运行`pip install --no-cache-dir --upgrade -r requirements.txt`。这一步将被Docker缓存，只有当`requirements.txt`变化时才会重新运行。
    *   **复制应用代码**: 将整个`nexus/`目录复制到容器的`/app/nexus/`。
*   **第二阶段 (最终阶段)**:
    *   **基础镜像**: 同样使用`python:3.11-slim-bullseye`。
    *   **设置工作目录**: `/app`。
    *   **创建非root用户**: 为了安全起见，创建一个名为`nexususer`的非root用户，并切换到该用户。
    *   **复制依赖**: 从`builder`阶段，将安装好的Python包（位于`/usr/local/lib/python3.11/site-packages`）复制过来。
    *   **复制应用代码**: 从`builder`阶段，将`nexus/`目录复制过来。
    *   **暴露端口**: 使用`EXPOSE 8000`指令，声明容器将监听8000端口。
    *   **启动命令 (`CMD`)**: 设置容器的默认启动命令为`["python", "-m", "nexus.main"]`。

**3. 创建`.dockerignore`文件**:
*   **文件路径**: `NEXUS/.dockerignore` (在项目根目录下创建新文件)
*   **内容**:
    ```
    .venv/
    __pycache__/
    *.pyc
    *.pyo
    *.pyd
    .pytest_cache/
    .git/
    .idea/
    .vscode/
    tests/
    ```
    *   **目的**: 确保在构建镜像时，不会将不必要的本地开发文件和目录复制进去。

---

#### **第二部分：AURA前端容器化**

**1. 文件路径**:
*   `AURA/Dockerfile` (在`aura/`目录下创建新文件)

**2. 核心指令**:
*   **使用多阶段构建 (Multi-Stage Build)**: 这是前端容器化的关键，以确保最终镜像只包含静态文件和轻量级服务器。
*   **第一阶段 (`builder`)**:
    *   **基础镜像**: 使用官方的`node:18-alpine`作为基础。
    *   **设置工作目录**: `/app`。
    *   **优化依赖缓存**:
        1.  **首先**只复制`package.json`和`pnpm-lock.yaml`。
        2.  **然后**运行`pnpm install`。
    *   **复制应用代码**: 将所有源代码复制到容器中。
    *   **构建应用**: 运行`pnpm build`，这将会在`/app/dist`目录下生成生产环境的静态文件。
*   **第二阶段 (最终阶段)**:
    *   **基础镜像**: 使用一个极其轻量级的`nginx:stable-alpine`作为Web服务器。
    *   **复制静态文件**: 从`builder`阶段的`/app/dist`目录，将所有构建好的静态文件复制到Nginx的默认HTML目录 (`/usr/share/nginx/html`)。
    *   **配置Nginx**:
        1.  创建一个简单的Nginx配置文件`nginx.conf`。
        2.  这个配置文件需要配置Nginx监听80端口，并将所有请求都指向`index.html`，以支持React Router的单页应用（SPA）路由。
        3.  将这个`nginx.conf`文件复制到容器的`/etc/nginx/conf.d/default.conf`。
    *   **暴露端口**: `EXPOSE 80`。

**3. 创建`nginx.conf`文件**:
*   **文件路径**: `AURA/nginx.conf` (在`aura/`目录下创建新文件)
*   **内容**:
    ```nginx
    server {
        listen 80;
        server_name localhost;

        root /usr/share/nginx/html;
        index index.html;

        location / {
            try_files $uri $uri/ /index.html;
        }
    }
    ```

**4. 创建`.dockerignore`文件**:
*   **文件路径**: `AURA/.dockerignore` (在`aura/`目录下创建新文件)
*   **内容**:
    ```
    node_modules/
    dist/
    .git/
    .vscode/
    ```

---
**交付要求：**
你必须：
1.  提供`NEXUS/Dockerfile`和`NEXUS/.dockerignore`的完整内容。
2.  提供`AURA/Dockerfile`, `AURA/nginx.conf`, 和`AURA/.dockerignore`的完整内容。

这些文件必须遵循最佳实践，以构建出安全、高效、且体积最小化的生产级Docker镜像。

**任务开始。**

---
---
创建Docker Compose配置以实现本地一键启动与验证。创建一个`docker-compose.yml`文件，使得开发者可以通过一条命令，在本地构建并运行整个NEXUS和AURA应用栈，并验证它们之间的连通性。

---

#### **第一部分：任务目标 (Objective)**

你的任务是创建一个`docker-compose.yml`文件，它需要能够：
1.  **定义两个服务**: 一个是`nexus-backend`，另一个是`aura-frontend`。
2.  **自动构建镜像**: 从我们之前创建的`Dockerfile`自动构建每个服务的Docker镜像。
3.  **管理网络**: 将两个服务连接在同一个内部网络中，使它们可以相互通信。
4.  **配置环境变量**: 从根目录的`.env`文件加载环境变量，并将其注入到`nexus-backend`服务中。
5.  **映射端口**: 将容器的内部端口映射到我们本地机器的端口，以便我们可以通过浏览器访问。

#### **第二部分：文件与核心指令 (Files & Core Instructions)**

你将在项目根目录下创建一个新文件。

**1. 新文件: `NEXUS/docker-compose.yml`**
*   **任务**: 编写Docker Compose的配置文件。
*   **核心指令**:
    *   **版本**: 使用`version: '3.8'`或更高版本。
    *   **定义`services`**:
        *   **`nexus-backend`服务**:
            *   `build`:
                *   `context`: `./nexus` (指向包含后端`Dockerfile`的目录)。
                *   `dockerfile`: `Dockerfile`。
            *   `ports`:
                *   映射本地机器的`8000`端口到容器的`8000`端口 (`"8000:8000"`)。
            *   `env_file`:
                *   指定使用根目录下的`.env`文件 (`./.env`)。
            *   `container_name`: `nexus_backend_dev`。
            *   `restart`: `unless-stopped` (可选，但在开发中很有用)。
        *   **`aura-frontend`服务**:
            *   `build`:
                *   `context`: `./aura` (指向包含前端`Dockerfile`的目录)。
                *   `dockerfile`: `Dockerfile`。
            *   `ports`:
                *   映射本地机器的`5173`端口到容器的`80`端口 (`"5173:80"`)。Nginx容器默认监听80端口。
            *   `container_name`: `aura_frontend_dev`。
            *   `depends_on`:
                *   `nexus-backend` (可选，但这能表达服务间的启动依赖关系)。
            *   `restart`: `unless-stopped`。

#### **第三部分：本地验证流程 (Local Validation Workflow)**

在交付`docker-compose.yml`文件后，你需要向我（枢）提供以下**验证步骤**，以便我指导禹进行操作：

1.  **构建并启动服务**:
    *   在`NEXUS/`根目录下，运行命令 `docker-compose up --build`。
    *   `--build`参数会强制Docker根据我们最新的`Dockerfile`重新构建镜像。
    *   这条命令会启动两个容器，并在终端中显示它们的合并日志。

2.  **验证服务状态**:
    *   打开一个新的终端窗口。
    *   运行`docker-compose ps`来查看两个容器（`nexus_backend_dev`和`aura_frontend_dev`）是否都处于`Up`状态。

3.  **访问前端**:
    *   打开浏览器，访问`http://localhost:5173`。
    *   此时应该能看到AURA的初始界面。

4.  **验证连接**:
    *   打开浏览器的开发者工具，查看控制台（Console）和网络（Network）标签页。
    *   **关键验证点**:
        *   控制台应该显示WebSocket成功连接的日志。
        *   网络标签页的WS（WebSocket）过滤器下，应该能看到一个状态码为`101 Switching Protocols`的连接，其URL为`ws://localhost:5173/api/v1/ws/...`（注意：浏览器可能会显示连接到`5173`，但Nginx会代理到后端）。

5.  **进行端到端测试**:
    *   发送一条消息，观察整个交互流程是否如预期般工作。

6.  **停止服务**:
    *   在第一个终端窗口（运行`docker-compose up`的那个），按下`Ctrl + C`。
    *   然后运行`docker-compose down`来彻底停止并移除容器和网络。

---
**交付要求：**
你必须：
1.  提供`NEXUS/docker-compose.yml`的完整内容。
2.  提供上述清晰的、分步的**本地验证流程**，作为对你工作的最终验证指南。

**任务开始。**

---
---
本地Docker Compose环境的全面验证与核对。执行并验证一个基于`docker-compose.yml`的本地应用环境。你需要确保所有服务都按预期启动、互相连接。

---

#### **第一部分：上下文与准备工作 (Context & Setup)**

**上下文**:
*   项目根目录下存在一个`docker-compose.yml`文件，定义了`nexus-backend`和`aura-frontend`两个服务。
*   项目根目录下存在一个`.env`文件，其中包含所有必需的API密钥和数据库连接字符串。
*   `nexus/`和`aura/`目录下分别存在对应的`Dockerfile`。

**准备工作**:
1.  确保你本地的Docker Desktop或Docker Engine正在运行。
2.  在执行任何操作前，先运行一次清理命令，以确保环境是干净的：
    ```bash
    docker-compose down --volumes --remove-orphans
    ```

#### **第二部分：验证清单与预期效果 (Verification Checklist & Expected Outcomes)**

请严格按照以下清单，执行并核对每一步的预期效果。

**1. 构建阶段 (Build Phase)**
*   **指令**:
    ```bash
    # 在 NEXUS/ 根目录下
    docker-compose build
    ```
*   **预期效果**:
    *   [ ] `nexus-backend`和`aura-frontend`两个服务的镜像都成功构建，没有任何`ERROR`级别的日志。
    *   [ ] 整个过程应该在合理的时间内完成（首次构建可能较长，后续会利用缓存）。
    *   [ ] 运行`docker images`后，可以看到新创建的`nexus-nexus-backend`和`nexus-aura-frontend`镜像（`docker-compose`会自动为镜像添加项目名前缀）。

**2. 启动阶段 (Launch Phase)**
*   **指令**:
    ```bash
    docker-compose up
    ```
*   **预期效果**:
    *   [ ] `nexus_backend_prod`容器首先开始启动。
    *   [ ] 你可以在终端日志中看到NEXUS后端服务（`Orchestrator`, `LLMService`等）成功初始化的`INFO`日志。
    *   [ ] 后端服务的健康检查（`healthcheck`）开始运行，并最终变为`healthy`状态。
    *   [ ] **只有在**后端变为`healthy`之后，`aura_frontend_prod`容器才开始启动。
    *   [ ] 你可以看到Nginx成功启动并开始监听端口的日志。
    *   [ ] 最终，两个容器都处于稳定运行状态，终端没有持续报错。

**3. 连接性与功能验证 (Connectivity & Functional Verification)**
*   **操作**:
    1.  打开一个新的终端，运行`docker ps`。
    2.  打开你的Web浏览器，访问`http://localhost:5173`。
    3.  打开浏览器的开发者工具，切换到“控制台 (Console)”和“网络 (Network)”面板。
*   **预期效果**:
    *   [ ] `docker ps`的输出显示`nexus_backend_prod`和`aura_frontend_prod`两个容器都处于`Up`状态，并且`STATUS`栏中应包含`(healthy)`字样。
    *   [ ] AURA前端页面成功加载，显示`NEXUS`标题和居中的输入框。
    *   [ ] 在浏览器控制台中，**必须**能看到`WebSocket connected to NEXUS`的日志。
    *   [ ] 在“网络”面板中，可以看到对`/api/v1/ws/...`的WebSocket连接请求，其状态码为`101 Switching Protocols`。

**4. 清理阶段 (Teardown Phase)**
*   **指令**:
    ```bash
    # 在运行 docker-compose up 的终端中，按下 Ctrl+C
    # 或者在另一个终端中运行
    docker-compose down
    ```
*   **预期效果**:
    *   [ ] 两个容器都优雅地停止。
    *   [ ] `nexus-net`网络被自动移除。
    *   [ ] 运行`docker ps -a`后，看不到已停止的`nexus_backend_prod`和`aura_frontend_prod`容器。

---
**交付要求：**
请你（工程师AI）严格按照上述清单，在你的环境中执行所有步骤。然后，向我提交一份**验证报告**。报告需要：
1.  确认每一个“预期效果”的复选框是否都已达成。
2.  如果遇到任何与预期不符的情况，请详细描述**实际现象**、你诊断出的**根本原因**，以及你建议的**修复方案**。

**任务开始。**