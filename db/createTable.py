import pymysql
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from conf import DB_CONFIG
import bcrypt

def create_database_if_not_exists():
    """创建数据库（如果不存在）"""
    try:
        # 连接到MySQL服务器（不指定数据库）
        config_without_db = DB_CONFIG.copy()
        database_name = config_without_db.pop('database')
        
        conn = pymysql.connect(
            host=config_without_db['host'],
            port=config_without_db['port'],
            user=config_without_db['user'],
            password=config_without_db['password'],
            charset=config_without_db.get('charset', 'utf8mb4')
        )
        cursor = conn.cursor()
        
        # 创建数据库（如果不存在）
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"[OK] 数据库 {database_name} 创建成功或已存在")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] 创建数据库失败: {e}")
        raise

def get_mysql_connection():
    """获取MySQL连接"""
    try:
        # 确保数据库存在
        create_database_if_not_exists()
        
        # 连接到指定数据库
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            charset=DB_CONFIG.get('charset', 'utf8mb4')
        )
        cursor = conn.cursor()
        return conn, cursor
        
    except Exception as e:
        print(f"[ERROR] 连接MySQL失败: {e}")
        raise

# 连接到MySQL数据库
conn, cursor = get_mysql_connection()

# 创建用户认证表（需要先创建，因为其他表会引用它）
cursor.execute('''
CREATE TABLE IF NOT EXISTS auth_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user') DEFAULT 'user',
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
''')

# 创建账号记录表
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type INT NOT NULL,
    filePath TEXT NOT NULL COMMENT '存储文件路径',
    userName VARCHAR(255) NOT NULL,
    status INT DEFAULT 0,
    created_by INT,
    FOREIGN KEY (created_by) REFERENCES auth_users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
''')

# 创建文件记录表
cursor.execute('''
CREATE TABLE IF NOT EXISTS file_records (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '唯一标识每条记录',
    filename VARCHAR(255) NOT NULL COMMENT '文件名',
    filesize DECIMAL(10,2) COMMENT '文件大小（单位：MB）',
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间，默认当前时间',
    file_path TEXT COMMENT '文件路径',
    created_by INT COMMENT '创建者用户ID',
    FOREIGN KEY (created_by) REFERENCES auth_users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
''')

# 创建账户存储表（存储cookies和登录信息）
cursor.execute('''
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
''')

# 创建用户会话表（可选，用于记录登录会话）
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
''')


# 创建默认管理员账号（如果不存在）
cursor.execute("SELECT COUNT(*) FROM auth_users WHERE role = 'admin'")
admin_count = cursor.fetchone()[0]

if admin_count == 0:
    # 默认管理员密码：ljlqweboanndieuyqwenqwjkehia
    password = "ljlqweboanndieuyqwenqwjkehia"
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    cursor.execute('''
    INSERT INTO auth_users (username, email, password_hash, role)
    VALUES (%s, %s, %s, %s)
    ''', ('admin', 'admin@example.com', password_hash, 'admin'))
    print("[OK] 创建默认管理员账号: admin/ljlqweboanndieuyqwenqwjkehia")

# 检查并添加 created_by 字段到 user_info 表（MySQL版本已在创建表时包含）
try:
    # 检查现有数据，将其关联到默认管理员账户
    cursor.execute("SELECT COUNT(*) FROM user_info WHERE created_by IS NULL")
    count = cursor.fetchone()[0]
    if count > 0:
        cursor.execute("SELECT id FROM auth_users WHERE role = 'admin' LIMIT 1")
        admin_user = cursor.fetchone()
        if admin_user:
            cursor.execute("UPDATE user_info SET created_by = %s WHERE created_by IS NULL", (admin_user[0],))
            print(f"[OK] 已将 {count} 个现有账号关联到管理员用户")
    
    print("[OK] user_info 表检查完成")
        
except Exception as e:
    print(f"⚠️ 更新 user_info 表时出错: {e}")

# 提交更改
conn.commit()
print("[OK] MySQL表创建成功")

# 关闭连接
cursor.close()
conn.close()