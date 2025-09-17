# 认证系统部署指南

## 快速开始

### 1. 安装依赖

```bash
pip install PyJWT==2.8.0 python-dotenv==1.0.0
```

或者直接安装所有依赖：

```bash
pip install -r requirements.txt
```

### 2. 环境配置

复制环境变量示例文件：

```bash
cp env.example .env
```

编辑 `.env` 文件，配置认证参数：

```env
# 用户认证配置
AUTH_USERNAME=admin                    # 修改为你的用户名
AUTH_PASSWORD=your_secure_password     # 修改为你的安全密码
TOKEN_EXPIRE_HOURS=24                  # Token过期时间（小时）
JWT_SECRET=your-very-secure-jwt-secret # 修改为安全的JWT密钥
```

### 3. 启动应用

```bash
python sau_backend.py
```

应用将在 `http://localhost:5409` 启动。

## 测试认证系统

### 自动化测试

运行测试脚本：

```bash
python test_auth.py
```

### 手动测试

#### 1. 登录获取Token

```bash
curl -X POST http://localhost:5409/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

响应示例：
```json
{
  "code": 200,
  "msg": "登录成功",
  "data": {
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "username": "admin",
    "expire_hours": 24
  }
}
```

#### 2. 使用Token访问API

```bash
# 方式一：Authorization Header（推荐）
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5409/api/getFiles

# 方式二：Query Parameter
curl "http://localhost:5409/api/getFiles?token=YOUR_TOKEN"
```

## 前端集成

### JavaScript示例

```javascript
// 登录函数
async function login(username, password) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password })
  });
  
  const data = await response.json();
  if (data.code === 200) {
    // 保存token到localStorage
    localStorage.setItem('auth_token', data.data.token);
    return data.data.token;
  } else {
    throw new Error(data.msg);
  }
}

// API请求函数
async function apiRequest(url, options = {}) {
  const token = localStorage.getItem('auth_token');
  
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` })
    }
  };
  
  const response = await fetch(url, { ...defaultOptions, ...options });
  
  if (response.status === 401) {
    // Token无效，重定向到登录页
    localStorage.removeItem('auth_token');
    window.location.href = '/login';
    return;
  }
  
  return response.json();
}

// 使用示例
try {
  const files = await apiRequest('/api/getFiles');
  console.log('文件列表:', files);
} catch (error) {
  console.error('请求失败:', error);
}
```

### Vue.js示例

```javascript
// 创建axios拦截器
import axios from 'axios';

// 请求拦截器
axios.interceptors.request.use(
  config => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// 响应拦截器
axios.interceptors.response.use(
  response => {
    return response;
  },
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      this.$router.push('/login');
    }
    return Promise.reject(error);
  }
);
```

## 安全建议

### 生产环境配置

1. **强密码策略**
   ```env
   AUTH_PASSWORD=SuperSecurePassword123!@#
   JWT_SECRET=very-long-random-string-at-least-32-characters-long
   ```

2. **Token过期时间**
   ```env
   TOKEN_EXPIRE_HOURS=8  # 工作时间
   ```

3. **HTTPS部署**
   - 确保在生产环境中使用HTTPS
   - 永远不要在HTTP连接中传输token

### 安全增强

1. **添加请求限制**
   - 实现登录失败次数限制
   - 添加IP白名单功能

2. **日志监控**
   - 记录所有认证相关的操作
   - 监控异常的API访问模式

3. **Token刷新**
   - 实现token自动刷新机制
   - 添加refresh token功能

## 故障排除

### 常见问题

1. **"缺少认证token"错误**
   - 检查请求是否包含Authorization header
   - 确认token格式为 `Bearer <token>`

2. **"Token已过期"错误**
   - 重新登录获取新token
   - 检查TOKEN_EXPIRE_HOURS配置

3. **"用户名或密码错误"**
   - 检查.env文件中的AUTH_USERNAME和AUTH_PASSWORD配置
   - 确认环境变量是否正确加载

4. **"Token无效"错误**
   - 检查JWT_SECRET是否正确
   - 确认token没有被篡改

### 调试模式

开启调试日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

这将显示详细的认证过程信息。

## 更新说明

从无认证版本升级时，需要：

1. 安装新的依赖包
2. 配置环境变量
3. 更新前端代码以支持token认证
4. 测试所有API接口的认证功能
