"""
修复递归问题的MySQL数据库连接管理模块
提供数据库连接池和基础操作方法
"""

import pymysql
from contextlib import contextmanager
from conf import DB_CONFIG
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MySQLConnection:
    """MySQL连接管理类"""
    
    def __init__(self):
        self.config = DB_CONFIG.copy()
        # 转换配置格式以适配PyMySQL
        self.pymysql_config = {
            'host': self.config['host'],
            'port': self.config['port'],
            'user': self.config['user'],
            'password': self.config['password'],
            'database': self.config['database'],
            'charset': self.config.get('charset', 'utf8mb4'),
            'autocommit': self.config.get('autocommit', True),
            'cursorclass': pymysql.cursors.DictCursor
        }
        logger.info("MySQL连接配置初始化成功")
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        connection = None
        try:
            connection = pymysql.connect(**self.pymysql_config)
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            if connection:
                connection.close()

# 全局数据库连接实例
db_connection = MySQLConnection()

def get_db():
    """获取数据库连接实例"""
    return db_connection

# 简化的mysql_connect函数，避免复杂的包装类导致递归
@contextmanager  
def mysql_connect():
    """提供类似sqlite3.connect的接口，但简化实现以避免递归"""
    with db_connection.get_connection() as conn:
        
        # 简单的行包装类
        class MySQLRow:
            def __init__(self, row_dict):
                self.row_dict = row_dict if row_dict else {}
                
            def __getitem__(self, key):
                if isinstance(key, int):
                    # 通过索引访问（需要转换为列表）
                    values = list(self.row_dict.values())
                    if 0 <= key < len(values):
                        return values[key]
                    raise IndexError(f"Index {key} out of range")
                else:
                    # 通过列名获取值
                    if key in self.row_dict:
                        return self.row_dict[key]
                    raise KeyError(f"Column '{key}' not found")
            
            def keys(self):
                return list(self.row_dict.keys())
                
            def values(self):
                return list(self.row_dict.values())
        
        # 保存原始的cursor方法，避免递归
        original_cursor_method = conn.cursor
        
        # 简化的cursor包装类，直接使用原始cursor
        class MySQLCursor:
            def __init__(self, connection, original_cursor_func):
                self.conn = connection
                # 使用保存的原始cursor方法，避免递归调用
                self._real_cursor = original_cursor_func(pymysql.cursors.DictCursor)
                
            def execute(self, query, params=()):
                # 将SQLite的?占位符转换为MySQL的%s占位符
                mysql_query = query.replace('?', '%s')
                return self._real_cursor.execute(mysql_query, params)
            
            def executemany(self, query, params_list):
                mysql_query = query.replace('?', '%s') 
                return self._real_cursor.executemany(mysql_query, params_list)
            
            def fetchone(self):
                row = self._real_cursor.fetchone()
                if row:
                    return MySQLRow(row)
                return None
            
            def fetchall(self):
                rows = self._real_cursor.fetchall()
                return [MySQLRow(row) for row in rows]
            
            @property
            def rowcount(self):
                return self._real_cursor.rowcount
                
            @property 
            def lastrowid(self):
                return self.conn.insert_id()
            
            def close(self):
                self._real_cursor.close()
                
        # 简单地创建cursor方法，不会导致递归
        def create_cursor(*args, **kwargs):
            # 忽略传入的参数，因为我们已经在MySQLCursor中设置了DictCursor
            return MySQLCursor(conn, original_cursor_method)
        
        # 为连接添加cursor方法
        conn.cursor = create_cursor
        conn.row_factory = None  # 兼容性属性
        
        yield conn
