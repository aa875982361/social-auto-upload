#!/bin/bash

# start_app.sh - 应用启动脚本
# 整合数据库等待和应用启动逻辑

set -e

echo "🚀 开始启动 Social Auto Upload 应用..."

# 设置环境变量默认值
DB_HOST=${DB_HOST:-mysql}
DB_PORT=${DB_PORT:-3306}
DB_USER=${DB_USER:-sau_user}
DB_PASSWORD=${DB_PASSWORD:-sau_password}
DB_NAME=${DB_NAME:-social_auto_upload}

# 导出环境变量供Python脚本使用
export DB_HOST DB_PORT DB_USER DB_PASSWORD DB_NAME

echo "📋 配置信息:"
echo "  - 数据库主机: $DB_HOST:$DB_PORT"
echo "  - 数据库名称: $DB_NAME"
echo "  - 数据库用户: $DB_USER"

# 1. 等待MySQL端口可用
echo ""
echo "⏳ 第1步: 等待MySQL端口可用..."
timeout=60
for i in $(seq $timeout); do
    if nc -z "$DB_HOST" "$DB_PORT" > /dev/null 2>&1; then
        echo "✅ MySQL端口 $DB_HOST:$DB_PORT 已可用"
        break
    fi
    echo "⏳ 等待MySQL端口 ($i/$timeout)..."
    sleep 1
done

if ! nc -z "$DB_HOST" "$DB_PORT" > /dev/null 2>&1; then
    echo "❌ 超时：MySQL端口 $DB_HOST:$DB_PORT 未在${timeout}秒内就绪"
    exit 1
fi

# 2. 检查MySQL服务和数据库连接
echo ""
echo "⏳ 第2步: 检查数据库连接..."
python /app/scripts/check_db_connection.py

if [ $? -ne 0 ]; then
    echo "❌ 数据库连接检查失败"
    exit 1
fi

# 3. 启动应用
echo ""
echo "🚀 第3步: 启动应用服务..."
echo "📝 日志将输出到标准输出"

# 切换到应用目录
cd /app

# 启动应用
exec python sau_backend.py
