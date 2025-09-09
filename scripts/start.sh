#!/bin/bash

# Social Auto Upload Docker 启动脚本

set -e

echo "🚀 启动 Social Auto Upload 服务..."

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p data/db data/logs data/accounts
mkdir -p videoFile logs media ssl

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "📝 创建环境变量文件..."
    cp env.example .env
    echo "⚠️  请编辑 .env 文件配置您的环境变量"
fi

# 检查配置文件
if [ ! -f conf.py ]; then
    echo "📝 创建配置文件..."
    cp conf.example.py conf.py
    echo "⚠️  请编辑 conf.py 文件配置您的设置"
fi

# 选择启动模式
echo "请选择启动模式："
echo "1) 开发环境 (前后端分离，支持热重载)"
echo "2) 生产环境 (包含 Nginx 反向代理)"
echo "3) 仅后端服务"
echo "4) 仅前端服务"

read -p "请输入选择 (1-4): " choice

case $choice in
    1)
        echo "🔧 启动开发环境..."
        docker-compose -f docker-compose.dev.yml up -d
        echo "✅ 开发环境启动完成！"
        echo "🌐 前端地址: http://localhost:3000"
        echo "🔗 后端地址: http://localhost:5409"
        ;;
    2)
        echo "🏭 启动生产环境..."
        docker-compose --profile production up -d
        echo "✅ 生产环境启动完成！"
        echo "🌐 应用地址: http://localhost"
        echo "🔒 HTTPS地址: https://localhost (需要配置SSL证书)"
        ;;
    3)
        echo "🔧 启动后端服务..."
        docker-compose up -d backend
        echo "✅ 后端服务启动完成！"
        echo "🔗 后端地址: http://localhost:5409"
        ;;
    4)
        echo "🎨 启动前端服务..."
        docker-compose up -d frontend
        echo "✅ 前端服务启动完成！"
        echo "🌐 前端地址: http://localhost"
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

# 显示服务状态
echo ""
echo "📊 服务状态："
docker-compose ps

echo ""
echo "📋 常用命令："
echo "  查看日志: docker-compose logs -f"
echo "  停止服务: docker-compose down"
echo "  重启服务: docker-compose restart"
echo "  查看状态: docker-compose ps"
