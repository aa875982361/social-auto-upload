-- MySQL默认数据插入脚本
-- 此脚本会在表创建后执行，插入默认数据

USE social_auto_upload;

-- 创建默认管理员账号（如果不存在）
-- 注意：此处使用预计算的bcrypt密码哈希，密码为：ljlqweboanndieuyqwenqwjkehia
INSERT IGNORE INTO auth_users (username, email, password_hash, role)
VALUES (
    'admin', 
    'admin@example.com', 
    '$2b$12$Rq05FPE7r81ImP73S5GJUeAlibKGHeeOHdDfLd2sKoXuhT5fJbODi', 
    'admin'
);

-- 为现有user_info记录分配默认创建者（如果存在未分配的记录）
UPDATE user_info 
SET created_by = (
    SELECT id FROM auth_users WHERE role = 'admin' LIMIT 1
) 
WHERE created_by IS NULL;
