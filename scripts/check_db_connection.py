#!/usr/bin/env python3
"""
数据库连接检查脚本
在应用启动前检查MySQL连接是否正常
"""

import sys
import time
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def check_db_connection():
    """检查数据库连接"""
    max_retries = 30
    retry_interval = 2
    
    # 导入数据库配置
    try:
        from conf import DB_CONFIG
        import pymysql
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        return False
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"⏳ 尝试连接数据库 ({attempt}/{max_retries})...")
            
            # 尝试连接数据库
            conn = pymysql.connect(
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database'],
                charset=DB_CONFIG.get('charset', 'utf8mb4'),
                connect_timeout=5
            )
            
            # 执行简单查询验证连接
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
            conn.close()
            
            if result:
                print("✅ 数据库连接成功！")
                return True
                
        except Exception as e:
            print(f"⚠️  连接失败 ({attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                print(f"⏳ {retry_interval}秒后重试...")
                time.sleep(retry_interval)
            else:
                print("❌ 达到最大重试次数，数据库连接失败")
                return False
    
    return False

def check_tables_exist():
    """检查必要的表是否存在"""
    try:
        from conf import DB_CONFIG
        import pymysql
        
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            charset=DB_CONFIG.get('charset', 'utf8mb4')
        )
        
        required_tables = ['auth_users', 'user_info', 'file_records', 'account_data']
        
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            existing_tables = [table[0] for table in cursor.fetchall()]
            
        conn.close()
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            print(f"⚠️  缺少表: {', '.join(missing_tables)}")
            print("💡 这些表将由MySQL初始化脚本自动创建")
        else:
            print("✅ 所有必要的表都已存在")
            
        return len(missing_tables) == 0
        
    except Exception as e:
        print(f"⚠️  检查表结构时出错: {e}")
        return False

if __name__ == "__main__":
    print("🔍 开始数据库连接检查...")
    
    # 检查数据库连接
    if not check_db_connection():
        print("❌ 数据库连接检查失败")
        sys.exit(1)
    
    # 检查表结构
    print("\n🔍 检查数据库表结构...")
    check_tables_exist()
    
    print("\n🚀 数据库检查完成，可以启动应用")
