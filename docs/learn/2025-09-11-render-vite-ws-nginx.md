## Render + Vite + WebSocket + Nginx 部署故障复盘（2025-09-11）

### 背景

前后端部署到 Render 后，构建正常，但前端始终尝试连接 `localhost` WebSocket，生产环境 WebSocket 连接失败。

### 现象

- 控制台配置打印：`env: production`，但 `wsUrl`/`apiUrl` 回退到了开发默认（或指向前端自身相对路径）。
- WebSocket 连接报错：`wss://<frontend>/api/v1/ws/<session>` 握手失败。

### 根因

1. Vite 环境变量注入规则：仅 `VITE_*` 前缀会被暴露到前端运行时代码，使用 `AURA_*`/`NEXUS_*` 无效，导致回退到默认配置。
2. 生产直连后端域名存在代理细节问题：HTTPS/SNI/Host 头处理不当导致 WS 升级失败。

### 关键改动

1) 前端配置（Vite + 相对路径回退）

- 使用 `import.meta.env.PROD` 判断生产环境；只读取 `VITE_AURA_WS_URL`、`VITE_AURA_API_URL`；生产未设置时回退到相对路径：

```ts
// aura/src/config/nexus.ts （节选）
const env = import.meta.env.PROD ? 'production' : 'development';
let wsUrl = import.meta.env.VITE_AURA_WS_URL as string | undefined;
let apiUrl = import.meta.env.VITE_AURA_API_URL as string | undefined;
if (env === 'production' && !wsUrl) wsUrl = '/api/v1/ws';
if (env === 'production' && !apiUrl) apiUrl = '/api/v1';
```

2) 前端容器内 Nginx 反向代理（支持 WS 升级 + SNI）

```nginx
# aura/nginx.conf （节选）
location ^~ /api/v1/ws/ {
    proxy_pass ${BACKEND_ORIGIN};
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $proxy_host;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400;
    proxy_ssl_server_name on;
}

location /api/ {
    proxy_pass ${BACKEND_ORIGIN};
    proxy_set_header Host $proxy_host;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_ssl_server_name on;
}
```

3) 运行时注入后端地址（避免构建期绑定）

- Dockerfile 使用 `envsubst` 在容器启动时渲染 Nginx 模板：

```dockerfile
# aura/Dockerfile （节选）
ENV BACKEND_ORIGIN=""
CMD sh -c "envsubst '\$BACKEND_ORIGIN' < /etc/nginx/conf.d/nginx.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"
```

- Render 配置：`BACKEND_ORIGIN=https://<后端域名>`

### 验证结果

- 控制台显示：`env: 'production'`，`wsUrl: '/api/v1/ws'`，`apiUrl: '/api/v1'`
- WebSocket 握手地址：`wss://<frontend>/api/v1/ws/<session>`，状态 101，连接成功
- REST `/api/v1/health` 200

### 教训与最佳实践

- 前端变量：仅 `VITE_*` 会被注入，构建期和运行期需区分，建议运行期用服务层渲染（如 envsubst）。
- 生产连通性：优先使用相对路径 + 反向代理，减少协议与跨域复杂度。
- WebSocket 代理：务必设置 `Upgrade/Connection`、`proxy_http_version 1.1`、`proxy_ssl_server_name on` 与正确 `Host` 头。

### 后续可优化

- 增加 Nginx 更细粒度超时与熔断策略、错误日志采集
- Render 内网域名互通可进一步降低延迟与外网依赖
- 引入运行时动态配置端点（/config.json）以摆脱 rebuild


