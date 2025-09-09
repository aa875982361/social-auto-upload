# Docker 部署指南

本文档介绍如何使用 Docker 部署 Social Auto Upload 应用。

## 目录结构

```
social-auto-upload/
├── Dockerfile.backend          # 后端 Docker 镜像构建文件
├── docker-compose.yml          # Docker Compose 配置文件
├── .dockerignore              # Docker 构建忽略文件
├── env.example                # 环境变量示例文件
├── nginx/
│   └── nginx.conf             # Nginx 配置文件
├── sau_frontend/
│   ├── Dockerfile             # 前端 Docker 镜像构建文件
│   └── nginx.conf             # 前端 Nginx 配置
└── DOCKER_DEPLOYMENT.md       # 本文档
```

## 快速开始

### 1. 环境准备

确保您的系统已安装：
- Docker (版本 20.10+)
- Docker Compose (版本 2.0+)

### 2. 配置环境变量

```bash
# 复制环境变量示例文件
cp env.example .env

# 编辑环境变量（根据需要修改）
nano .env
```

### 3. 创建必要的目录

```bash
# 创建数据存储目录
mkdir -p data/db data/logs data/accounts
mkdir -p videoFile logs media ssl
```

### 4. 启动服务

#### 开发环境（仅前后端）

```bash
# 启动前后端服务
docker-compose up -d backend frontend

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

#### 生产环境（包含 Nginx 反向代理）

```bash
# 启动所有服务（包括 Nginx）
docker-compose --profile production up -d

# 查看服务状态
docker-compose ps
```

### 5. 访问应用

- 前端界面：http://localhost
- 后端API：http://localhost:5409
- 生产环境（HTTPS）：https://localhost

## 详细配置

### 服务说明

#### 后端服务 (backend)
- **端口**: 5409
- **镜像**: 基于 Python 3.11-slim
- **功能**: Flask API 服务，处理文件上传、账号管理等
- **数据卷**: 
  - `./data:/app/data` - 数据库和账号数据
  - `./logs:/app/logs` - 应用日志
  - `./videoFile:/app/videoFile` - 视频文件存储
  - `./media:/app/media` - 媒体文件
  - `./ssl:/app/ssl` - SSL 证书

#### 前端服务 (frontend)
- **端口**: 80
- **镜像**: 基于 Node.js 18 + Nginx
- **功能**: Vue.js 前端应用
- **代理**: 自动代理 API 请求到后端

#### Nginx 服务 (nginx)
- **端口**: 443 (HTTPS)
- **功能**: 反向代理、SSL 终止、负载均衡
- **配置**: 支持大文件上传、SSE 连接

### 环境变量配置

主要环境变量说明：

```bash
# 应用配置
APP_NAME=Social Auto Upload
APP_ENV=production

# 服务端口
BACKEND_PORT=5409
FRONTEND_PORT=80

# 文件路径
VIDEO_FILE_PATH=/app/videoFile
DB_PATH=/app/data/db/database.db

# 小红书服务
XHS_SERVER=http://127.0.0.1:11901

# 安全配置
SECRET_KEY=your-secret-key-here
```

### SSL 证书配置

生产环境需要配置 SSL 证书：

```bash
# 将证书文件放入 ssl 目录
cp your-cert.pem ssl/cert.pem
cp your-key.pem ssl/key.pem

# 设置正确的权限
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem
```

## 常用命令

### 服务管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f [service_name]
```

### 构建和更新

```bash
# 重新构建镜像
docker-compose build

# 强制重新构建
docker-compose build --no-cache

# 更新服务
docker-compose up -d --build
```

### 数据管理

```bash
# 备份数据
docker-compose exec backend tar -czf /tmp/backup.tar.gz /app/data

# 恢复数据
docker-compose exec backend tar -xzf /tmp/backup.tar.gz -C /app/

# 清理未使用的镜像和容器
docker system prune -a
```

## 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tulpn | grep :5409
   
   # 修改 docker-compose.yml 中的端口映射
   ports:
     - "5408:5409"  # 改为其他端口
   ```

2. **权限问题**
   ```bash
   # 设置目录权限
   chmod -R 755 data/ logs/ videoFile/
   ```

3. **数据库初始化**
   ```bash
   # 进入后端容器
   docker-compose exec backend bash
   
   # 运行数据库初始化脚本
   python db/createTable.py
   ```

4. **前端构建失败**
   ```bash
   # 清理 node_modules 并重新构建
   docker-compose build --no-cache frontend
   ```

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs frontend

# 实时查看日志
docker-compose logs -f backend
```

### 健康检查

```bash
# 检查服务健康状态
docker-compose ps

# 手动健康检查
curl -f http://localhost:5409/  # 后端
curl -f http://localhost/        # 前端
```

## 性能优化

### 资源限制

在 `docker-compose.yml` 中添加资源限制：

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

### 缓存优化

```yaml
services:
  frontend:
    volumes:
      - node_modules_cache:/app/node_modules
      
volumes:
  node_modules_cache:
```

## 安全建议

1. **更改默认密码和密钥**
2. **使用 HTTPS 证书**
3. **限制网络访问**
4. **定期更新镜像**
5. **监控日志文件**

## 备份和恢复

### 数据备份

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"

mkdir -p $BACKUP_DIR

# 备份数据目录
tar -czf $BACKUP_DIR/data_$DATE.tar.gz data/

# 备份视频文件
tar -czf $BACKUP_DIR/videoFile_$DATE.tar.gz videoFile/

# 备份配置文件
cp docker-compose.yml $BACKUP_DIR/
cp .env $BACKUP_DIR/
```

### 数据恢复

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# 停止服务
docker-compose down

# 恢复数据
tar -xzf $BACKUP_FILE

# 启动服务
docker-compose up -d
```

## 监控和维护

### 日志轮转

```bash
# 配置 logrotate
cat > /etc/logrotate.d/docker-sau << EOF
/var/lib/docker/containers/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
EOF
```

### 自动更新

```bash
#!/bin/bash
# update.sh

# 拉取最新镜像
docker-compose pull

# 重新构建和启动
docker-compose up -d --build

# 清理旧镜像
docker image prune -f
```

## 支持

如果遇到问题，请：

1. 查看本文档的故障排除部分
2. 检查 Docker 和 Docker Compose 版本
3. 查看服务日志
4. 确认环境变量配置正确
5. 检查网络和端口配置

---

**注意**: 请根据实际环境调整配置参数，特别是端口、路径和安全设置。
