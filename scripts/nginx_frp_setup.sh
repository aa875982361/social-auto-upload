#!/bin/bash

# Nginx + FRP 集成配置脚本
# 用于配置nginx反向代理frp穿透的服务

set -e

# 配置变量
NGINX_CONFIG_DIR="/etc/nginx/conf.d"
FRP_PROXY_CONFIG="frp_proxy.conf"
NGINX_LOG_DIR="/var/log/nginx"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_blue() {
    echo -e "${BLUE}[CONFIG]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用root权限运行此脚本"
        exit 1
    fi
}

# 检查nginx是否安装
check_nginx() {
    if ! command -v nginx &> /dev/null; then
        log_error "nginx 未安装，请先安装nginx"
        log_info "安装命令: apt update && apt install -y nginx"
        exit 1
    fi
    log_info "nginx 已安装"
}

# 备份现有配置
backup_config() {
    if [ -f "$NGINX_CONFIG_DIR/$FRP_PROXY_CONFIG" ]; then
        log_info "备份现有配置文件..."
        cp "$NGINX_CONFIG_DIR/$FRP_PROXY_CONFIG" "$NGINX_CONFIG_DIR/$FRP_PROXY_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
    fi
}

# 配置nginx
configure_nginx() {
    log_info "配置 nginx..."
    
    # 读取用户输入
    read -p "请输入域名 (例如: your-domain.com): " DOMAIN
    read -p "请输入frp后端端口 (默认: 8080): " BACKEND_PORT
    BACKEND_PORT=${BACKEND_PORT:-8080}
    
    read -p "是否启用HTTPS? (y/n): " ENABLE_HTTPS
    read -p "是否启用HTTP重定向到HTTPS? (y/n): " ENABLE_REDIRECT
    
    # 创建nginx配置
    cat > "$NGINX_CONFIG_DIR/$FRP_PROXY_CONFIG" << EOF
# FRP 反向代理配置
# 用于nginx反向代理frp穿透的服务

# 上游服务器配置 (frp穿透的本地服务)
upstream frp_backend {
    server 127.0.0.1:$BACKEND_PORT;
    keepalive 32;
}

# 主服务器配置
server {
    listen 80;
    server_name $DOMAIN;
    
    # 日志配置
    access_log $NGINX_LOG_DIR/frp_proxy_access.log;
    error_log $NGINX_LOG_DIR/frp_proxy_error.log;
    
    # 安全头设置
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # 客户端最大请求体大小
    client_max_body_size 100M;
    
    # 超时设置
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    # 代理设置
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header X-Forwarded-Host \$host;
    proxy_set_header X-Forwarded-Port \$server_port;
    
    # 缓冲设置
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
    proxy_busy_buffers_size 8k;
    
    # 主要代理规则
    location / {
        proxy_pass http://frp_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_intercept_errors on;
        error_page 502 503 504 /50x.html;
    }
    
    # 静态文件缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)\$ {
        proxy_pass http://frp_backend;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # API接口特殊处理
    location /api/ {
        proxy_pass http://frp_backend;
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization";
        
        if (\$request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin *;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization";
            add_header Access-Control-Max-Age 1728000;
            add_header Content-Type 'text/plain; charset=utf-8';
            add_header Content-Length 0;
            return 204;
        }
    }
    
    # 文件上传处理
    location /upload/ {
        proxy_pass http://frp_backend;
        client_max_body_size 500M;
        proxy_request_buffering off;
    }
    
    # 健康检查端点
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # 错误页面
    location = /50x.html {
        root /usr/share/nginx/html;
    }
    
    # 禁止访问敏感文件
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    location ~ ~\$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF

    # 如果启用HTTPS，添加HTTPS配置
    if [[ "$ENABLE_HTTPS" == "y" || "$ENABLE_HTTPS" == "Y" ]]; then
        read -p "请输入SSL证书路径: " SSL_CERT
        read -p "请输入SSL私钥路径: " SSL_KEY
        
        cat >> "$NGINX_CONFIG_DIR/$FRP_PROXY_CONFIG" << EOF

# HTTPS配置
server {
    listen 443 ssl http2;
    server_name $DOMAIN;
    
    # SSL证书配置
    ssl_certificate $SSL_CERT;
    ssl_certificate_key $SSL_KEY;
    
    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # 其他配置与HTTP相同
    access_log $NGINX_LOG_DIR/frp_proxy_ssl_access.log;
    error_log $NGINX_LOG_DIR/frp_proxy_ssl_error.log;
    
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    client_max_body_size 100M;
    
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header X-Forwarded-Host \$host;
    proxy_set_header X-Forwarded-Port \$server_port;
    
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
    proxy_busy_buffers_size 8k;
    
    location / {
        proxy_pass http://frp_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_intercept_errors on;
        error_page 502 503 504 /50x.html;
    }
    
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)\$ {
        proxy_pass http://frp_backend;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location /api/ {
        proxy_pass http://frp_backend;
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization";
        
        if (\$request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin *;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization";
            add_header Access-Control-Max-Age 1728000;
            add_header Content-Type 'text/plain; charset=utf-8';
            add_header Content-Length 0;
            return 204;
        }
    }
    
    location /upload/ {
        proxy_pass http://frp_backend;
        client_max_body_size 500M;
        proxy_request_buffering off;
    }
    
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    location = /50x.html {
        root /usr/share/nginx/html;
    }
    
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    location ~ ~\$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF
    fi

    # 如果启用重定向，添加重定向配置
    if [[ "$ENABLE_REDIRECT" == "y" || "$ENABLE_REDIRECT" == "Y" ]]; then
        cat >> "$NGINX_CONFIG_DIR/$FRP_PROXY_CONFIG" << EOF

# HTTP重定向到HTTPS
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}
EOF
    fi

    log_info "nginx 配置完成"
}

# 测试nginx配置
test_nginx_config() {
    log_info "测试 nginx 配置..."
    if nginx -t; then
        log_info "nginx 配置测试通过"
    else
        log_error "nginx 配置测试失败"
        exit 1
    fi
}

# 重启nginx
restart_nginx() {
    log_info "重启 nginx..."
    systemctl restart nginx
    systemctl status nginx --no-pager
    
    if systemctl is-active --quiet nginx; then
        log_info "nginx 重启成功"
    else
        log_error "nginx 重启失败"
        exit 1
    fi
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙..."
    
    # 检查ufw是否安装
    if command -v ufw &> /dev/null; then
        ufw allow 80/tcp comment "nginx http"
        ufw allow 443/tcp comment "nginx https"
        log_info "防火墙规则已添加"
    else
        log_warn "未检测到ufw防火墙，请手动开放端口 80 和 443"
    fi
}

# 显示使用说明
show_usage() {
    log_info "配置完成！使用说明："
    echo
    log_blue "1. 访问地址:"
    echo "   HTTP: http://$DOMAIN"
    if [[ "$ENABLE_HTTPS" == "y" || "$ENABLE_HTTPS" == "Y" ]]; then
        echo "   HTTPS: https://$DOMAIN"
    fi
    echo
    log_blue "2. 健康检查:"
    echo "   http://$DOMAIN/health"
    echo
    log_blue "3. 日志文件:"
    echo "   访问日志: $NGINX_LOG_DIR/frp_proxy_access.log"
    echo "   错误日志: $NGINX_LOG_DIR/frp_proxy_error.log"
    if [[ "$ENABLE_HTTPS" == "y" || "$ENABLE_HTTPS" == "Y" ]]; then
        echo "   HTTPS访问日志: $NGINX_LOG_DIR/frp_proxy_ssl_access.log"
        echo "   HTTPS错误日志: $NGINX_LOG_DIR/frp_proxy_ssl_error.log"
    fi
    echo
    log_blue "4. 服务管理:"
    echo "   重启: systemctl restart nginx"
    echo "   状态: systemctl status nginx"
    echo "   重载配置: nginx -s reload"
    echo
    log_blue "5. 配置文件:"
    echo "   位置: $NGINX_CONFIG_DIR/$FRP_PROXY_CONFIG"
}

# 主函数
main() {
    log_info "开始配置 nginx + frp 反向代理..."
    
    check_root
    check_nginx
    backup_config
    configure_nginx
    test_nginx_config
    restart_nginx
    configure_firewall
    show_usage
    
    log_info "nginx + frp 反向代理配置完成！"
}

# 运行主函数
main "$@"
