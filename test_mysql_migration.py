#!/usr/bin/env python3
"""
MySQL迁移测试脚本
用于验证数据库连接和基本功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_mysql_connection():
    """测试MySQL连接"""
    try:
        from db.mysql_connection import db_connection
        
        print("🔌 测试MySQL连接...")
        if db_connection.test_connection():
            print("✅ MySQL连接成功！")
            return True
        else:
            print("❌ MySQL连接失败！")
            return False
    except Exception as e:
        print(f"❌ MySQL连接测试出错: {e}")
        return False

def test_mysql_operations():
    """测试MySQL基本操作"""
    try:
        from db.mysql_connection import mysql_connect
        
        print("🧪 测试MySQL基本操作...")
        
        with mysql_connect() as conn:
            cursor = conn.cursor()
            
            # 测试查询
            cursor.execute("SELECT COUNT(*) FROM auth_users")
            count = cursor.fetchone()[0]
            print(f"✅ 查询成功，auth_users表有 {count} 条记录")
            
            # 测试查询账号表
            cursor.execute("SELECT COUNT(*) FROM user_info")
            count = cursor.fetchone()[0]
            print(f"✅ 查询成功，user_info表有 {count} 条记录")
            
            # 测试查询文件表
            cursor.execute("SELECT COUNT(*) FROM file_records")
            count = cursor.fetchone()[0]
            print(f"✅ 查询成功，file_records表有 {count} 条记录")
            
        return True
        
    except Exception as e:
        print(f"❌ MySQL操作测试出错: {e}")
        return False

def test_auth_service():
    """测试认证服务"""
    try:
        from myUtils.auth_service import AuthService
        
        print("🔐 测试认证服务...")
        
        auth_service = AuthService()
        
        # 测试获取用户（应该有默认管理员）
        admin_user = auth_service.get_user_by_id(1)
        if admin_user:
            print(f"✅ 找到管理员用户: {admin_user['username']}")
        else:
            print("⚠️ 未找到管理员用户")
            
        return True
        
    except Exception as e:
        print(f"❌ 认证服务测试出错: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始MySQL迁移测试...\n")
    
    tests = [
        ("MySQL连接测试", test_mysql_connection),
        ("MySQL操作测试", test_mysql_operations),
        ("认证服务测试", test_auth_service),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！MySQL迁移成功！")
        return True
    else:
        print("⚠️ 部分测试失败，请检查配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
