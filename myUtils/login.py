import asyncio
import sqlite3
import os
import datetime

from playwright.async_api import async_playwright

from myUtils.auth import check_cookie
from utils.base_social_media import set_init_script
import uuid
from pathlib import Path
from conf import BASE_DIR

from utils.browser_config import get_browser_options, is_docker_env


class ConsoleMessageCollector:
    """控制台消息收集器类，为每个登录会话提供独立的消息收集"""
    
    def __init__(self):
        self.messages = []
    
    def handle_console_message(self, msg):
        """处理控制台消息"""
        self.messages.append({
            "type": msg.type,
            "text": msg.text,
            "location": f"{msg.location['url']}:{msg.location['lineNumber']}:{msg.location['columnNumber']}" if msg.location else "unknown",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    def clear_messages(self):
        """清空消息列表"""
        self.messages = []
    
    def get_messages(self):
        """获取所有消息"""
        return self.messages.copy()
    
    def setup_page_listeners(self, page):
        """为页面设置控制台消息监听器"""
        self.clear_messages()  # 重置控制台消息列表
        page.on("console", self.handle_console_message)

# 调试失败时保存页面截图和调试信息
async def save_debug_info(page, platform_name, user_id, console_collector=None):
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_dir = Path(BASE_DIR / "data" / "logs" / "debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存页面截图
        screenshot_path = debug_dir / f"{platform_name}_{user_id}_{timestamp}_timeout.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        
        # 获取页面HTML源码
        try:
            page_content = await page.content()
            html_file = debug_dir / f"{platform_name}_{user_id}_{timestamp}_page.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(page_content)
        except Exception as e:
            print(f"⚠️ 保存页面HTML失败: {e}")
        
        # 保存调试信息
        debug_info = {
            "timestamp": timestamp,
            "platform": platform_name,
            "user_id": user_id,
            "current_url": page.url,
            "title": await page.title(),
            "is_docker": is_docker_env(),
            "viewport": page.viewport_size,
        }
        
        # 获取控制台消息
        console_messages = console_collector.get_messages() if console_collector else []
        
        debug_file = debug_dir / f"{platform_name}_{user_id}_{timestamp}_debug.txt"
        with open(debug_file, 'w', encoding='utf-8') as f:
            # 写入基本调试信息
            f.write("=== 基本信息 ===\n")
            for key, value in debug_info.items():
                f.write(f"{key}: {value}\n")
            
            # 写入控制台消息
            f.write("\n=== 控制台消息 ===\n")
            if console_messages:
                for msg in console_messages:
                    f.write(f"[{msg['timestamp']}] [{msg['type']}] {msg['text']} - {msg['location']}\n")
            else:
                f.write("无控制台消息记录\n")
        
        # 保存单独的控制台日志文件
        if console_messages:
            console_file = debug_dir / f"{platform_name}_{user_id}_{timestamp}_console.log"
            with open(console_file, 'w', encoding='utf-8') as f:
                for msg in console_messages:
                    f.write(f"[{msg['timestamp']}] [{msg['type']}] {msg['text']} - {msg['location']}\n")
        
        print(f"🔍 调试信息已保存到: {debug_dir}")
        print(f"📸 页面截图: {screenshot_path}")
        print(f"📝 调试信息: {debug_file}")
        print(f"💻 控制台消息数量: {len(console_messages)}")
        print(f"🌐 当前URL: {page.url}")
        print(f"📄 页面标题: {await page.title()}")
        print(f"🐳 Docker环境: {is_docker_env()}")
        
    except Exception as e:
        print(f"❌ 保存调试信息失败: {e}")

# 抖音登录
async def douyin_cookie_gen(id,status_queue):
    url_changed_event = asyncio.Event()
    console_collector = ConsoleMessageCollector()  # 创建独立的控制台消息收集器
    
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
        
        # 设置页面监听器
        console_collector.setup_page_listeners(page)
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
            await save_debug_info(page, "douyin_success", id, console_collector)
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            print("❌ 抖音登录监听页面跳转超时")
            await save_debug_info(page, "douyin", id, console_collector)
            await page.close()
            await context.close()
            await browser.close()
            status_queue.put("500")
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        await context.storage_state(path=Path(BASE_DIR / "cookiesFile" / f"{uuid_v1}.json"))
        result = await check_cookie(3, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()
        with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO user_info (type, filePath, userName, status)
                                VALUES (?, ?, ?, ?)
                                ''', (3, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ 用户状态已记录")
        status_queue.put("200")


# 视频号登录
async def get_tencent_cookie(id,status_queue):
    url_changed_event = asyncio.Event()
    console_collector = ConsoleMessageCollector()  # 创建独立的控制台消息收集器
    
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
        
        # 设置页面监听器
        console_collector.setup_page_listeners(page)
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
            print("❌ 视频号登录监听页面跳转超时")
            await save_debug_info(page, "tencent", id, console_collector)
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        await context.storage_state(path=Path(BASE_DIR / "cookiesFile" / f"{uuid_v1}.json"))
        result = await check_cookie(2,f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO user_info (type, filePath, userName, status)
                                VALUES (?, ?, ?, ?)
                                ''', (2, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ 用户状态已记录")
        status_queue.put("200")

# 快手登录
async def get_ks_cookie(id,status_queue):
    url_changed_event = asyncio.Event()
    console_collector = ConsoleMessageCollector()  # 创建独立的控制台消息收集器
    
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
        
        # 设置页面监听器
        console_collector.setup_page_listeners(page)
        await page.goto("https://cp.kuaishou.com")

        # 定位并点击"立即登录"按钮（类型为 link）
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
            print("❌ 快手登录监听页面跳转超时")
            await save_debug_info(page, "kuaishou", id, console_collector)
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        await context.storage_state(path=Path(BASE_DIR / "cookiesFile" / f"{uuid_v1}.json"))
        result = await check_cookie(4, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                        INSERT INTO user_info (type, filePath, userName, status)
                                        VALUES (?, ?, ?, ?)
                                        ''', (4, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ 用户状态已记录")
        status_queue.put("200")

# 小红书登录
async def xiaohongshu_cookie_gen(id,status_queue):
    url_changed_event = asyncio.Event()
    console_collector = ConsoleMessageCollector()  # 创建独立的控制台消息收集器

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
        
        # 设置页面监听器
        console_collector.setup_page_listeners(page)
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
            print("❌ 小红书登录监听页面跳转超时")
            await save_debug_info(page, "xiaohongshu", id, console_collector)
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        await context.storage_state(path=Path(BASE_DIR / "cookiesFile" / f"{uuid_v1}.json"))
        result = await check_cookie(1, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO user_info (type, filePath, userName, status)
                           VALUES (?, ?, ?, ?)
                           ''', (1, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ 用户状态已记录")
        status_queue.put("200")

# a = asyncio.run(xiaohongshu_cookie_gen(4,None))
# print(a)
