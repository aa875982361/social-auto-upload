import { http } from '@/utils/request'

// 用户相关API
export const userApi = {
  // 获取用户信息
  getUserInfo(id) {
    return http.get(`/api/user/${id}`)
  },
  
  // 获取用户列表
  getUserList(params) {
    return http.get('/api/user/list', params)
  },
  
  // 创建用户
  createUser(data) {
    return http.post('/api/user', data)
  },
  
  // 更新用户信息
  updateUser(id, data) {
    return http.put(`/api/user/${id}`, data)
  },
  
  // 删除用户
  deleteUser(id) {
    return http.delete(`/api/user/${id}`)
  },
  
  // 用户登录
  login(data) {
    return http.post('/api/auth/login', data)
  },
  
  // 用户注册
  register(data) {
    return http.post('/api/auth/register', data)
  },
  
  // 用户登出
  logout() {
    return http.post('/api/auth/logout')
  },
  
  // 刷新token
  refreshToken() {
    return http.post('/api/auth/refresh')
  }
}