import os

def is_docker_env():
    """检查是否在Docker环境中运行"""
    return os.getenv('DOCKER_ENV') == 'true' or os.path.exists('/.dockerenv')

def get_browser_options():
    """获取浏览器启动选项"""
    if is_docker_env():
        return {
            'headless': True,
            'args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-default-apps',
                '--disable-sync',
                '--no-default-browser-check',
                '--disable-background-networking',
                '--disable-component-extensions-with-background-pages'
            ]
        }
    else:
        return {
            'headless': False
        }

def get_browser_launch_options(executable_path=None, proxy=None):
    """获取浏览器启动选项，支持自定义可执行路径和代理"""
    options = get_browser_options()
    
    if executable_path:
        options['executable_path'] = executable_path
    
    if proxy:
        options['proxy'] = proxy
    
    return options

def get_douyin_optimized_context_options():
    """获取抖音优化的浏览器上下文选项，减少触发二次验证的可能性"""
    options = {
        'viewport': {'width': 1920, 'height': 1080},
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.4324.150 Safari/537.36',
        'locale': 'zh-CN',
        'timezone_id': 'Asia/Shanghai',
        'extra_http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
    }
    
    # 如果启用严格模式，添加更多的环境模拟
    if os.getenv('DOUYIN_STRICT_MODE', 'false').lower() == 'true':
        options.update({
            'permissions': ['geolocation'],
            'geolocation': {'latitude': 39.9042, 'longitude': 116.4074},  # 北京坐标
            'screen': {'width': 1920, 'height': 1080},
            'device_scale_factor': 1,
            'is_mobile': False,
            'has_touch': False
        })
    
    return options
