# MySQL数据库迁移说明

本项目已从SQLite迁移到MySQL数据库。以下是详细的配置和使用说明。

## 🔄 迁移内容

1. ✅ 更新依赖包（PyMySQL）
2. ✅ 创建MySQL连接管理模块
3. ✅ 修改数据库表创建脚本
4. ✅ 更新所有业务代码中的数据库连接
5. ✅ 修改认证服务的数据库连接
6. ✅ 更新Docker配置，添加MySQL服务
7. ✅ 解决依赖冲突问题（移除mysql-connector-python）

## 📝 配置说明

### 本地开发环境

1. **安装MySQL服务器**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install mysql-server
   
   # CentOS/RHEL
   sudo yum install mysql-server
   
   # macOS
   brew install mysql
   
   # Windows
   # 下载并安装MySQL Community Server
   ```

2. **创建数据库和用户**
   ```sql
   CREATE DATABASE social_auto_upload CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'sau_user'@'localhost' IDENTIFIED BY 'sau_password';
   GRANT ALL PRIVILEGES ON social_auto_upload.* TO 'sau_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

3. **配置环境变量**
   ```bash
   cp env.example .env
   # 编辑.env文件，配置数据库连接信息
   ```

4. **初始化数据库表**
   ```bash
   python scripts/init_mysql.py
   # 或者直接运行
   python db/createTable.py
   ```

### Docker环境

1. **启动服务**
   ```bash
   docker-compose up -d
   ```

   Docker会自动：
   - 启动MySQL 8.0容器
   - 创建数据库和用户
   - 配置环境变量
   - 等待MySQL就绪后启动应用

2. **初始化数据库（如果需要）**
   ```bash
   docker-compose exec backend python db/createTable.py
   ```

## 🗃️ 数据库配置

### 默认配置
- **数据库名**: social_auto_upload
- **用户名**: sau_user
- **密码**: sau_password
- **端口**: 3306
- **字符集**: utf8mb4

### 环境变量
```bash
DB_HOST=localhost          # 数据库主机（Docker环境下为mysql）
DB_PORT=3306              # 数据库端口
DB_USER=sau_user          # 数据库用户名
DB_PASSWORD=sau_password   # 数据库密码
DB_NAME=social_auto_upload # 数据库名
```

## 📊 数据表结构

### auth_users（用户认证表）
- id: 用户ID（主键）
- username: 用户名（唯一）
- email: 邮箱（唯一）
- password_hash: 密码哈希
- role: 用户角色（admin/user）
- is_active: 是否激活
- created_at/updated_at: 创建/更新时间

### user_info（账号记录表）
- id: 记录ID（主键）
- type: 平台类型
- filePath: 文件路径
- userName: 账号名称
- status: 状态
- created_by: 创建者ID（外键）

### file_records（文件记录表）
- id: 文件ID（主键）
- filename: 文件名
- filesize: 文件大小（MB）
- upload_time: 上传时间
- file_path: 文件路径
- created_by: 创建者ID（外键）

### user_sessions（用户会话表）
- id: 会话ID（主键）
- user_id: 用户ID（外键）
- token_hash: Token哈希
- expires_at: 过期时间
- created_at: 创建时间

## 🔐 默认账号

- **用户名**: admin
- **密码**: ljlqweboanndieuyqwenqwjkehia
- **角色**: 管理员

## ⚠️ 注意事项

1. **数据迁移**: 原SQLite数据不会自动迁移，如需保留原数据请手动导入
2. **权限配置**: 确保MySQL用户有足够的权限操作数据库
3. **字符集**: 统一使用utf8mb4字符集支持emoji和中文
4. **时区**: 默认设置为+8:00（北京时间）
5. **连接池**: 使用连接池管理数据库连接，提高性能

## 🚀 启动方式

### 本地开发
```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python scripts/init_mysql.py

# 启动应用
python sau_backend.py
```

### Docker部署
```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
```

## 🔧 故障排除

### 常见问题

1. **依赖冲突问题**
   - 项目使用PyMySQL而不是mysql-connector-python，避免与protobuf版本冲突
   - 如果遇到安装问题，确保只安装PyMySQL==1.1.0

2. **连接被拒绝**
   - 检查MySQL服务是否启动
   - 验证用户名密码是否正确
   - 确认防火墙设置

3. **字符集问题**
   - 确保数据库和表使用utf8mb4字符集
   - 检查MySQL配置文件

4. **权限错误**
   - 检查数据库用户权限
   - 确认可以远程连接（如果需要）

### 日志查看
```bash
# Docker环境
docker-compose logs mysql
docker-compose logs backend

# 本地环境
tail -f logs/app.log
```

## 📈 性能优化建议

1. **连接池配置**: 根据并发量调整连接池大小
2. **索引优化**: 为常用查询字段添加索引
3. **缓存策略**: 考虑添加Redis缓存层
4. **监控告警**: 配置数据库性能监控

---

如有问题，请查看日志文件或联系开发团队。
