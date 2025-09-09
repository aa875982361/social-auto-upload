#!/bin/bash

# Social Auto Upload Docker 停止脚本

set -e

echo "🛑 停止 Social Auto Upload 服务..."

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装"
    exit 1
fi

# 停止所有服务
echo "⏹️  停止所有服务..."
docker-compose down

# 停止开发环境服务（如果存在）
if [ -f docker-compose.dev.yml ]; then
    echo "⏹️  停止开发环境服务..."
    docker-compose -f docker-compose.dev.yml down
fi

# 清理未使用的容器和网络
echo "🧹 清理未使用的容器和网络..."
docker-compose down --remove-orphans

echo "✅ 所有服务已停止！"

# 询问是否清理数据
read -p "是否清理所有数据？这将删除所有上传的文件和数据库 (y/N): " cleanup

if [[ $cleanup =~ ^[Yy]$ ]]; then
    echo "🗑️  清理数据目录..."
    rm -rf data/db/*.db
    rm -rf videoFile/*
    rm -rf logs/*
    echo "✅ 数据已清理！"
fi

# 询问是否清理Docker镜像
read -p "是否清理未使用的Docker镜像？(y/N): " cleanup_images

if [[ $cleanup_images =~ ^[Yy]$ ]]; then
    echo "🧹 清理未使用的Docker镜像..."
    docker image prune -f
    echo "✅ Docker镜像已清理！"
fi

echo "🎉 清理完成！"
