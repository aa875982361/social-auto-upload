#!/usr/bin/env python3
"""
MySQL数据库初始化脚本
用于创建数据库表和默认数据
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    # 运行数据库创建脚本
    import subprocess
    
    print("[INFO] 开始初始化MySQL数据库...")
    
    # 切换到项目根目录
    os.chdir(project_root)
    
    # 运行createTable.py
    result = subprocess.run([sys.executable, "db/createTable.py"], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("[OK] MySQL数据库初始化成功！")
        print(result.stdout)
    else:
        print("[ERROR] MySQL数据库初始化失败！")
        print("错误信息：", result.stderr)
        sys.exit(1)
        
except Exception as e:
    print(f"[ERROR] 初始化过程中发生错误: {e}")
    sys.exit(1)

print("\n📝 迁移完成说明：")
print("1. 数据库已从SQLite迁移到MySQL")
print("2. 原SQLite数据不会自动迁移，需要手动导入")
print("3. 默认管理员账号: admin / ljlqweboanndieuyqwenqwjkehia")
print("4. 请确保MySQL服务正在运行并配置正确")
