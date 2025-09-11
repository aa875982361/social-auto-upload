import asyncio
import sqlite3
import os
import json

from playwright.async_api import async_playwright

from myUtils.auth import check_cookie
from utils.base_social_media import set_init_script
import uuid
from pathlib import Path
from conf import BASE_DIR
from utils.account_data_manager import AccountDataManager
from db.mysql_connection import mysql_connect

def get_user_account_dir(user_id):
    """获取用户专属账号目录"""
    from pathlib import Path
    account_dir = Path(BASE_DIR / "data" / "users" / str(user_id) / "accounts")
    account_dir.mkdir(parents=True, exist_ok=True)
    return account_dir

from utils.browser_config import get_browser_options, is_docker_env

# 抖音登录
async def douyin_cookie_gen(id,status_queue,current_user_id):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()
    async with async_playwright() as playwright:
        options = get_browser_options()
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://creator.douyin.com/")
        original_url = page.url
        img_locator = page.get_by_role("img", name="二维码")
        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)
        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            status_queue.put("500")
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        user_account_dir = get_user_account_dir(current_user_id)
        account_file_path = user_account_dir / f"{uuid_v1}.json"
        await context.storage_state(path=str(account_file_path))
        result = await check_cookie(3, str(account_file_path))
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO user_info (type, filePath, userName, status, created_by)
                                VALUES (?, ?, ?, ?, ?)
                                ''', (3, str(account_file_path), id, 1, current_user_id))
            conn.commit()
            print("✅ 用户状态已记录")
        status_queue.put("200")


# 视频号登录
async def get_tencent_cookie(id,status_queue,current_user_id):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = get_browser_options()
        if not is_docker_env():
            options['args'] = ['--lang en-GB']
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        # Pause the page, and start recording manually.
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto("https://channels.weixin.qq.com")
        original_url = page.url

        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        # 等待 iframe 出现（最多等 60 秒）
        iframe_locator = page.frame_locator("iframe").first

        # 获取 iframe 中的第一个 img 元素
        img_locator = iframe_locator.get_by_role("img").first

        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        print("✅ 图片地址:", src)
        status_queue.put(src)

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None
        # 获取storage_state数据
        storage_state = await context.storage_state()
        
        # 验证cookies
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        user_account_dir = get_user_account_dir(current_user_id)
        temp_file_path = user_account_dir / f"{uuid_v1}.json"
        
        # 临时保存文件用于验证
        await context.storage_state(path=str(temp_file_path))
        result = await check_cookie(2, str(temp_file_path))
        
        if not result:
            status_queue.put("500")
            # 清理临时文件
            if temp_file_path.exists():
                temp_file_path.unlink()
            await page.close()
            await context.close()
            await browser.close()
            return None
        
        await page.close()
        await context.close()
        await browser.close()

        # 保存到MySQL数据库
        try:
            with mysql_connect() as conn:
                cursor = conn.cursor()
                # 插入账户基本信息
                cursor.execute('''
                    INSERT INTO user_info (type, filePath, userName, status, created_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (2, f"mysql://{uuid_v1}", id, 1, current_user_id))
                
                account_id = cursor.lastrowid
                
                # 保存账户数据到MySQL
                if AccountDataManager.save_account_data(account_id, storage_state):
                    print("✅ 账户数据已保存到MySQL")
                    # 清理临时文件
                    if temp_file_path.exists():
                        temp_file_path.unlink()
                else:
                    print("❌ 保存账户数据到MySQL失败")
                    status_queue.put("500")
                    return None
                    
                conn.commit()
                print("✅ 用户状态已记录")
        except Exception as e:
            print(f"❌ 数据库操作失败: {e}")
            status_queue.put("500")
            return None
        status_queue.put("200")

# 快手登录
async def get_ks_cookie(id,status_queue,current_user_id):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()
    async with async_playwright() as playwright:
        options = get_browser_options()
        if not is_docker_env():
            options['args'] = ['--lang en-GB']
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://cp.kuaishou.com")

        # 定位并点击“立即登录”按钮（类型为 link）
        await page.get_by_role("link", name="立即登录").click()
        await page.get_by_text("扫码登录").click()
        img_locator = page.get_by_role("img", name="qrcode")
        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        original_url = page.url
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None
        # 获取storage_state数据
        storage_state = await context.storage_state()
        
        # 验证cookies
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        user_account_dir = get_user_account_dir(current_user_id)
        temp_file_path = user_account_dir / f"{uuid_v1}.json"
        
        # 临时保存文件用于验证
        await context.storage_state(path=str(temp_file_path))
        result = await check_cookie(4, str(temp_file_path))
        
        if not result:
            status_queue.put("500")
            # 清理临时文件
            if temp_file_path.exists():
                temp_file_path.unlink()
            await page.close()
            await context.close()
            await browser.close()
            return None
        
        await page.close()
        await context.close()
        await browser.close()

        # 保存到MySQL数据库
        try:
            with mysql_connect() as conn:
                cursor = conn.cursor()
                # 插入账户基本信息
                cursor.execute('''
                    INSERT INTO user_info (type, filePath, userName, status, created_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (4, f"mysql://{uuid_v1}", id, 1, current_user_id))
                
                account_id = cursor.lastrowid
                
                # 保存账户数据到MySQL
                if AccountDataManager.save_account_data(account_id, storage_state):
                    print("✅ 账户数据已保存到MySQL")
                    # 清理临时文件
                    if temp_file_path.exists():
                        temp_file_path.unlink()
                else:
                    print("❌ 保存账户数据到MySQL失败")
                    status_queue.put("500")
                    return None
                    
                conn.commit()
                print("✅ 用户状态已记录")
        except Exception as e:
            print(f"❌ 数据库操作失败: {e}")
            status_queue.put("500")
            return None
        status_queue.put("200")

# 小红书登录
async def xiaohongshu_cookie_gen(id,status_queue,current_user_id):
    url_changed_event = asyncio.Event()

    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = get_browser_options()
        if not is_docker_env():
            options['args'] = ['--lang en-GB']
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://creator.xiaohongshu.com/")
        await page.locator('img.css-wemwzq').click()

        img_locator = page.get_by_role("img").nth(2)
        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        original_url = page.url
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        # 获取storage_state数据
        storage_state = await context.storage_state()
        
        # 验证cookies
        print(f"UUID v1: {uuid_v1}")
        user_account_dir = get_user_account_dir(current_user_id)
        temp_file_path = user_account_dir / f"{uuid_v1}.json"
        
        # 临时保存文件用于验证
        await context.storage_state(path=str(temp_file_path))
        result = await check_cookie(1, str(temp_file_path))
        
        if not result:
            status_queue.put("500")
            # 清理临时文件
            if temp_file_path.exists():
                temp_file_path.unlink()
            await page.close()
            await context.close()
            await browser.close()
            return None
        
        await page.close()
        await context.close()
        await browser.close()

        # 保存到MySQL数据库
        try:
            with mysql_connect() as conn:
                cursor = conn.cursor()
                # 插入账户基本信息
                cursor.execute('''
                    INSERT INTO user_info (type, filePath, userName, status, created_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (1, f"mysql://{uuid_v1}", id, 1, current_user_id))
                
                account_id = cursor.lastrowid
                
                # 保存账户数据到MySQL
                if AccountDataManager.save_account_data(account_id, storage_state):
                    print("✅ 账户数据已保存到MySQL")
                    # 清理临时文件
                    if temp_file_path.exists():
                        temp_file_path.unlink()
                else:
                    print("❌ 保存账户数据到MySQL失败")
                    status_queue.put("500")
                    return None
                    
                conn.commit()
                print("✅ 用户状态已记录")
        except Exception as e:
            print(f"❌ 数据库操作失败: {e}")
            status_queue.put("500")
            return None
        status_queue.put("200")

# a = asyncio.run(xiaohongshu_cookie_gen(4,None))
# print(a)
