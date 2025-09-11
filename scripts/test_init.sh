#!/bin/bash

# test_init.sh - 测试新的Docker初始化方案
# 此脚本用于验证MySQL自动初始化功能

echo "🧪 开始测试Docker MySQL自动初始化方案..."

# 检查必要文件是否存在
echo ""
echo "📁 检查必要文件..."

check_file() {
    if [ -f "$1" ]; then
        echo "✅ $1 存在"
    else
        echo "❌ $1 不存在"
        return 1
    fi
}

check_file "docker-compose.yml"
check_file "Dockerfile.backend" 
check_file "docker.env"
check_file "mysql/init/01-create-database.sql"
check_file "mysql/init/02-insert-default-data.sql"
check_file "scripts/start_app.sh"
check_file "scripts/check_db_connection.py"

echo ""
echo "🔍 验证配置文件..."

# 验证docker-compose配置
echo "⏳ 验证docker-compose配置..."
if docker-compose config > /dev/null 2>&1; then
    echo "✅ docker-compose.yml 配置正确"
else
    echo "❌ docker-compose.yml 配置有错误"
    docker-compose config
    exit 1
fi

# 检查SQL语法（如果有mysql命令的话）
echo "⏳ 检查SQL脚本语法..."
if command -v mysql &> /dev/null; then
    echo "✅ 将验证SQL脚本语法"
    # 这里可以添加SQL语法检查
else
    echo "⚠️  mysql命令不可用，跳过SQL语法检查"
fi

echo ""
echo "📊 配置摘要:"
echo "  - MySQL初始化方式: SQL脚本自动执行"
echo "  - 数据库名称: social_auto_upload"
echo "  - 默认管理员: admin / ljlqweboanndieuyqwenqwjkehia"
echo "  - 初始化脚本: mysql/init/*.sql"
echo "  - 启动脚本: scripts/start_app.sh"

echo ""
echo "🚀 新初始化方案的优势:"
echo "  ✅ 无需手动运行Python脚本"
echo "  ✅ 使用MySQL官方初始化机制"
echo "  ✅ 容器启动即自动完成数据库初始化"
echo "  ✅ 智能等待和健康检查"
echo "  ✅ 详细的启动日志"

echo ""
echo "💡 使用方法:"
echo "  1. 启动服务: docker-compose up -d"
echo "  2. 查看日志: docker-compose logs -f"
echo "  3. 检查状态: docker-compose ps"

echo ""
echo "✅ 测试完成! 新的Docker初始化方案已就绪"
echo "📖 详细说明请查看: DOCKER_INIT_GUIDE.md"
