# FRPC 客户端配置

这个目录包含了frp客户端的配置文件，用于将本地服务通过frp服务器暴露到公网。

## 配置方式

### 方式1：统一配置（推荐）

使用 `frpc.toml` 文件配置多个代理：

1. **修改配置**
   编辑 `frpc.toml` 文件，修改以下参数：
   - `server_addr`: 您的frp服务器IP地址
   - `server_port`: frp服务器端口（通常是7000）
   - `token`: 认证token（需要与frps服务器配置一致）
   - `remote_port`: 远程端口（确保不与服务器其他服务冲突）

2. **启动服务**
   ```bash
   # 启动所有服务（包括frpc）
   docker-compose up -d
   
   # 或者只启动frpc服务
   docker-compose up -d frpc
   ```

### 方式2：分离配置

如果需要为不同服务使用独立的frpc实例：

1. **使用分离配置**
   ```bash
   # 启动分离的frpc服务
   docker-compose --profile separate-frpc up -d
   ```

2. **查看日志**
   ```bash
   docker-compose logs -f frpc
   ```

## 配置说明

### 代理类型

- **TCP代理**: 适用于需要直接TCP连接的服务
- **HTTP代理**: 适用于Web服务，支持域名访问
- **HTTPS代理**: 适用于需要SSL加密的Web服务

### 端口映射

- 后端服务: 本地5409端口 → 远程15409端口
- 前端服务: 本地8080端口 → 远程18080端口

### 管理界面

frpc提供了Web管理界面，默认访问地址：
- 统一配置: http://localhost:7400
- 后端专用: http://localhost:7401
- 前端专用: http://localhost:7402
- 用户名: huangpeilin
- 密码: asdfQWER1234

### 多端口代理说明

**重要**: 一个frpc服务实例可以代理多个端口，通过在配置文件中添加多个 `[[proxies]]` 段落实现。每个代理段落代表一个端口映射。

示例配置：
```toml
# 后端服务代理
[[proxies]]
name = "sau-backend"
type = "tcp"
local_ip = "127.0.0.1"
local_port = 5409
remote_port = 15409

# 前端服务代理
[[proxies]]
name = "sau-frontend"
type = "tcp"
local_ip = "127.0.0.1"
local_port = 8080
remote_port = 18080
```

**重要提示**：
- 每个代理的 `name` 必须在整个 frp 服务器中唯一
- 如果使用分离配置，确保不同配置文件中的代理名称不重复
- 建议使用项目前缀（如 `sau-`）来避免命名冲突

## 故障排除

1. **连接失败**
   - 检查server_addr和server_port是否正确
   - 确认frp服务器是否正常运行
   - 检查网络连接和防火墙设置

2. **认证失败**
   - 确认token与frps服务器配置一致
   - 检查token是否包含特殊字符需要转义

3. **端口冲突**
   - 修改remote_port避免与服务器其他服务冲突
   - 确保frps服务器配置了对应的端口

4. **代理名称冲突**
   - 错误信息：`proxy [[proxies]] already exists`
   - 解决方案：确保所有代理的 `name` 字段在 frp 服务器中唯一
   - 检查是否有多个 frpc 实例使用相同的代理名称

## 安全建议

1. 使用强密码作为token
2. 定期更换认证token
3. 限制管理界面的访问权限
4. 使用HTTPS代理时配置SSL证书
