import sqlite3
import json
import os

# 数据库文件路径（如果不存在会自动创建）
# 注意：这个脚本现在主要用于独立创建数据库，实际运行时数据库在 data/db/database.db
db_file = './data/db/database.db'

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

# 创建文件记录表
cursor.execute('''CREATE TABLE IF NOT EXISTS file_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- 唯一标识每条记录
    filename TEXT NOT NULL,               -- 文件名
    filesize REAL,                     -- 文件大小（单位：MB）
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 上传时间，默认当前时间
    file_path TEXT                        -- 文件路径
)
''')

# 创建发布历史记录表
cursor.execute('''CREATE TABLE IF NOT EXISTS publish_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- 唯一标识每条记录
    task_id TEXT NOT NULL,                 -- 任务ID，用于防重复和追踪
    platform_type INTEGER NOT NULL,        -- 平台类型：1小红书 2视频号 3抖音 4快手
    platform_name TEXT NOT NULL,           -- 平台名称
    account_name TEXT NOT NULL,            -- 账号名称
    account_file_path TEXT NOT NULL,       -- 账号文件路径
    title TEXT NOT NULL,                   -- 视频标题
    tags TEXT,                             -- 话题标签，JSON格式存储
    file_list TEXT NOT NULL,               -- 文件列表，JSON格式存储
    status TEXT DEFAULT 'pending',         -- 发布状态：pending发布中 success成功 failed失败
    error_message TEXT,                    -- 错误信息（如果发布失败）
    publish_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 发布时间
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 创建时间
    enable_timer INTEGER DEFAULT 0,        -- 是否启用定时发布：0否 1是
    videos_per_day INTEGER DEFAULT 1,      -- 每天发布视频数量
    daily_times TEXT,                      -- 每天发布时间，JSON格式存储
    start_days INTEGER DEFAULT 0,          -- 开始天数：0明天 1后天
    category INTEGER DEFAULT 0             -- 原创标识：0非原创 其他为原创
)
''')


# 提交更改
conn.commit()
print("✅ 表创建成功")
# 关闭连接
conn.close()