import asyncio
import configparser
import os
import tempfile
import json

from playwright.async_api import async_playwright
from xhs import XhsClient

from conf import BASE_DIR
from utils.base_social_media import set_init_script
from utils.log import tencent_logger, kuaishou_logger
from pathlib import Path
from uploader.xhs_uploader.main import sign_local
from utils.browser_config import get_browser_options
from utils.account_data_manager import AccountDataManager

async def cookie_auth_douyin(account_file):
    async with async_playwright() as playwright:
        options = get_browser_options()
        browser = await playwright.chromium.launch(**options)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        try:
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=5000)
        except:
            print("[+] 等待5秒 cookie 失效")
            await context.close()
            await browser.close()
            return False
        # 2024.06.17 抖音创作者中心改版
        if await page.get_by_text('手机号登录').count() or await page.get_by_text('扫码登录').count():
            print("[+] 等待5秒 cookie 失效")
            return False
        else:
            print("[+] cookie 有效")
            return True

async def cookie_auth_tencent(account_file):
    async with async_playwright() as playwright:
        options = get_browser_options()
        browser = await playwright.chromium.launch(**options)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://channels.weixin.qq.com/platform/post/create")
        try:
            await page.wait_for_selector('div.title-name:has-text("微信小店")', timeout=5000)  # 等待5秒
            tencent_logger.error("[+] 等待5秒 cookie 失效")
            return False
        except:
            tencent_logger.success("[+] cookie 有效")
            return True

async def cookie_auth_ks(account_file):
    async with async_playwright() as playwright:
        options = get_browser_options()
        browser = await playwright.chromium.launch(**options)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://cp.kuaishou.com/article/publish/video")
        try:
            await page.wait_for_selector("div.names div.container div.name:text('机构服务')", timeout=5000)  # 等待5秒

            kuaishou_logger.info("[+] 等待5秒 cookie 失效")
            return False
        except:
            kuaishou_logger.success("[+] cookie 有效")
            return True


async def cookie_auth_xhs(account_file):
    async with async_playwright() as playwright:
        options = get_browser_options()
        browser = await playwright.chromium.launch(**options)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.xiaohongshu.com/creator-micro/content/upload")
        try:
            await page.wait_for_url("https://creator.xiaohongshu.com/creator-micro/content/upload", timeout=5000)
        except:
            print("[+] 等待5秒 cookie 失效")
            await context.close()
            await browser.close()
            return False
        # 2024.06.17 抖音创作者中心改版
        if await page.get_by_text('手机号登录').count() or await page.get_by_text('扫码登录').count():
            print("[+] 等待5秒 cookie 失效")
            return False
        else:
            print("[+] cookie 有效")
            return True


async def check_cookie_from_mysql(type, account_id):
    """从MySQL检查cookie有效性"""
    try:
        # 从MySQL获取账户数据
        storage_state = AccountDataManager.get_account_data(account_id)
        if not storage_state:
            print(f"[!] 账户 {account_id} 数据不存在或已过期")
            return False
        
        # 创建临时文件用于验证
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(storage_state, temp_file, ensure_ascii=False, indent=2)
            temp_file_path = temp_file.name
        
        try:
            # 使用临时文件进行验证
            result = await check_cookie(type, temp_file_path)
            
            if not result:
                # 如果验证失败，标记账户为无效
                AccountDataManager.mark_account_invalid(account_id)
            
            return result
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        print(f"[!] 从MySQL验证cookie失败: {e}")
        return False

async def check_cookie(type, file_path):
    """检查cookie有效性，file_path可以是完整路径或相对路径"""
    # 检查是否是MySQL存储的账户（以mysql://开头）
    if isinstance(file_path, str) and file_path.startswith('mysql://'):
        # 从filePath提取account_id（去掉mysql://前缀后查找对应的user_info记录）
        mysql_id = file_path.replace('mysql://', '')
        try:
            from db.mysql_connection import mysql_connect
            with mysql_connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM user_info WHERE filePath = ?", (file_path,))
                result = cursor.fetchone()
                if result:
                    account_id = result[0]
                    return await check_cookie_from_mysql(type, account_id)
        except Exception as e:
            print(f"[!] 查询MySQL账户ID失败: {e}")
            return False
    
    # 传统文件方式验证
    # 如果是完整路径，直接使用；否则使用旧的cookiesFile目录
    if Path(file_path).is_absolute() or '/' in file_path or '\\' in file_path:
        full_path = Path(file_path)
    else:
        full_path = Path(BASE_DIR / "cookiesFile" / file_path)
    
    match type:
        # 小红书
        case 1:
            return await cookie_auth_xhs(full_path)
        # 视频号
        case 2:
            return await cookie_auth_tencent(full_path)
        # 抖音
        case 3:
            return await cookie_auth_douyin(full_path)
        # 快手
        case 4:
            return await cookie_auth_ks(full_path)
        case _:
            return False

# a = asyncio.run(check_cookie(1,"3a6cfdc0-3d51-11f0-8507-44e51723d63c.json"))
# print(a)