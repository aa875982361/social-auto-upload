from pathlib import Path
import os

BASE_DIR = Path(__file__).parent.resolve()
XHS_SERVER = "http://127.0.0.1:11901"
LOCAL_CHROME_PATH = ""   # change me necessary！ for example C:/Program Files/Google/Chrome/Application/chrome.exe

# MySQL数据库配置
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'sau_user'),
    'password': os.environ.get('DB_PASSWORD', 'sau_password'),
    'database': os.environ.get('DB_NAME', 'social_auto_upload'),
    'charset': 'utf8mb4',
    'autocommit': True
}
