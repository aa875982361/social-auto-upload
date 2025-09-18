#!/bin/bash

# FRP服务端Docker部署脚本
# 用于在服务器上部署FRP服务端，提供网络穿透服务

set -e

# 配置变量
FRP_VERSION="0.52.3"
FRP_SERVER_PORT="7000"
FRP_HTTP_PORT="8080"
FRP_HTTPS_PORT="8443"
FRP_DASHBOARD_PORT="7500"
FRP_TOKEN="your_frp_token_here"  # 请修改为你的token
FRP_DOMAIN="your-domain.com"     # 请修改为你的域名

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始部署FRP服务端...${NC}"

# 创建必要的目录
mkdir -p frp-server/{conf,logs}

# 创建FRP服务端配置文件
cat > frp-server/conf/frps.ini << EOF
[common]
# 服务端监听端口
bind_port = ${FRP_SERVER_PORT}

# HTTP和HTTPS代理端口
vhost_http_port = ${FRP_HTTP_PORT}
vhost_https_port = ${FRP_HTTPS_PORT}

# 认证token
token = ${FRP_TOKEN}

# 管理后台配置
dashboard_port = ${FRP_DASHBOARD_PORT}
dashboard_user = admin
dashboard_pwd = admin123

# 日志配置
log_file = /var/log/frps.log
log_level = info
log_max_days = 3

# 其他配置
max_pool_count = 5
max_ports_per_client = 0
tcp_mux = true

# 子域名配置
subdomain_host = ${FRP_DOMAIN}

# 自定义404页面
custom_404_page = /etc/frp/404.html
EOF

# 创建404页面
cat > frp-server/conf/404.html << EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>404 - 页面未找到</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 100px; }
        h1 { color: #666; }
    </style>
</head>
<body>
    <h1>404 - 页面未找到</h1>
    <p>您访问的页面不存在</p>
</body>
</html>
EOF

# 创建Docker Compose文件
cat > frp-server/docker-compose.yml << EOF
version: '3.8'

services:
  frps:
    image: snowdreamtech/frps:${FRP_VERSION}
    container_name: frp-server
    restart: unless-stopped
    ports:
      - "${FRP_SERVER_PORT}:${FRP_SERVER_PORT}"
      - "${FRP_HTTP_PORT}:${FRP_HTTP_PORT}"
      - "${FRP_HTTPS_PORT}:${FRP_HTTPS_PORT}"
      - "${FRP_DASHBOARD_PORT}:${FRP_DASHBOARD_PORT}"
    volumes:
      - ./conf/frps.ini:/etc/frp/frps.ini:ro
      - ./conf/404.html:/etc/frp/404.html:ro
      - ./logs:/var/log
    networks:
      - frp-network
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:${FRP_DASHBOARD_PORT}"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  frp-network:
    driver: bridge
EOF

# 创建启动脚本
cat > frp-server/start.sh << 'EOF'
#!/bin/bash
echo "启动FRP服务端..."
docker-compose up -d
echo "FRP服务端已启动"
echo "管理后台: http://your-server-ip:7500"
echo "用户名: admin, 密码: admin123"
EOF

# 创建停止脚本
cat > frp-server/stop.sh << 'EOF'
#!/bin/bash
echo "停止FRP服务端..."
docker-compose down
echo "FRP服务端已停止"
EOF

# 创建重启脚本
cat > frp-server/restart.sh << 'EOF'
#!/bin/bash
echo "重启FRP服务端..."
docker-compose restart
echo "FRP服务端已重启"
EOF

# 创建日志查看脚本
cat > frp-server/logs.sh << 'EOF'
#!/bin/bash
echo "查看FRP服务端日志..."
docker-compose logs -f frps
EOF

# 设置脚本执行权限
chmod +x frp-server/*.sh

echo -e "${GREEN}FRP服务端配置完成！${NC}"
echo -e "${YELLOW}请修改以下配置：${NC}"
echo "1. 编辑 frp-server/conf/frps.ini 中的 token 和域名"
echo "2. 确保服务器防火墙开放端口: ${FRP_SERVER_PORT}, ${FRP_HTTP_PORT}, ${FRP_HTTPS_PORT}, ${FRP_DASHBOARD_PORT}"
echo ""
echo -e "${GREEN}使用方法：${NC}"
echo "cd frp-server"
echo "./start.sh    # 启动服务"
echo "./stop.sh     # 停止服务"
echo "./restart.sh  # 重启服务"
echo "./logs.sh     # 查看日志"
echo ""
echo -e "${GREEN}管理后台访问地址：${NC}"
echo "http://your-server-ip:${FRP_DASHBOARD_PORT}"
echo "用户名: admin, 密码: admin123"