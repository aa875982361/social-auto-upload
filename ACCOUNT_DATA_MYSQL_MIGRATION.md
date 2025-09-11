# 账户数据MySQL迁移方案实施文档

## 📋 迁移概述

本文档描述了将账户cookies和登录信息从文件存储迁移到MySQL数据库的完整实施方案。

## ✅ 已完成的工作

### 1. 数据库表结构设计

已创建 `account_data` 表用于存储账户的cookies和登录信息：

```sql
CREATE TABLE IF NOT EXISTS account_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL COMMENT '关联user_info表的ID',
    cookies_data JSON COMMENT '存储cookies的JSON数据',
    origins_data JSON COMMENT '存储origins的JSON数据（localStorage等）',
    local_storage JSON COMMENT '存储localStorage数据',
    session_storage JSON COMMENT '存储sessionStorage数据',
    cookies_expire_time TIMESTAMP NULL COMMENT 'cookies过期时间',
    is_valid TINYINT(1) DEFAULT 1 COMMENT '是否有效',
    last_check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '最后检查时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES user_info(id) ON DELETE CASCADE,
    INDEX idx_account_id (account_id),
    INDEX idx_is_valid (is_valid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

### 2. 账户数据管理器

创建了 `utils/account_data_manager.py` 模块，提供：

- **AccountDataManager 类**：统一的账户数据CRUD操作
- **save_account_data()**：保存playwright storage_state到MySQL
- **get_account_data()**：从MySQL读取并重构storage_state格式
- **mark_account_invalid()**：标记账户为无效
- **check_account_validity()**：检查账户有效性
- **delete_account_data()**：删除账户数据
- **get_user_accounts_with_data()**：获取用户账户及数据状态

### 3. 登录逻辑更新

修改了 `myUtils/login.py` 中的所有登录函数：

- **视频号登录** (`get_tencent_cookie`)
- **快手登录** (`get_ks_cookie`) 
- **小红书登录** (`xiaohongshu_cookie_gen`)

**更新内容：**
- 获取playwright的storage_state数据
- 临时保存文件仅用于验证
- 验证成功后保存到MySQL数据库
- `user_info` 表的 `filePath` 字段使用 `mysql://uuid` 格式
- 自动清理临时验证文件

### 4. 账户验证逻辑更新

更新了 `myUtils/auth.py` 的验证机制：

- **check_cookie_from_mysql()**：从MySQL验证cookie有效性
- **check_cookie()**：支持文件和MySQL两种存储方式
- 自动检测 `mysql://` 格式的账户路径
- 创建临时文件进行验证，验证后自动清理
- 验证失败时自动标记账户为无效

### 5. 账户上下文管理器

创建了 `utils/account_context_manager.py` 模块：

- **AccountContextManager 类**：统一的storage_state访问接口
- **get_storage_state_path()**：获取实际文件路径（支持MySQL临时文件）
- **save_storage_state_after_upload()**：上传后保存storage_state
- **StorageStateContext**：上下文管理器，自动处理临时文件清理
- **AsyncStorageStateContext**：异步版本的上下文管理器

### 6. 上传器适配

以抖音上传器为例，展示了如何使用新的账户管理系统：

```python
from utils.account_context_manager import storage_state_context, AccountContextManager

# 在upload方法中使用
with storage_state_context(self.account_file) as storage_state_file:
    context = await browser.new_context(storage_state=storage_state_file)
    # ... 执行上传逻辑
    
    # 保存更新的cookies
    if isinstance(self.account_file, str) and self.account_file.startswith('mysql://'):
        AccountContextManager.save_storage_state_after_upload(self.account_file, context)
    else:
        await context.storage_state(path=self.account_file)
```

### 7. API接口更新

更新了 `sau_backend.py` 中的 `getValidAccounts` 接口：

- 使用 `AccountDataManager.get_user_accounts_with_data()` 获取账户信息
- 返回数据包含账户的数据状态：
  - `has_data`: 是否有登录数据 (0/1)
  - `is_valid`: 数据是否有效 (0/1)

### 8. 前端数据格式更新

更新了 `sau_frontend/src/stores/account.js`：

- 兼容新的数据格式（向后兼容）
- 新增字段：
  - `hasData`: 是否有登录数据
  - `isValid`: 数据是否有效  
  - `dataStatus`: 数据状态描述（'有效'/'已过期'/'无数据'）

## 🔄 迁移机制

### 兼容性设计

1. **向后兼容**：系统同时支持文件存储和MySQL存储
2. **自动识别**：通过 `filePath` 字段的 `mysql://` 前缀识别存储方式
3. **渐进迁移**：新登录的账户自动使用MySQL存储，旧账户继续使用文件存储

### 数据流程

1. **用户登录** → 获取storage_state → 保存到MySQL → 更新user_info表
2. **账户验证** → 检测存储方式 → 从MySQL/文件读取 → 临时文件验证 → 清理
3. **视频发布** → 使用上下文管理器 → 获取临时文件 → 发布完成 → 更新MySQL → 清理

## 🚀 使用方式

### 启动数据库

确保MySQL服务运行，并执行：

```bash
# 初始化数据库和表结构
python scripts/init_mysql.py
python db/createTable.py
```

### 新账户登录

新登录的账户会自动使用MySQL存储，`user_info` 表的 `filePath` 字段格式为 `mysql://uuid`。

### 旧账户兼容

已有的文件存储账户会继续正常工作，无需手动迁移。

## 🔧 配置要求

### 环境变量

确保 `conf.py` 中配置了正确的MySQL连接信息：

```python
DB_CONFIG = {
    'host': 'localhost',  # 或Docker环境下的mysql服务名
    'port': 3306,
    'user': 'sau_user',
    'password': 'sau_password', 
    'database': 'social_auto_upload',
    'charset': 'utf8mb4'
}
```

### 依赖安装

```bash
pip install PyMySQL==1.1.0
```

## 📊 优势

1. **性能提升**：MySQL查询比文件IO更高效
2. **并发安全**：MySQL的ACID特性保证数据一致性
3. **集中管理**：统一的数据存储便于备份和维护
4. **扩展性**：支持分布式部署和数据共享
5. **监控能力**：可以查询账户状态、过期时间等
6. **自动清理**：过期cookies自动标记为无效

## ⚠️ 注意事项

1. **不会迁移现有数据**：如前所述，本方案不迁移已有的文件数据
2. **临时文件**：系统会创建临时文件用于验证，验证后自动清理
3. **MySQL版本**：建议使用MySQL 5.7+，支持JSON数据类型
4. **字符集**：确保使用utf8mb4字符集以支持emoji等特殊字符

## 🎯 下一步计划

1. 其他上传器的适配（快手、视频号、小红书等）
2. 账户数据的自动过期清理机制
3. 数据库连接池优化
4. 监控面板显示账户状态统计
5. 批量账户健康检查功能
