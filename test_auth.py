#!/usr/bin/env python3
"""
测试认证系统功能
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:5409"

def test_login():
    """测试登录功能"""
    print("🔍 测试管理员登录...")
    
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=login_data,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 200:
                token = data['data']['access_token']
                print("✅ 登录成功!")
                print(f"Token: {token[:50]}...")
                return token
            else:
                print("❌ 登录失败:", data.get('msg'))
                return None
        else:
            print("❌ HTTP错误:", response.status_code)
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败，请确保后端服务已启动")
        return None
    except Exception as e:
        print(f"❌ 请求错误: {e}")
        return None

def test_profile(token):
    """测试获取用户信息"""
    print("\n🔍 测试获取用户信息...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/auth/profile",
            headers=headers,
            timeout=5
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 200:
                print("✅ 获取用户信息成功!")
                print(f"用户信息: {json.dumps(data['data'], indent=2, ensure_ascii=False)}")
                return True
            else:
                print("❌ 获取失败:", data.get('msg'))
                return False
        else:
            print("❌ HTTP错误:", response.status_code)
            return False
            
    except Exception as e:
        print(f"❌ 请求错误: {e}")
        return False

def test_protected_api(token):
    """测试受保护的API"""
    print("\n🔍 测试受保护的API (getFiles)...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/getFiles",
            headers=headers,
            timeout=5
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            print("✅ 受保护API访问成功!")
            return True
        else:
            print("❌ 受保护API访问失败")
            return False
            
    except Exception as e:
        print(f"❌ 请求错误: {e}")
        return False

def main():
    print("🚀 开始测试认证系统...")
    
    # 等待服务启动
    print("⏳ 等待服务启动...")
    time.sleep(3)
    
    # 测试登录
    token = test_login()
    if not token:
        print("❌ 登录测试失败，无法继续后续测试")
        sys.exit(1)
    
    # 测试获取用户信息
    if not test_profile(token):
        print("❌ 用户信息测试失败")
    
    # 测试受保护的API
    if not test_protected_api(token):
        print("❌ 受保护API测试失败")
    
    print("\n🎉 认证系统测试完成!")

if __name__ == "__main__":
    main()
