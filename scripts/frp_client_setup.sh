#!/bin/bash

# FRP 客户端配置脚本
# 用于在本地配置 frp 客户端，连接到服务端实现内网穿透

set -e

# 配置变量
FRP_VERSION="0.52.3"
FRP_ARCH="linux_amd64"
FRP_DIR="./frp_client"
FRP_CONFIG_FILE="$FRP_DIR/frpc.ini"

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

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        FRP_ARCH="linux_amd64"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        FRP_ARCH="darwin_amd64"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        FRP_ARCH="windows_amd64"
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
    log_info "检测到操作系统架构: $FRP_ARCH"
}

# 下载frp客户端
download_frp() {
    log_info "下载 frp 客户端 v$FRP_VERSION..."
    
    # 创建目录
    mkdir -p "$FRP_DIR"
    
    # 下载frp
    cd "$FRP_DIR"
    
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows
        wget "https://github.com/fatedier/frp/releases/download/v$FRP_VERSION/frp_${FRP_VERSION}_${FRP_ARCH}.zip"
        unzip "frp_${FRP_VERSION}_${FRP_ARCH}.zip"
        cd "frp_${FRP_VERSION}_${FRP_ARCH}"
        cp frpc.exe ../
        cp frpc.ini ../
    else
        # Linux/macOS
        wget "https://github.com/fatedier/frp/releases/download/v$FRP_VERSION/frp_${FRP_VERSION}_${FRP_ARCH}.tar.gz"
        tar -xzf "frp_${FRP_VERSION}_${FRP_ARCH}.tar.gz"
        cd "frp_${FRP_VERSION}_${FRP_ARCH}"
        cp frpc ../
        cp frpc.ini ../
    fi
    
    cd ../..
    log_info "frp 客户端下载完成"
}

# 配置frp客户端
configure_frpc() {
    log_info "配置 frp 客户端..."
    
    # 读取用户输入
    read -p "请输入服务端IP地址: " SERVER_IP
    read -p "请输入服务端端口 (默认: 7000): " SERVER_PORT
    SERVER_PORT=${SERVER_PORT:-7000}
    
    read -s -p "请输入认证token: " AUTH_TOKEN
    echo
    
    read -p "请输入客户端名称 (默认: social-auto-upload): " CLIENT_NAME
    CLIENT_NAME=${CLIENT_NAME:-social-auto-upload}
    
    # 配置本地服务
    log_blue "配置本地服务映射..."
    
    read -p "请输入本地服务端口 (默认: 8080): " LOCAL_PORT
    LOCAL_PORT=${LOCAL_PORT:-8080}
    
    read -p "请输入远程访问端口 (默认: 8080): " REMOTE_PORT
    REMOTE_PORT=${REMOTE_PORT:-8080}
    
    read -p "请输入自定义域名 (可选，用于nginx反向代理): " CUSTOM_DOMAIN
    
    # 创建配置文件
    cat > "$FRP_CONFIG_FILE" << EOF
[common]
# 服务端地址
server_addr = $SERVER_IP
server_port = $SERVER_PORT

# 认证token
token = $AUTH_TOKEN

# 客户端名称
user = $CLIENT_NAME

# 日志配置
log_file = $FRP_DIR/frpc.log
log_level = info
log_max_days = 3

# 管理面板
admin_addr = 127.0.0.1
admin_port = 7400
admin_user = admin
admin_pwd = admin123

# 本地服务映射
[web]
type = tcp
local_ip = 127.0.0.1
local_port = $LOCAL_PORT
remote_port = $REMOTE_PORT
EOF

    # 如果设置了自定义域名，添加HTTP代理配置
    if [ ! -z "$CUSTOM_DOMAIN" ]; then
        cat >> "$FRP_CONFIG_FILE" << EOF

# HTTP代理配置 (用于nginx反向代理)
[http_proxy]
type = http
local_ip = 127.0.0.1
local_port = $LOCAL_PORT
custom_domains = $CUSTOM_DOMAIN
EOF
    fi

    log_info "frp 客户端配置完成"
}

# 创建启动脚本
create_start_script() {
    log_info "创建启动脚本..."
    
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows批处理脚本
        cat > "$FRP_DIR/start_frpc.bat" << EOF
@echo off
echo 启动 FRP 客户端...
cd /d "%~dp0"
frpc.exe -c frpc.ini
pause
EOF
        chmod +x "$FRP_DIR/start_frpc.bat"
    else
        # Linux/macOS shell脚本
        cat > "$FRP_DIR/start_frpc.sh" << EOF
#!/bin/bash
echo "启动 FRP 客户端..."
cd "\$(dirname "\$0")"
./frpc -c frpc.ini
EOF
        chmod +x "$FRP_DIR/start_frpc.sh"
    fi
}

# 创建停止脚本
create_stop_script() {
    log_info "创建停止脚本..."
    
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows批处理脚本
        cat > "$FRP_DIR/stop_frpc.bat" << EOF
@echo off
echo 停止 FRP 客户端...
taskkill /f /im frpc.exe
echo FRP 客户端已停止
pause
EOF
        chmod +x "$FRP_DIR/stop_frpc.bat"
    else
        # Linux/macOS shell脚本
        cat > "$FRP_DIR/stop_frpc.sh" << EOF
#!/bin/bash
echo "停止 FRP 客户端..."
pkill -f "frpc -c frpc.ini"
echo "FRP 客户端已停止"
EOF
        chmod +x "$FRP_DIR/stop_frpc.sh"
    fi
}

# 创建systemd服务 (仅Linux)
create_systemd_service() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_info "创建 systemd 服务..."
        
        read -p "是否创建systemd服务以便开机自启? (y/n): " CREATE_SERVICE
        if [[ "$CREATE_SERVICE" == "y" || "$CREATE_SERVICE" == "Y" ]]; then
            SERVICE_FILE="/etc/systemd/system/frpc.service"
            ABSOLUTE_FRP_DIR="$(realpath $FRP_DIR)"
            
            sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Frp Client Service
After=network.target

[Service]
Type=simple
User=$USER
Restart=on-failure
RestartSec=5s
WorkingDirectory=$ABSOLUTE_FRP_DIR
ExecStart=$ABSOLUTE_FRP_DIR/frpc -c frpc.ini
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5s

[Install]
WantedBy=multi-user.target
EOF

            sudo systemctl daemon-reload
            sudo systemctl enable frpc
            
            log_info "systemd 服务创建完成"
            log_info "服务管理命令:"
            log_info "  启动: sudo systemctl start frpc"
            log_info "  停止: sudo systemctl stop frpc"
            log_info "  状态: sudo systemctl status frpc"
        fi
    fi
}

# 显示使用说明
show_usage() {
    log_info "配置完成！使用说明："
    echo
    log_blue "1. 启动客户端:"
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "   双击运行: $FRP_DIR/start_frpc.bat"
        echo "   或命令行: cd $FRP_DIR && frpc.exe -c frpc.ini"
    else
        echo "   运行脚本: $FRP_DIR/start_frpc.sh"
        echo "   或命令行: cd $FRP_DIR && ./frpc -c frpc.ini"
    fi
    echo
    log_blue "2. 停止客户端:"
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "   双击运行: $FRP_DIR/stop_frpc.bat"
    else
        echo "   运行脚本: $FRP_DIR/stop_frpc.sh"
    fi
    echo
    log_blue "3. 访问地址:"
    echo "   本地服务: http://127.0.0.1:$LOCAL_PORT"
    echo "   远程访问: http://$SERVER_IP:$REMOTE_PORT"
    if [ ! -z "$CUSTOM_DOMAIN" ]; then
        echo "   域名访问: http://$CUSTOM_DOMAIN"
    fi
    echo
    log_blue "4. 管理面板:"
    echo "   地址: http://127.0.0.1:7400"
    echo "   用户名: admin"
    echo "   密码: admin123"
    echo
    log_blue "5. 配置文件:"
    echo "   位置: $FRP_CONFIG_FILE"
    echo "   日志: $FRP_DIR/frpc.log"
}

# 主函数
main() {
    log_info "开始配置 frp 客户端..."
    
    detect_os
    download_frp
    configure_frpc
    create_start_script
    create_stop_script
    create_systemd_service
    show_usage
    
    log_info "frp 客户端配置完成！"
}

# 运行主函数
main "$@"
