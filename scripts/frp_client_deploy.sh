#!/bin/bash

# FRP客户端Docker部署脚本
# 用于在本地部署FRP客户端，连接到FRP服务端

set -e

# 配置变量
FRP_VERSION="0.52.3"
FRP_SERVER_IP="your-server-ip"    # 请修改为你的服务器IP
FRP_SERVER_PORT="7000"
FRP_TOKEN="your_frp_token_here"   # 请修改为你的token，与服务端保持一致
LOCAL_HTTP_PORT="8080"            # 本地HTTP服务端口
LOCAL_HTTPS_PORT="8443"           # 本地HTTPS服务端口
SUBDOMAIN="local"                 # 子域名前缀

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始部署FRP客户端...${NC}"

# 创建必要的目录
mkdir -p frp-client/{conf,logs}

# 创建FRP客户端配置文件
cat > frp-client/conf/frpc.ini << EOF
[common]
# 服务端地址和端口
server_addr = ${FRP_SERVER_IP}
server_port = ${FRP_SERVER_PORT}

# 认证token
token = ${FRP_TOKEN}

# 日志配置
log_file = /var/log/frpc.log
log_level = info
log_max_days = 3

# 管理后台配置
admin_addr = 127.0.0.1
admin_port = 7400
admin_user = admin
admin_pwd = admin123

# HTTP代理配置
[http_proxy]
type = http
local_ip = 127.0.0.1
local_port = ${LOCAL_HTTP_PORT}
subdomain = ${SUBDOMAIN}
use_encryption = false
use_compression = true

# HTTPS代理配置
[https_proxy]
type = https
local_ip = 127.0.0.1
local_port = ${LOCAL_HTTPS_PORT}
subdomain = ${SUBDOMAIN}https
use_encryption = false
use_compression = true

# TCP代理配置（可选，用于SSH等）
[ssh]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 6000
use_encryption = false
use_compression = true

# 自定义域名配置（可选）
[custom_domain]
type = http
local_ip = 127.0.0.1
local_port = ${LOCAL_HTTP_PORT}
custom_domains = your-custom-domain.com
use_encryption = false
use_compression = true
EOF

# 创建Docker Compose文件
cat > frp-client/docker-compose.yml << EOF
version: '3.8'

services:
  frpc:
    image: snowdreamtech/frpc:${FRP_VERSION}
    container_name: frp-client
    restart: unless-stopped
    volumes:
      - ./conf/frpc.ini:/etc/frp/frpc.ini:ro
      - ./logs:/var/log
    networks:
      - frp-network
    depends_on:
      - local-service
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:7400"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 本地服务示例（可以是你的应用）
  local-service:
    image: nginx:alpine
    container_name: local-nginx
    restart: unless-stopped
    ports:
      - "${LOCAL_HTTP_PORT}:80"
      - "${LOCAL_HTTPS_PORT}:443"
    volumes:
      - ./html:/usr/share/nginx/html:ro
    networks:
      - frp-network

networks:
  frp-network:
    driver: bridge
EOF

# 创建示例HTML页面
mkdir -p frp-client/html
cat > frp-client/html/index.html << EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>FRP客户端测试页面</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            text-align: center; 
            margin-top: 100px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container {
            background: rgba(255,255,255,0.1);
            padding: 40px;
            border-radius: 10px;
            display: inline-block;
            backdrop-filter: blur(10px);
        }
        h1 { color: #fff; margin-bottom: 20px; }
        p { font-size: 18px; margin: 10px 0; }
        .status { color: #4CAF50; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 FRP网络穿透测试</h1>
        <p class="status">✅ 连接成功！</p>
        <p>当前时间: <span id="time"></span></p>
        <p>访问地址: ${SUBDOMAIN}.your-domain.com</p>
        <p>本地端口: ${LOCAL_HTTP_PORT}</p>
    </div>
    
    <script>
        function updateTime() {
            document.getElementById('time').textContent = new Date().toLocaleString();
        }
        updateTime();
        setInterval(updateTime, 1000);
    </script>
</body>
</html>
EOF

# 创建启动脚本
cat > frp-client/start.sh << 'EOF'
#!/bin/bash
echo "启动FRP客户端..."
docker-compose up -d
echo "FRP客户端已启动"
echo "管理后台: http://localhost:7400"
echo "用户名: admin, 密码: admin123"
echo "测试页面: http://localhost:8080"
EOF

# 创建停止脚本
cat > frp-client/stop.sh << 'EOF'
#!/bin/bash
echo "停止FRP客户端..."
docker-compose down
echo "FRP客户端已停止"
EOF

# 创建重启脚本
cat > frp-client/restart.sh << 'EOF'
#!/bin/bash
echo "重启FRP客户端..."
docker-compose restart
echo "FRP客户端已重启"
EOF

# 创建日志查看脚本
cat > frp-client/logs.sh << 'EOF'
#!/bin/bash
echo "查看FRP客户端日志..."
docker-compose logs -f frpc
EOF

# 创建状态检查脚本
cat > frp-client/status.sh << 'EOF'
#!/bin/bash
echo "FRP客户端状态："
docker-compose ps
echo ""
echo "连接状态："
curl -s http://localhost:7400/api/proxy/tcp || echo "管理后台未响应"
EOF

# 设置脚本执行权限
chmod +x frp-client/*.sh

echo -e "${GREEN}FRP客户端配置完成！${NC}"
echo -e "${YELLOW}请修改以下配置：${NC}"
echo "1. 编辑 frp-client/conf/frpc.ini 中的服务器IP和token"
echo "2. 确保本地防火墙允许端口: ${LOCAL_HTTP_PORT}, ${LOCAL_HTTPS_PORT}"
echo "3. 如果使用自定义域名，请修改配置文件中的域名设置"
echo ""
echo -e "${GREEN}使用方法：${NC}"
echo "cd frp-client"
echo "./start.sh    # 启动服务"
echo "./stop.sh     # 停止服务"
echo "./restart.sh  # 重启服务"
echo "./logs.sh     # 查看日志"
echo "./status.sh   # 查看状态"
echo ""
echo -e "${GREEN}访问地址：${NC}"
echo "本地测试: http://localhost:${LOCAL_HTTP_PORT}"
echo "远程访问: http://${SUBDOMAIN}.your-domain.com"
echo "管理后台: http://localhost:7400"
echo ""
echo -e "${YELLOW}注意事项：${NC}"
echo "1. 确保FRP服务端已启动并配置正确"
echo "2. 检查网络连接和防火墙设置"
echo "3. 如果连接失败，请查看日志文件排查问题"
