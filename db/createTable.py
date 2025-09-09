import sqlite3
import json
import os

# 数据库文件路径（如果不存在会自动创建）
db_file = './database.db'

# 如果数据库已存在，则删除旧的表（可选）
# if os.path.exists(db_file):
#     os.remove(db_file)

# 连接到SQLite数据库（如果文件不存在则会自动创建）
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# 创建账号记录表
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type INTEGER NOT NULL,
    filePath TEXT NOT NULL,  -- 存储文件路径
    userName TEXT NOT NULL,
    status INTEGER DEFAULT 0
)
''')

# 创建用户认证表
cursor.execute('''
CREATE TABLE IF NOT EXISTS auth_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',  -- 'admin', 'user'
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

# 创建文件记录表
cursor.execute('''CREATE TABLE IF NOT EXISTS file_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- 唯一标识每条记录
    filename TEXT NOT NULL,               -- 文件名
    filesize REAL,                     -- 文件大小（单位：MB）
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 上传时间，默认当前时间
    file_path TEXT,                        -- 文件路径
    created_by INTEGER,                   -- 创建者用户ID
    FOREIGN KEY (created_by) REFERENCES auth_users(id)
)
''')

# 创建用户会话表（可选，用于记录登录会话）
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES auth_users(id)
)
''')


# 创建默认管理员账号（如果不存在）
cursor.execute("SELECT COUNT(*) FROM auth_users WHERE role = 'admin'")
admin_count = cursor.fetchone()[0]

if admin_count == 0:
    import bcrypt
    # 默认管理员密码：ljlqweboanndieuyqwenqwjkehia
    password = "ljlqweboanndieuyqwenqwjkehia"
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    cursor.execute('''
    INSERT INTO auth_users (username, email, password_hash, role)
    VALUES (?, ?, ?, ?)
    ''', ('admin', 'admin@example.com', password_hash, 'admin'))
    print("✅ 创建默认管理员账号: admin/ljlqweboanndieuyqwenqwjkehia")

# 提交更改
conn.commit()
print("✅ 表创建成功")
# 关闭连接
conn.close()