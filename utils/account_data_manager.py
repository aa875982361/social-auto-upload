"""
账户数据管理模块
提供账户cookies和登录信息的MySQL存储管理
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from db.mysql_connection import mysql_connect

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AccountDataManager:
    """账户数据管理类"""
    
    @staticmethod
    def save_account_data(account_id: int, storage_state: Dict) -> bool:
        """
        保存账户数据到MySQL数据库
        
        Args:
            account_id: user_info表中的账户ID
            storage_state: playwright的storage_state数据
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with mysql_connect() as conn:
                cursor = conn.cursor()
                
                # 提取数据
                cookies_data = storage_state.get('cookies', [])
                origins_data = storage_state.get('origins', [])
                
                # 处理localStorage和sessionStorage数据
                local_storage = {}
                session_storage = {}
                
                for origin in origins_data:
                    origin_url = origin.get('origin', '')
                    if 'localStorage' in origin:
                        local_storage[origin_url] = origin['localStorage']
                    if 'sessionStorage' in origin:
                        session_storage[origin_url] = origin['sessionStorage']
                
                # 计算cookies过期时间（取最早过期的cookie时间）
                cookies_expire_time = None
                if cookies_data:
                    expire_times = []
                    for cookie in cookies_data:
                        if 'expires' in cookie and cookie['expires'] > 0:
                            expire_times.append(datetime.fromtimestamp(cookie['expires']))
                    
                    if expire_times:
                        cookies_expire_time = min(expire_times)
                
                # 检查是否已存在数据
                cursor.execute(
                    "SELECT id FROM account_data WHERE account_id = ?",
                    (account_id,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # 更新现有数据
                    cursor.execute('''
                        UPDATE account_data 
                        SET cookies_data = ?, origins_data = ?, local_storage = ?, 
                            session_storage = ?, cookies_expire_time = ?, 
                            is_valid = 1, last_check_time = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE account_id = ?
                    ''', (
                        json.dumps(cookies_data),
                        json.dumps(origins_data),
                        json.dumps(local_storage),
                        json.dumps(session_storage),
                        cookies_expire_time,
                        account_id
                    ))
                    logger.info(f"更新账户 {account_id} 的数据")
                else:
                    # 插入新数据
                    cursor.execute('''
                        INSERT INTO account_data 
                        (account_id, cookies_data, origins_data, local_storage, 
                         session_storage, cookies_expire_time, is_valid)
                        VALUES (?, ?, ?, ?, ?, ?, 1)
                    ''', (
                        account_id,
                        json.dumps(cookies_data),
                        json.dumps(origins_data),
                        json.dumps(local_storage),
                        json.dumps(session_storage),
                        cookies_expire_time
                    ))
                    logger.info(f"保存账户 {account_id} 的新数据")
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"保存账户数据失败: {e}")
            return False
    
    @staticmethod
    def get_account_data(account_id: int) -> Optional[Dict]:
        """
        获取账户数据
        
        Args:
            account_id: user_info表中的账户ID
            
        Returns:
            Dict: storage_state格式的数据，如果不存在返回None
        """
        try:
            with mysql_connect() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT cookies_data, origins_data, local_storage, session_storage,
                           is_valid, cookies_expire_time
                    FROM account_data 
                    WHERE account_id = ? AND is_valid = 1
                ''', (account_id,))
                
                result = cursor.fetchone()
                if not result:
                    return None
                
                # 检查cookies是否过期
                cookies_expire_time = result[5]
                if cookies_expire_time and datetime.now() > cookies_expire_time:
                    # 标记为无效
                    AccountDataManager.mark_account_invalid(account_id)
                    logger.warning(f"账户 {account_id} 的cookies已过期")
                    return None
                
                # 重构storage_state格式
                storage_state = {
                    'cookies': json.loads(result[0]) if result[0] else [],
                    'origins': json.loads(result[1]) if result[1] else []
                }
                
                # 合并localStorage和sessionStorage
                local_storage = json.loads(result[2]) if result[2] else {}
                session_storage = json.loads(result[3]) if result[3] else {}
                
                # 重新构建origins数据
                all_origins = set()
                for origin_url in local_storage.keys():
                    all_origins.add(origin_url)
                for origin_url in session_storage.keys():
                    all_origins.add(origin_url)
                
                for origin_url in all_origins:
                    origin_data = {'origin': origin_url}
                    if origin_url in local_storage:
                        origin_data['localStorage'] = local_storage[origin_url]
                    if origin_url in session_storage:
                        origin_data['sessionStorage'] = session_storage[origin_url]
                    
                    # 检查是否已存在
                    existing_origin = None
                    for origin in storage_state['origins']:
                        if origin.get('origin') == origin_url:
                            existing_origin = origin
                            break
                    
                    if existing_origin:
                        existing_origin.update(origin_data)
                    else:
                        storage_state['origins'].append(origin_data)
                
                return storage_state
                
        except Exception as e:
            logger.error(f"获取账户数据失败: {e}")
            return None
    
    @staticmethod
    def mark_account_invalid(account_id: int) -> bool:
        """
        标记账户为无效
        
        Args:
            account_id: user_info表中的账户ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            with mysql_connect() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE account_data 
                    SET is_valid = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE account_id = ?
                ''', (account_id,))
                
                conn.commit()
                logger.info(f"账户 {account_id} 已标记为无效")
                return True
                
        except Exception as e:
            logger.error(f"标记账户无效失败: {e}")
            return False
    
    @staticmethod
    def check_account_validity(account_id: int) -> bool:
        """
        检查账户是否有效
        
        Args:
            account_id: user_info表中的账户ID
            
        Returns:
            bool: 账户是否有效
        """
        try:
            with mysql_connect() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT is_valid, cookies_expire_time
                    FROM account_data 
                    WHERE account_id = ?
                ''', (account_id,))
                
                result = cursor.fetchone()
                if not result:
                    return False
                
                is_valid = result[0]
                cookies_expire_time = result[1]
                
                # 检查过期时间
                if cookies_expire_time and datetime.now() > cookies_expire_time:
                    AccountDataManager.mark_account_invalid(account_id)
                    return False
                
                return bool(is_valid)
                
        except Exception as e:
            logger.error(f"检查账户有效性失败: {e}")
            return False
    
    @staticmethod
    def delete_account_data(account_id: int) -> bool:
        """
        删除账户数据
        
        Args:
            account_id: user_info表中的账户ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with mysql_connect() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "DELETE FROM account_data WHERE account_id = ?",
                    (account_id,)
                )
                
                conn.commit()
                logger.info(f"账户 {account_id} 的数据已删除")
                return True
                
        except Exception as e:
            logger.error(f"删除账户数据失败: {e}")
            return False
    
    @staticmethod
    def get_user_accounts_with_data(user_id: int) -> List[Tuple]:
        """
        获取用户的所有账户及其数据状态
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Tuple]: 账户信息列表，每个元素包含(id, type, filePath, userName, status, has_data, is_valid)
        """
        try:
            with mysql_connect() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT ui.id, ui.type, ui.filePath, ui.userName, ui.status,
                           CASE WHEN ad.id IS NOT NULL THEN 1 ELSE 0 END as has_data,
                           COALESCE(ad.is_valid, 0) as is_valid
                    FROM user_info ui
                    LEFT JOIN account_data ad ON ui.id = ad.account_id
                    WHERE ui.created_by = ? AND ui.created_by IS NOT NULL
                    ORDER BY ui.id
                ''', (user_id,))
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"获取用户账户列表失败: {e}")
            return []

# 向后兼容：提供文件方式的读取函数（用于迁移期间）
def read_storage_state_from_file(file_path: str) -> Optional[Dict]:
    """
    从文件读取storage_state数据（向后兼容）
    
    Args:
        file_path: JSON文件路径
        
    Returns:
        Dict: storage_state数据，如果读取失败返回None
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except Exception as e:
        logger.error(f"读取文件 {file_path} 失败: {e}")
        return None

def save_storage_state_to_file(storage_state: Dict, file_path: str) -> bool:
    """
    保存storage_state数据到文件（向后兼容）
    
    Args:
        storage_state: storage_state数据
        file_path: JSON文件路径
        
    Returns:
        bool: 保存是否成功
    """
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(storage_state, f, ensure_ascii=False, indent=2)
            
        return True
        
    except Exception as e:
        logger.error(f"保存文件 {file_path} 失败: {e}")
        return False
