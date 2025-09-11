"""
账户上下文管理模块
为上传器提供统一的账户数据访问接口，支持文件和MySQL两种存储方式
"""

import tempfile
import json
import os
from pathlib import Path
from utils.account_data_manager import AccountDataManager
from db.mysql_connection import mysql_connect
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AccountContextManager:
    """账户上下文管理器，用于获取storage_state数据"""
    
    @staticmethod
    def get_storage_state_path(account_file_path):
        """
        获取storage_state文件路径，支持MySQL和文件两种存储方式
        
        Args:
            account_file_path: 账户文件路径（可能是文件路径或mysql://格式）
            
        Returns:
            str: 实际的文件路径（MySQL存储的情况会创建临时文件）
            
        Note:
            返回的临时文件需要调用者负责清理
        """
        # 检查是否是MySQL存储格式
        if isinstance(account_file_path, str) and account_file_path.startswith('mysql://'):
            return AccountContextManager._get_mysql_storage_state(account_file_path)
        else:
            # 传统文件存储方式，直接返回路径
            return str(account_file_path)
    
    @staticmethod
    def _get_mysql_storage_state(mysql_path):
        """
        从MySQL获取storage_state数据并创建临时文件
        
        Args:
            mysql_path: MySQL路径格式 (mysql://uuid)
            
        Returns:
            str: 临时文件路径
        """
        try:
            # 从filePath查找对应的account_id
            with mysql_connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM user_info WHERE filePath = ?", (mysql_path,))
                result = cursor.fetchone()
                
                if not result:
                    logger.error(f"未找到账户记录: {mysql_path}")
                    raise Exception(f"Account not found: {mysql_path}")
                
                account_id = result[0]
            
            # 从MySQL获取storage_state数据
            storage_state = AccountDataManager.get_account_data(account_id)
            if not storage_state:
                logger.error(f"账户 {account_id} 数据不存在或已过期")
                raise Exception(f"Account data not found or expired: {account_id}")
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.json', 
                delete=False,
                encoding='utf-8'
            )
            
            json.dump(storage_state, temp_file, ensure_ascii=False, indent=2)
            temp_file.close()
            
            logger.info(f"为账户 {account_id} 创建临时文件: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"从MySQL获取storage_state失败: {e}")
            raise
    
    @staticmethod
    def save_storage_state_after_upload(account_file_path, playwright_context):
        """
        上传完成后保存storage_state数据
        
        Args:
            account_file_path: 原始账户文件路径
            playwright_context: Playwright上下文对象
        """
        try:
            # 检查是否是MySQL存储格式
            if isinstance(account_file_path, str) and account_file_path.startswith('mysql://'):
                AccountContextManager._save_mysql_storage_state(account_file_path, playwright_context)
            else:
                # 传统文件存储方式，直接保存到文件
                import asyncio
                asyncio.create_task(playwright_context.storage_state(path=str(account_file_path)))
                
        except Exception as e:
            logger.error(f"保存storage_state失败: {e}")
    
    @staticmethod
    def _save_mysql_storage_state(mysql_path, playwright_context):
        """
        保存storage_state数据到MySQL
        
        Args:
            mysql_path: MySQL路径格式 (mysql://uuid)
            playwright_context: Playwright上下文对象
        """
        try:
            # 获取当前的storage_state数据
            import asyncio
            storage_state = asyncio.run(playwright_context.storage_state())
            
            # 从filePath查找对应的account_id
            with mysql_connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM user_info WHERE filePath = ?", (mysql_path,))
                result = cursor.fetchone()
                
                if not result:
                    logger.error(f"未找到账户记录: {mysql_path}")
                    return
                
                account_id = result[0]
            
            # 保存到MySQL
            if AccountDataManager.save_account_data(account_id, storage_state):
                logger.info(f"账户 {account_id} 的storage_state已更新到MySQL")
            else:
                logger.error(f"更新账户 {account_id} 的storage_state失败")
                
        except Exception as e:
            logger.error(f"保存storage_state到MySQL失败: {e}")
    
    @staticmethod
    def cleanup_temp_file(file_path):
        """
        清理临时文件
        
        Args:
            file_path: 文件路径
        """
        try:
            if file_path and os.path.exists(file_path) and file_path.startswith(tempfile.gettempdir()):
                os.unlink(file_path)
                logger.debug(f"已清理临时文件: {file_path}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

# 上下文管理器类，用于自动处理临时文件清理
class StorageStateContext:
    """Storage State上下文管理器，自动处理临时文件的创建和清理"""
    
    def __init__(self, account_file_path):
        self.account_file_path = account_file_path
        self.temp_file_path = None
        self.is_temp_file = False
    
    def __enter__(self):
        """进入上下文时获取storage_state文件路径"""
        self.temp_file_path = AccountContextManager.get_storage_state_path(self.account_file_path)
        
        # 检查是否为临时文件（MySQL存储方式）
        if (isinstance(self.account_file_path, str) and 
            self.account_file_path.startswith('mysql://') and
            self.temp_file_path.startswith(tempfile.gettempdir())):
            self.is_temp_file = True
        
        return self.temp_file_path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时清理临时文件"""
        if self.is_temp_file and self.temp_file_path:
            AccountContextManager.cleanup_temp_file(self.temp_file_path)

# 异步上下文管理器类
class AsyncStorageStateContext:
    """异步Storage State上下文管理器"""
    
    def __init__(self, account_file_path):
        self.account_file_path = account_file_path
        self.temp_file_path = None
        self.is_temp_file = False
    
    async def __aenter__(self):
        """异步进入上下文"""
        return self.__enter__()
    
    def __enter__(self):
        """进入上下文时获取storage_state文件路径"""
        self.temp_file_path = AccountContextManager.get_storage_state_path(self.account_file_path)
        
        # 检查是否为临时文件（MySQL存储方式）
        if (isinstance(self.account_file_path, str) and 
            self.account_file_path.startswith('mysql://') and
            self.temp_file_path.startswith(tempfile.gettempdir())):
            self.is_temp_file = True
        
        return self.temp_file_path
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步退出上下文"""
        return self.__exit__(exc_type, exc_val, exc_tb)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时清理临时文件"""
        if self.is_temp_file and self.temp_file_path:
            AccountContextManager.cleanup_temp_file(self.temp_file_path)

# 便捷函数
def get_storage_state_path(account_file):
    """
    便捷函数：获取storage_state文件路径
    
    Args:
        account_file: 账户文件路径
        
    Returns:
        str: 实际文件路径
    """
    return AccountContextManager.get_storage_state_path(account_file)

def storage_state_context(account_file):
    """
    便捷函数：创建storage_state上下文管理器
    
    Args:
        account_file: 账户文件路径
        
    Returns:
        StorageStateContext: 上下文管理器
    """
    return StorageStateContext(account_file)
