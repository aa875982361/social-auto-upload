-- MySQL数据库初始化脚本
-- 此脚本会在MySQL容器首次启动时自动执行

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS social_auto_upload CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE social_auto_upload;

-- 创建用户认证表（需要先创建，因为其他表会引用它）
CREATE TABLE IF NOT EXISTS auth_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user') DEFAULT 'user',
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建账号记录表
CREATE TABLE IF NOT EXISTS user_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type INT NOT NULL,
    filePath TEXT NOT NULL COMMENT '存储文件路径',
    userName VARCHAR(255) NOT NULL,
    status INT DEFAULT 0,
    created_by INT,
    FOREIGN KEY (created_by) REFERENCES auth_users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建文件记录表
CREATE TABLE IF NOT EXISTS file_records (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '唯一标识每条记录',
    filename VARCHAR(255) NOT NULL COMMENT '文件名',
    filesize DECIMAL(10,2) COMMENT '文件大小（单位：MB）',
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间，默认当前时间',
    file_path TEXT COMMENT '文件路径',
    created_by INT COMMENT '创建者用户ID',
    FOREIGN KEY (created_by) REFERENCES auth_users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建账户存储表（存储cookies和登录信息）
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建用户会话表（可选，用于记录登录会话）
CREATE TABLE IF NOT EXISTS user_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
