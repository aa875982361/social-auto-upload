# FRP网络穿透部署指南

本指南将帮助您使用Docker部署FRP网络穿透服务，实现通过服务器访问本地服务。

## 架构说明

```
本地服务 ←→ FRP客户端 ←→ 互联网 ←→ FRP服务端 ←→ Nginx ←→ 用户
```

## 部署步骤

### 1. 服务器端部署（FRP服务端）

#### 1.1 运行部署脚本
```bash
# 给脚本执行权限
chmod +x scripts/frp_server_deploy.sh

# 运行部署脚本
./scripts/frp_server_deploy.sh
```

#### 1.2 配置服务端
编辑 `frp-server/conf/frps.ini` 文件：
```ini
[common]
bind_port = 7000
vhost_http_port = 8080
vhost_https_port = 8443
token = your_secure_token_here  # 修改为安全的token
dashboard_port = 7500
dashboard_user = admin
dashboard_pwd = your_admin_password  # 修改为安全的密码
subdomain_host = your-domain.com     # 修改为你的域名
```

#### 1.3 启动服务端
```bash
cd frp-server
./start.sh
```

#### 1.4 配置防火墙
确保服务器防火墙开放以下端口：
- `7000` - FRP服务端端口
- `8080` - HTTP代理端口
- `8443` - HTTPS代理端口
- `7500` - 管理后台端口

### 2. 本地部署（FRP客户端）

#### 2.1 运行部署脚本
```bash
# 给脚本执行权限
chmod +x scripts/frp_client_deploy.sh

# 运行部署脚本
./scripts/frp_client_deploy.sh
```

#### 2.2 配置客户端
编辑 `frp-client/conf/frpc.ini` 文件：
```ini
[common]
server_addr = your-server-ip        # 修改为你的服务器IP
server_port = 7000
token = your_secure_token_here      # 与服务端保持一致
```

#### 2.3 启动客户端
```bash
cd frp-client
./start.sh
```

### 3. 集成到现有项目

#### 3.1 使用集成配置
```bash
# 设置环境变量
export FRP_SERVER_ADDR=your-server-ip
export FRP_SERVER_PORT=7000
export FRP_TOKEN=your_secure_token_here

# 启动带FRP的完整服务
docker-compose -f docker-compose.yml -f docker-compose.frp.yml --profile frp up -d
```

#### 3.2 配置Nginx反向代理
将 `nginx/frp_proxy.conf` 配置添加到你的Nginx配置中：

```bash
# 在nginx.conf的http块中添加
include /path/to/nginx/frp_proxy.conf;
```

## 访问地址

### 服务端管理后台
- 地址：`http://your-server-ip:7500`
- 用户名：admin
- 密码：你设置的密码

### 客户端管理后台
- 地址：`http://localhost:7400`
- 用户名：admin
- 密码：admin123

### 穿透后的服务访问
- 前端：`http://app.your-domain.com`
- 后端API：`http://api.your-domain.com`
- 自定义域名：`http://your-custom-domain.com`

## 常用命令

### 服务端管理
```bash
cd frp-server
./start.sh      # 启动服务
./stop.sh       # 停止服务
./restart.sh    # 重启服务
./logs.sh       # 查看日志
```

### 客户端管理
```bash
cd frp-client
./start.sh      # 启动服务
./stop.sh       # 停止服务
./restart.sh    # 重启服务
./logs.sh       # 查看日志
./status.sh     # 查看状态
```

### Docker Compose管理
```bash
# 启动完整服务（包含FRP）
docker-compose -f docker-compose.yml -f docker-compose.frp.yml --profile frp up -d

# 停止服务
docker-compose -f docker-compose.yml -f docker-compose.frp.yml down

# 查看日志
docker-compose -f docker-compose.yml -f docker-compose.frp.yml logs -f
```

## 故障排除

### 1. 连接失败
- 检查服务器IP和端口是否正确
- 确认防火墙设置
- 验证token是否一致
- 查看客户端和服务端日志

### 2. 域名无法访问
- 确认域名解析到服务器IP
- 检查Nginx配置
- 验证FRP子域名配置

### 3. 服务不稳定
- 检查网络连接
- 查看系统资源使用情况
- 调整FRP配置参数

## 安全建议

1. **使用强密码**：为管理后台设置强密码
2. **定期更新token**：定期更换FRP认证token
3. **限制访问**：使用防火墙限制管理端口访问
4. **启用HTTPS**：在生产环境中启用SSL/TLS
5. **监控日志**：定期检查访问日志和错误日志

## 性能优化

1. **启用压缩**：在FRP配置中启用压缩
2. **调整缓冲区**：根据网络情况调整缓冲区大小
3. **负载均衡**：使用多个FRP客户端实例
4. **CDN加速**：结合CDN提升访问速度

## 注意事项

1. 确保服务器有足够的带宽和资源
2. 定期备份配置文件
3. 监控服务运行状态
4. 遵守相关法律法规，合理使用网络穿透服务