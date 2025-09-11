"""
用户认证服务模块
提供用户注册、登录、JWT token生成和验证等功能
"""

import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from flask import current_app, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt, decode_token
import bcrypt
from functools import wraps
from conf import BASE_DIR
from db.mysql_connection import mysql_connect


class AuthService:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化Flask应用的JWT配置"""
        # JWT配置
        app.config['JWT_SECRET_KEY'] = 'your-secret-string-change-this-in-production'  # 生产环境请修改
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)  # Token有效期24小时
        app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)  # 刷新token有效期30天
        
        self.jwt = JWTManager(app)
        
        # 设置JWT错误处理
        @self.jwt.expired_token_loader
        def expired_token_callback(jwt_header, jwt_payload):
            return jsonify({
                'code': 401,
                'msg': 'Token已过期，请重新登录',
                'data': None
            }), 401
        
        @self.jwt.invalid_token_loader
        def invalid_token_callback(error):
            return jsonify({
                'code': 401,
                'msg': 'Token无效，请重新登录',
                'data': None
            }), 401
        
        @self.jwt.unauthorized_loader
        def missing_token_callback(error):
            return jsonify({
                'code': 401,
                'msg': '需要登录才能访问此资源',
                'data': None
            }), 401

    def hash_password(self, password):
        """密码哈希"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password, hashed):
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def get_db_connection(self):
        """获取数据库连接（已废弃，使用mysql_connect代替）"""
        # 这个方法保留是为了兼容性，但实际使用mysql_connect
        return mysql_connect()
    
    def register_user(self, username, email, password, role='user'):
        """用户注册"""
        try:
            with mysql_connect() as conn:
                cursor = conn.cursor()
                
                # 检查用户名和邮箱是否已存在
                cursor.execute(
                    "SELECT id FROM auth_users WHERE username = %s OR email = %s",
                    (username, email)
                )
                existing_user = cursor.fetchone()
                
                if existing_user:
                    return {
                        'success': False,
                        'message': '用户名或邮箱已存在'
                    }
                
                # 密码哈希
                password_hash = self.hash_password(password)
                
                # 插入新用户
                cursor.execute('''
                    INSERT INTO auth_users (username, email, password_hash, role)
                    VALUES (%s, %s, %s, %s)
                ''', (username, email, password_hash, role))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                return {
                    'success': True,
                    'message': '注册成功',
                    'user_id': user_id
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'注册失败: {str(e)}'
            }
    
    def authenticate_user(self, username, password):
        """用户认证"""
        try:
            with mysql_connect() as conn:
                cursor = conn.cursor()
                
                # 查找用户
                cursor.execute('''
                    SELECT id, username, email, password_hash, role, is_active
                    FROM auth_users 
                    WHERE (username = %s OR email = %s) AND is_active = 1
                ''', (username, username))
                
                user = cursor.fetchone()
                
                if not user:
                    return {
                        'success': False,
                        'message': '用户不存在或已被禁用'
                    }
                
                # 验证密码
                if not self.verify_password(password, user['password_hash']):
                    return {
                        'success': False,
                        'message': '密码错误'
                    }
                
                # 生成JWT token
                access_token = create_access_token(
                    identity=str(user['id']),  # 转换为字符串
                    additional_claims={
                        'username': user['username'],
                        'role': user['role']
                    }
                )
                
                # 记录登录会话
                self._create_session(user['id'], access_token)
                
                return {
                    'success': True,
                    'message': '登录成功',
                    'data': {
                        'user_id': user['id'],
                        'username': user['username'],
                        'email': user['email'],
                        'role': user['role'],
                        'access_token': access_token
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'登录失败: {str(e)}'
            }
    
    def _create_session(self, user_id, token):
        """创建用户会话记录"""
        try:
            with mysql_connect() as conn:
                cursor = conn.cursor()
                
                # 计算token过期时间
                expires_at = datetime.now() + timedelta(hours=24)
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                
                cursor.execute('''
                    INSERT INTO user_sessions (user_id, token_hash, expires_at)
                    VALUES (%s, %s, %s)
                ''', (user_id, token_hash, expires_at))
                
                conn.commit()
                
        except Exception as e:
            print(f"创建会话失败: {str(e)}")
    
    def get_user_by_id(self, user_id):
        """根据用户ID获取用户信息"""
        try:
            with mysql_connect() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, username, email, role, is_active, created_at
                    FROM auth_users 
                    WHERE id = %s AND is_active = 1
                ''', (user_id,))
                
                user = cursor.fetchone()
                
                if user:
                    return dict(user)
                return None
                
        except Exception as e:
            print(f"获取用户信息失败: {str(e)}")
            return None
    
    def logout_user(self, token):
        """用户登出（使token失效）"""
        try:
            with mysql_connect() as conn:
                cursor = conn.cursor()
                
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                
                cursor.execute('''
                    DELETE FROM user_sessions 
                    WHERE token_hash = %s
                ''', (token_hash,))
                
                conn.commit()
                
                return {
                    'success': True,
                    'message': '登出成功'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'登出失败: {str(e)}'
            }


def get_user_by_id_direct(user_id):
    """直接通过数据库连接获取用户信息，避免创建新的AuthService实例"""
    try:
        with mysql_connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, email, role, is_active, created_at
                FROM auth_users 
                WHERE id = %s AND is_active = 1
            ''', (user_id,))
            
            user = cursor.fetchone()
            
            if user:
                return dict(user)
            return None
            
    except Exception as e:
        print(f"获取用户信息失败: {str(e)}")
        return None


def require_auth(roles=None):
    """权限装饰器，可指定需要的角色"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            current_user_id = int(get_jwt_identity())  # 转换为整数
            claims = get_jwt()
            
            # 检查用户是否仍然有效
            # 直接使用数据库连接，避免创建新的AuthService实例
            user = get_user_by_id_direct(current_user_id)
            
            if not user:
                return jsonify({
                    'code': 401,
                    'msg': '用户不存在或已被禁用',
                    'data': None
                }), 401
            
            # 检查角色权限
            if roles and user['role'] not in roles:
                return jsonify({
                    'code': 403,
                    'msg': '权限不足',
                    'data': None
                }), 403
            
            # 将用户信息添加到请求上下文
            request.current_user = user
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_admin():
    """管理员权限装饰器"""
    return require_auth(['admin'])


def require_user():
    """用户权限装饰器（包括管理员）"""
    return require_auth(['user', 'admin'])


def verify_token_from_params():
    """
    从URL参数中验证token
    返回: (is_valid, user_info, error_response)
    """
    try:
        # 从URL参数获取token
        token = request.args.get('token')
        if not token:
            return False, None, jsonify({
                'code': 401,
                'msg': '缺少认证token',
                'data': None
            }), 401
        
        # 解码token
        try:
            decoded_token = decode_token(token)
            user_id = int(decoded_token['sub'])
        except Exception as e:
            return False, None, jsonify({
                'code': 401,
                'msg': 'Token无效或已过期',
                'data': None
            }), 401
        
        # 验证用户是否存在
        user = get_user_by_id_direct(user_id)
        
        if not user:
            return False, None, jsonify({
                'code': 401,
                'msg': '用户不存在或已被禁用',
                'data': None
            }), 401
        
        return True, user, None
        
    except Exception as e:
        return False, None, jsonify({
            'code': 500,
            'msg': f'Token验证失败: {str(e)}',
            'data': None
        }), 500
