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
    status INTEGER DEFAULT 0,
    created_by INTEGER,      -- 创建者用户ID
    FOREIGN KEY (created_by) REFERENCES auth_users(id)
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

# 检查并添加 created_by 字段到 user_info 表
try:
    cursor.execute("PRAGMA table_info(user_info)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'created_by' not in columns:
        cursor.execute('ALTER TABLE user_info ADD COLUMN created_by INTEGER')
        print("✅ 已为 user_info 表添加 created_by 字段")
        
        # 如果存在现有数据，将其关联到默认管理员账户
        cursor.execute("SELECT COUNT(*) FROM user_info WHERE created_by IS NULL")
        count = cursor.fetchone()[0]
        if count > 0:
            cursor.execute("SELECT id FROM auth_users WHERE role = 'admin' LIMIT 1")
            admin_user = cursor.fetchone()
            if admin_user:
                cursor.execute("UPDATE user_info SET created_by = ? WHERE created_by IS NULL", (admin_user[0],))
                print(f"✅ 已将 {count} 个现有账号关联到管理员用户")
    else:
        print("✅ user_info 表已包含 created_by 字段")
        
except Exception as e:
    print(f"⚠️ 更新 user_info 表时出错: {e}")

# 提交更改
conn.commit()
print("✅ 表创建成功")
# 关闭连接
conn.close()