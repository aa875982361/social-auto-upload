import os
from conf import LOCAL_CHROME_PATH

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
                '--disable-gpu'
            ]
        }
    else:
        return {
            'headless': False,
            'executable_path': LOCAL_CHROME_PATH
        }

def get_browser_launch_options(executable_path=None, proxy=None):
    """获取浏览器启动选项，支持自定义可执行路径和代理"""
    options = get_browser_options()
    
    if executable_path:
        options['executable_path'] = executable_path
    
    if proxy:
        options['proxy'] = proxy
    
    return options
