#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音登录测试脚本
用于测试和验证抖音登录优化配置的效果
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent))

from myUtils.login import douyin_cookie_gen
from queue import Queue


async def test_douyin_login():
    """测试抖音登录功能"""
    print("🔍 开始测试抖音登录功能...")
    print(f"📁 当前工作目录: {os.getcwd()}")
    print(f"🐳 Docker环境: {os.getenv('DOCKER_ENV', 'false')}")
    print(f"🎯 抖音严格模式: {os.getenv('DOUYIN_STRICT_MODE', 'false')}")
    
    # 创建测试队列
    test_queue = Queue()
    test_user_id = "test_user_" + str(int(asyncio.get_event_loop().time()))
    
    try:
        # 执行抖音登录测试
        print(f"🚀 开始执行抖音登录测试，用户ID: {test_user_id}")
        await douyin_cookie_gen(test_user_id, test_queue)
        
        # 检查结果
        if not test_queue.empty():
            result = test_queue.get()
            if result == "200":
                print("✅ 抖音登录测试成功！")
                return True
            elif result.startswith("data:image"):
                print(f"📱 获取到二维码: {result[:50]}...")
                print("⏳ 请扫描二维码完成登录测试")
                return True
            else:
                print(f"❌ 抖音登录测试失败，返回码: {result}")
                return False
        else:
            print("❌ 测试队列为空，登录过程可能出现异常")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出现异常: {e}")
        return False


def print_optimization_tips():
    """打印优化建议"""
    print("\n📋 抖音登录优化建议:")
    print("1. 🔧 如果仍然触发二次验证，请设置环境变量 DOUYIN_STRICT_MODE=true")
    print("2. 🌐 确保服务器网络环境稳定，避免频繁切换IP")
    print("3. ⏰ 避免在高峰时段进行大量登录操作")
    print("4. 🔒 使用相同的浏览器指纹信息保持一致性")
    print("5. 📍 如果可能，保持地理位置信息的一致性")
    
    print("\n🛠 环境变量配置:")
    print("   export DOUYIN_STRICT_MODE=true  # 启用严格模式")
    print("   export DOCKER_ENV=true          # Docker环境标识")


if __name__ == "__main__":
    print("🎬 抖音登录优化测试工具")
    print("=" * 50)
    
    # 检查环境
    if not Path("conf.py").exists():
        print("❌ 未找到 conf.py 文件，请确保在项目根目录运行此脚本")
        sys.exit(1)
    
    print_optimization_tips()
    
    # 询问是否继续测试
    user_input = input("\n是否要进行实际的抖音登录测试？(y/N): ").strip().lower()
    if user_input in ['y', 'yes']:
        print("\n🚀 开始测试...")
        try:
            result = asyncio.run(test_douyin_login())
            if result:
                print("\n✅ 测试完成！")
            else:
                print("\n❌ 测试失败，请检查配置和网络环境")
        except KeyboardInterrupt:
            print("\n⚠️ 测试被用户中断")
        except Exception as e:
            print(f"\n❌ 测试异常: {e}")
    else:
        print("\n👋 测试取消，优化配置已应用到代码中")
    
    print("\n📚 更多信息请查看项目文档")
