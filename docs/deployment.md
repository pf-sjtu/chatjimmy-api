# 部署指南

本文档介绍如何将 ChatJimmy API Server 部署到各种平台。

## 目录

- [Render 部署（推荐）](#render-部署推荐)
- [本地部署](#本地部署)
- [Docker 部署](#docker-部署)
- [其他平台](#其他平台)

---

## Render 部署（推荐）

[Render](https://render.com) 提供免费的 Web 服务托管，非常适合部署此 API。

### 快速部署

#### 方法一：使用 Blueprint（推荐）

1. Fork 本仓库到你的 GitHub 账户
2. 登录 [Render Dashboard](https://dashboard.render.com)
3. 点击 **New +** → **Blueprint**
4. 选择你的 fork 仓库
5. Render 会自动读取 `render.yaml` 配置并创建服务

#### 方法二：手动创建

1. 登录 [Render Dashboard](https://dashboard.render.com)
2. 点击 **New +** → **Web Service**
3. 选择你的仓库
4. 配置以下设置：

| 设置项 | 值 |
|--------|-----|
| Name | chatjimmy-api（或你喜欢的名称） |
| Runtime | Python 3 |
| Build Command | `pip install -e ".[server]"` |
| Start Command | `uvicorn chatjimmy.server:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

5. 添加环境变量（见下方）
6. 点击 **Create Web Service**

### 环境变量配置

在 Render 的 **Environment** 标签页中设置：

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `API_KEY` | ✅ | - | 访问 API 所需的密钥 |
| `CHATJIMMY_BASE_URL` | ❌ | https://chatjimmy.ai | chatjimmy API 地址 |
| `CHATJIMMY_TIMEOUT` | ❌ | 30 | 请求超时时间（秒） |
| `LOG_LEVEL` | ❌ | info | 日志级别 |
| `ALLOWED_ORIGINS` | ❌ | * | CORS 允许的域名 |

#### 生成 API Key

使用以下命令生成安全的随机密钥：

```bash
# macOS / Linux
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 验证部署

部署完成后，访问以下 URL 验证：

```bash
# 健康检查
curl https://your-service-name.onrender.com/health

# 列出模型
curl https://your-service-name.onrender.com/v1/models \
  -H "Authorization: Bearer your-api-key"

# 聊天测试
curl https://your-service-name.onrender.com/v1/chat/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1-8B",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

---

## 本地部署

### 环境要求

- Python 3.10+
- pip 或 uv

### 安装步骤

#### 使用 pip

```bash
# 克隆仓库
git clone https://github.com/pf-sjtu/chatjimmy-api.git
cd chatjimmy-api

# 安装依赖
pip install -e ".[server]"

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置 API_KEY

# 启动服务器
python -m chatjimmy
```

#### 使用 uv（推荐）

```bash
# 克隆仓库
git clone https://github.com/pf-sjtu/chatjimmy-api.git
cd chatjimmy-api

# 安装依赖
uv sync --extra server

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 启动服务器
uv run python -m chatjimmy
```

### 访问服务

启动后，服务默认运行在 http://localhost:8000

- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

---

## Docker 部署

### Dockerfile

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[server]"

# 复制代码
COPY src/ ./src/

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "chatjimmy.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 构建和运行

```bash
# 构建镜像
docker build -t chatjimmy-api .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -e API_KEY=your-secret-key \
  -e LOG_LEVEL=info \
  --name chatjimmy-api \
  chatjimmy-api
```

### Docker Compose

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - API_KEY=${API_KEY}
      - CHATJIMMY_TIMEOUT=30
      - LOG_LEVEL=info
      - ALLOWED_ORIGins=*
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

运行：

```bash
docker-compose up -d
```

---

## 其他平台

### Railway

1. Fork 本仓库
2. 在 [Railway](https://railway.app) 创建新项目
3. 选择 GitHub 仓库
4. 添加环境变量
5. 部署

### Heroku

由于 Heroku 已停止免费套餐，不再推荐。

### AWS / GCP / Azure

可以使用以下方式部署：

- **AWS**: ECS Fargate, Elastic Beanstalk, EC2
- **GCP**: Cloud Run, App Engine, Compute Engine
- **Azure**: Container Instances, App Service

通用步骤：

1. 构建 Docker 镜像
2. 推送到容器仓库（ECR/GCR/ACR）
3. 配置环境变量
4. 部署到容器服务

---

## 生产环境检查清单

### 安全性

- [ ] 设置强 API Key（至少 32 字符随机字符串）
- [ ] 配置 CORS，限制允许的域名（不要设置为 `*`）
- [ ] 启用 HTTPS（Render 自动提供）
- [ ] 定期轮换 API Key

### 性能

- [ ] 根据负载调整 timeout 设置
- [ ] 监控响应时间和错误率
- [ ] 配置适当的日志级别（生产环境建议 `warning` 或 `error`）

### 可靠性

- [ ] 配置健康检查
- [ ] 设置自动重启策略
- [ ] 监控上游 API 可用性

---

## 故障排查

### 启动失败

**检查日志**：

```bash
# Render
curl https://api.render.com/v1/services/{service_id}/logs

# Docker
docker logs chatjimmy-api

# 本地
python -m chatjimmy  # 查看控制台输出
```

**常见问题**：

1. **ImportError**: 确保安装了 `[server]` 额外依赖
2. **API_KEY 未设置**: 检查环境变量配置
3. **端口冲突**: 确保端口未被占用

### 请求失败

**401 Unauthorized**:
- 检查 Authorization header 格式：`Bearer your-api-key`
- 确认 API Key 与环境变量匹配

**502 Bad Gateway**:
- 上游 chatjimmy.ai 服务可能不可用
- 检查网络连接和代理设置

**空响应**:
- 输入可能超过 6K tokens 限制
- 减少输入长度

---

## 监控建议

### 日志监控

在 Render 或其他平台的日志界面中关注：

- 错误率
- 响应时间
- 请求频率

### 健康检查

定期访问 `/health` 端点：

```bash
*/5 * * * * curl -f https://your-api.com/health || echo "ALERT"
```

## 相关文档

- [API 限制说明](./api-limitations.md)
- [使用示例](../README.md)
