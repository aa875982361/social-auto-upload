# Docker 数据库自动初始化指南

## 概述

本项目已实现了MySQL数据库的Docker自动初始化功能，无需手动运行Python脚本。数据库表结构和默认数据会在容器启动时自动创建。

## 新的初始化方案

### 1. MySQL 自动初始化

**特点：**
- 使用标准的MySQL Docker初始化机制
- 初始化脚本位于 `mysql/init/` 目录
- 容器首次启动时自动执行SQL脚本
- 无需Python依赖，更加可靠

**初始化文件：**
```
mysql/init/
├── 01-create-database.sql    # 创建数据库和表结构
└── 02-insert-default-data.sql # 插入默认数据
```

### 2. 应用启动等待机制

**特点：**
- 智能等待MySQL服务完全就绪
- 多层次检查：端口可用性 → 数据库连接 → 表结构验证
- 详细的启动日志输出

**相关文件：**
```
scripts/
├── start_app.sh              # 主启动脚本
├── check_db_connection.py    # 数据库连接检查
└── wait-for-mysql.sh         # MySQL等待脚本（备用）
```

## 使用方法

### 首次启动（生产环境）

```bash
# 1. 启动所有服务
docker-compose up -d

# 2. 查看启动日志
docker-compose logs -f backend

# 3. 验证服务状态
docker-compose ps
```

### 开发环境启动

```bash
# 使用开发环境配置
docker-compose -f docker-compose.dev.yml up -d
```

### 重新初始化数据库

如果需要重新初始化数据库：

```bash
# 1. 停止服务
docker-compose down

# 2. 删除数据库卷（注意：会丢失所有数据）
docker volume rm social-auto-upload_mysql_data

# 3. 重新启动
docker-compose up -d
```

## 配置说明

### 环境变量

主要配置在 `docker.env` 文件中：

```env
# 数据库配置
DB_HOST=mysql
DB_PORT=3306
DB_USER=sau_user
DB_PASSWORD=sau_password
DB_NAME=social_auto_upload

# MySQL Root配置
MYSQL_ROOT_PASSWORD=root_password_2024
```

### 默认账户

系统会自动创建默认管理员账户：
- **用户名**: `admin`
- **邮箱**: `admin@example.com`  
- **密码**: `ljlqweboanndieuyqwenqwjkehia`
- **角色**: `admin`

## 启动流程

1. **MySQL容器启动**
   - 执行 `mysql/init/` 目录下的SQL脚本
   - 创建数据库、表结构和默认数据

2. **后端应用启动**
   - 等待MySQL端口可用
   - 检查数据库连接
   - 验证表结构
   - 启动Flask应用

3. **前端服务启动**
   - 等待后端服务健康检查通过
   - 启动Nginx服务

## 故障排除

### 常见问题

1. **MySQL连接超时**
   ```bash
   # 检查MySQL容器状态
   docker-compose logs mysql
   
   # 检查网络连接
   docker-compose exec backend nc -z mysql 3306
   ```

2. **数据库初始化失败**
   ```bash
   # 查看MySQL初始化日志
   docker-compose logs mysql | grep -i error
   
   # 检查初始化脚本语法
   mysql -u root -p < mysql/init/01-create-database.sql
   ```

3. **应用启动失败**
   ```bash
   # 查看后端启动日志
   docker-compose logs backend
   
   # 手动测试数据库连接
   docker-compose exec backend python scripts/check_db_connection.py
   ```

### 健康检查

所有服务都配置了健康检查：

```bash
# 查看服务健康状态
docker-compose ps

# 查看具体健康检查日志
docker inspect $(docker-compose ps -q backend) | grep -A 20 Health
```

## 迁移说明

### 从旧版本迁移

如果你之前使用Python脚本初始化数据库：

1. **备份现有数据**（如果需要）
2. **停止旧版本服务**
3. **使用新的Docker配置启动**
4. **数据会自动重新初始化**

### 数据保留

- 数据库数据存储在Docker卷 `mysql_data` 中
- 应用数据存储在 `./data` 目录中
- 日志文件存储在 `./logs` 目录中

## 优势

相比之前的Python脚本方案：

✅ **更可靠**: 使用MySQL官方初始化机制  
✅ **更简单**: 无需手动运行脚本  
✅ **更快速**: 容器启动即完成初始化  
✅ **更标准**: 遵循Docker最佳实践  
✅ **更安全**: 避免Python依赖问题  
✅ **更清晰**: 启动流程日志详细  

## 技术细节

- **MySQL容器**: 使用官方MySQL 8.0镜像
- **初始化机制**: `/docker-entrypoint-initdb.d/` 目录自动执行
- **健康检查**: 多层次验证确保服务就绪
- **网络通信**: 使用Docker内部网络
- **数据持久化**: Docker卷管理数据存储
