# 用户数据隔离设计

本文档描述了社交媒体自动发布系统中用户数据隔离的设计和实现。

## 设计目标

确保每个用户只能访问和操作自己的数据，实现多用户环境下的数据安全隔离。

## 隔离范围

### 1. 文件数据隔离

**文件上传和存储：**
- 每个用户的文件存储在独立的目录：`data/users/{user_id}/videos/`
- 数据库记录中使用 `created_by` 字段关联文件所有者
- 文件访问时验证所有权

**实现细节：**
```python
def get_user_video_dir(user_id):
    """获取用户专属视频目录"""
    video_dir = get_user_data_dir(user_id) / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    return video_dir
```

**接口保护：**
- `/upload` - 文件上传时自动关联当前用户
- `/getFiles` - 只返回当前用户的文件列表
- `/getFile` - 下载时验证文件所有权
- `/deleteFile` - 删除时验证所有权

### 2. 账号数据隔离

**账号存储：**
- 每个用户的账号文件存储在：`data/users/{user_id}/accounts/`
- 数据库 `user_info` 表使用 `created_by` 字段关联账号所有者
- 登录生成的 cookie 文件保存在用户专属目录

**实现细节：**
```python
def get_user_account_dir(user_id):
    """获取用户专属账号目录"""
    account_dir = get_user_data_dir(user_id) / "accounts"
    account_dir.mkdir(parents=True, exist_ok=True)
    return account_dir
```

**接口保护：**
- `/getValidAccounts` - 只返回当前用户的账号
- `/deleteAccount` - 删除时验证账号所有权
- `/updateUserinfo` - 更新时验证账号所有权
- `/login` - 登录生成的账号文件存储在用户目录

### 3. 发布操作隔离

**权限验证：**
- `/postVideo` - 验证使用的账号是否属于当前用户
- `/postVideoBatch` - 批量发布时验证所有账号权限

**实现示例：**
```python
# 验证账号权限：确保所有账号都属于当前用户
for account_file in account_list:
    cursor.execute('''
        SELECT COUNT(*) FROM user_info 
        WHERE filePath = ? AND created_by = ?
    ''', (account_file, current_user_id))
    
    if cursor.fetchone()[0] == 0:
        return jsonify({"code": 403, "msg": f"无权限使用账号: {account_file}"})
```

## 数据库设计

### 用户表 (auth_users)
```sql
CREATE TABLE auth_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 文件记录表 (file_records)
```sql
CREATE TABLE file_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filesize REAL,
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    file_path TEXT,
    created_by INTEGER,  -- 关联用户ID
    FOREIGN KEY (created_by) REFERENCES auth_users(id)
);
```

### 账号信息表 (user_info)
```sql
CREATE TABLE user_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type INTEGER NOT NULL,
    filePath TEXT NOT NULL,
    userName TEXT NOT NULL,
    status INTEGER DEFAULT 0,
    created_by INTEGER,  -- 关联用户ID
    FOREIGN KEY (created_by) REFERENCES auth_users(id)
);
```

## 目录结构

```
data/
└── users/
    ├── 1/                 # 用户ID为1的数据
    │   ├── videos/        # 用户上传的视频文件
    │   └── accounts/      # 用户的账号文件
    ├── 2/                 # 用户ID为2的数据
    │   ├── videos/
    │   └── accounts/
    └── ...
```

## 安全机制

### 1. 认证与授权
- 所有数据操作接口都需要用户认证 (`@require_user()`)
- 使用 JWT Token 识别当前用户身份
- 通过 `get_jwt_identity()` 获取当前用户ID

### 2. 数据访问控制
- 数据库查询时始终包含 `created_by = current_user_id` 条件
- 文件系统访问限制在用户专属目录内
- 跨用户数据访问返回 403 Forbidden

### 3. 路径安全
- 防止路径穿越攻击
- 文件名校验和清理
- 使用绝对路径避免相对路径漏洞

## 工具函数

### 数据隔离工具
```python
def get_user_data_dir(user_id):
    """获取用户专属数据目录"""
    user_dir = Path(BASE_DIR / "data" / "users" / str(user_id))
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir

def verify_file_ownership(file_path, user_id):
    """验证文件是否属于指定用户"""
    # 数据库查询验证

def verify_account_ownership(account_id, user_id):
    """验证账号是否属于指定用户"""
    # 数据库查询验证
```

## 测试

运行用户数据隔离测试：
```bash
python test_user_isolation.py
```

测试覆盖：
- ✅ 文件数据隔离
- ✅ 账号数据隔离  
- ✅ 防止跨用户访问
- ✅ 用户目录结构隔离

## 最佳实践

1. **始终验证所有权**：在任何数据操作前验证资源是否属于当前用户
2. **使用专属目录**：不同用户的文件存储在不同目录
3. **数据库约束**：使用外键约束确保数据关联的正确性
4. **最小权限原则**：用户只能访问必要的资源
5. **审计日志**：记录关键数据操作便于排查问题

## 升级说明

### 从旧版本升级

如果系统已有数据，需要执行数据迁移：

1. **添加 created_by 字段**（已在 createTable.py 中实现）
2. **迁移现有文件到用户目录**
3. **更新文件路径引用**
4. **验证数据完整性**

### 兼容性

- 新实现向后兼容现有的 cookiesFile 目录
- `check_cookie` 函数支持新旧路径格式
- 渐进式迁移，不影响现有功能

## 监控和维护

- 定期检查数据隔离完整性
- 监控跨用户访问尝试
- 清理孤立的文件和数据
- 用户数据备份和恢复策略
