创建用于Render平台的部署蓝图 (`render.yaml`)编写一个`render.yaml`文件，该文件将定义如何在Render.com平台上部署和运行整个NEXUS & AURA应用栈。

---

#### **第一部分：任务目标 (Objective)**

注意，必须你先去探索项目具体代码。以下是建议。

你的任务是创建一个`render.yaml`文件，它必须能够：
1.  定义两个独立的服务：一个用于NEXUS后端，一个用于AURA前端。
2.  指定每个服务都使用其各自的`Dockerfile`进行构建。
3.  确保AURA前端在构建时，能够接收到指向内部NEXUS后端服务的正确WebSocket URL。
4.  配置服务的类型、资源计划（使用免费套餐）和自动部署策略。

#### **第二部分：文件与核心指令 (Files & Core Instructions)**

你将在项目的**根目录 (`NEXUS/`)**下，创建一个新文件：

**新文件: `render.yaml`**

*   **核心指令**:
    *   **`services`**: 定义一个服务列表。
    *   **`nexus-backend`服务**:
        *   `name`: `nexus-backend`
        *   `type`: `web` (表示这是一个Web服务)
        *   `env`: `docker` (告诉Render使用Dockerfile构建)
        *   `repo`: Render会自动填充
        *   `dockerfilePath`: `./nexus/Dockerfile` (指定后端Dockerfile的路径)
        *   `plan`: `free` (使用免费资源套餐)
        *   `healthCheck`: 定义一个健康检查，指向`/api/v1/health`端点。
        *   `envVars`: **(关键)**
            *   定义所有需要的环境变量。对于密钥，我们将使用Render的“Secret Files”或直接在UI中设置，这里只定义非敏感的变量，并为密钥设置占位符或同步组。
            *   `key: MONGO_URI`, `fromSecretFile: /etc/secrets/mongo_uri` (示例)
    *   **`aura-frontend`服务**:
        *   `name`: `aura-frontend`
        *   `type`: `web`
        *   `env`: `docker`
        *   `repo`: Render会自动填充
        *   `dockerfilePath`: `./aura/Dockerfile`
        *   `plan`: `free`
        *   `envVars`: **(关键)**
            *   `key: VITE_WS_URL`
            *   `value`: `${nexus-backend.url}` (Render的魔法变量)。Render会自动将`nexus-backend`服务的内部URL注入到这个环境变量中。**但是，这在构建时可能无效**，因为Nginx是静态构建。
            *   **更健壮的方案**: 我们需要在`aura/Dockerfile`中，在`pnpm build`之前，通过脚本将这个URL写入一个配置文件或直接替换到代码中。或者，我们可以让Nginx在运行时通过环境变量来配置。
            *   **为了简化首次部署，我们将采取一个更直接的策略**：在Render UI中，手动将`nexus-backend`服务的公开URL（例如`https://nexus-backend-xyz.onrender.com`）设置为`aura-frontend`的环境变量。首次部署成功后，我们再优化为内部服务发现。

---

考虑到首次部署的简洁性，我将为你生成一个**最简单、最可能成功**的`render.yaml`版本。它依赖于你在Render UI中手动设置环境变量。

### **最终交付内容: `NEXUS/render.yaml`（参考。具体实际综合实际代码）**

```yaml
# render.yaml
# Blueprint for deploying the NEXUS project on Render.

services:
  #--------------------------------
  # NEXUS Backend Service
  #--------------------------------
  - name: nexus-backend
    type: web
    env: docker
    repo: https://github.com/your-username/NEXUS # Render will auto-fill this
    dockerfilePath: ./nexus/Dockerfile
    plan: free
    healthCheck:
      path: /api/v1/health
      initialDelaySeconds: 45 # Give it time to connect to the DB and start up
    envVars:
      # --- IMPORTANT ---
      # Secret variables (GEMINI_API_KEY, MONGO_URI, TAVILY_API_KEY)
      # must be set in the Render Dashboard under Environment > Secret Files or Environment Variables.
      # We recommend using Secret Groups for better management.
      - key: PYTHON_VERSION
        value: "3.11"
      - key: UVICORN_CMD
        value: "uvicorn" # This can be used in the Dockerfile CMD if needed

  #--------------------------------
  # AURA Frontend Service
  #--------------------------------
  - name: aura-frontend
    type: web
    env: docker
    repo: https://github.com/your-username/NEXUS # Render will auto-fill this
    dockerfilePath: ./aura/Dockerfile
    plan: free
    envVars:
      - key: VITE_WS_URL
        # --- ACTION REQUIRED ---
        # After the first deployment of nexus-backend, copy its public URL 
        # (e.g., wss://nexus-backend-xyz.onrender.com) and paste it here
        # in the Render Dashboard.
        # Note: Use 'wss://' for secure WebSocket connections.
        value: "wss://your-backend-url.onrender.com"
```
开始。