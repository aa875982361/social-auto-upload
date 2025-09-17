import os
import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class JWTAuth:
    def __init__(self):
        self.jwt_secret = os.getenv('JWT_SECRET', 'your-jwt-secret-here')
        self.auth_username = os.getenv('AUTH_USERNAME', 'admin')
        self.auth_password = os.getenv('AUTH_PASSWORD', 'admin123')
        self.token_expire_hours = int(os.getenv('TOKEN_EXPIRE_HOURS', 24))
    
    def verify_credentials(self, username, password):
        """验证用户名和密码"""
        return username == self.auth_username and password == self.auth_password
    
    def generate_token(self, username):
        """生成JWT token"""
        payload = {
            'username': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=self.token_expire_hours),
            'iat': datetime.datetime.utcnow()
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def verify_token(self, token):
        """验证JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return True, payload
        except jwt.ExpiredSignatureError:
            return False, {'error': 'Token已过期'}
        except jwt.InvalidTokenError:
            return False, {'error': 'Token无效'}
    
    def get_token_from_request(self):
        """从请求中获取token"""
        # 从Authorization header获取
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
        
        # 从query parameter获取
        token = request.args.get('token')
        if token:
            return token
        
        return None

# 创建全局实例
jwt_auth = JWTAuth()

def token_required(f):
    """装饰器：要求有效的JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = jwt_auth.get_token_from_request()
        
        if not token:
            return jsonify({
                'code': 401,
                'msg': '缺少认证token',
                'data': None
            }), 401
        
        is_valid, payload = jwt_auth.verify_token(token)
        if not is_valid:
            return jsonify({
                'code': 401,
                'msg': payload.get('error', 'Token验证失败'),
                'data': None
            }), 401
        
        # 将用户信息添加到请求上下文
        request.current_user = payload.get('username')
        return f(*args, **kwargs)
    
    return decorated

def optional_token(f):
    """装饰器：可选的JWT token验证"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = jwt_auth.get_token_from_request()
        request.current_user = None
        
        if token:
            is_valid, payload = jwt_auth.verify_token(token)
            if is_valid:
                request.current_user = payload.get('username')
        
        return f(*args, **kwargs)
    
    return decorated
