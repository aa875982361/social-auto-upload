#!/bin/bash

# wait-for-mysql.sh - 等待MySQL服务就绪的脚本
# 用法: ./wait-for-mysql.sh host port [timeout]

set -e

host="$1"
port="$2"
timeout="${3:-30}"

cmd="$@"

if [ -z "$host" ] || [ -z "$port" ]; then
    echo "用法: $0 host port [timeout] [-- command args]"
    echo "例如: $0 mysql 3306 30 -- python sau_backend.py"
    exit 1
fi

echo "⏳ 等待MySQL服务 $host:$port 就绪..."

# 等待端口可用
for i in $(seq $timeout); do
    if nc -z "$host" "$port" > /dev/null 2>&1; then
        echo "✅ MySQL端口 $host:$port 已可用"
        break
    fi
    echo "⏳ 等待MySQL ($i/$timeout)..."
    sleep 1
done

# 检查端口是否成功连接
if ! nc -z "$host" "$port" > /dev/null 2>&1; then
    echo "❌ 超时：MySQL服务 $host:$port 未在${timeout}秒内就绪"
    exit 1
fi

# 等待MySQL服务完全初始化（检查数据库连接）
echo "⏳ 检查MySQL数据库连接..."
for i in $(seq 30); do
    if mysql -h"$host" -P"$port" -u"${DB_USER:-sau_user}" -p"${DB_PASSWORD:-sau_password}" -e "SELECT 1" > /dev/null 2>&1; then
        echo "✅ MySQL数据库连接成功"
        break
    fi
    echo "⏳ 等待MySQL数据库初始化完成 ($i/30)..."
    sleep 2
done

# 检查数据库是否可用
if ! mysql -h"$host" -P"$port" -u"${DB_USER:-sau_user}" -p"${DB_PASSWORD:-sau_password}" -e "SELECT 1" > /dev/null 2>&1; then
    echo "❌ MySQL数据库连接失败，请检查配置"
    exit 1
fi

# 检查数据库和表是否存在
echo "⏳ 检查数据库表结构..."
if mysql -h"$host" -P"$port" -u"${DB_USER:-sau_user}" -p"${DB_PASSWORD:-sau_password}" "${DB_NAME:-social_auto_upload}" -e "SHOW TABLES" > /dev/null 2>&1; then
    echo "✅ 数据库表结构检查完成"
else
    echo "⚠️  数据库表可能还未完全初始化，但连接正常"
fi

echo "🚀 MySQL服务已完全就绪，启动应用..."

# 如果有额外的命令参数，执行它们
if [ $# -gt 3 ]; then
    shift 3
    exec "$@"
fi
