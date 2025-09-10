import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import request from '@/utils/request'

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('token') || null)

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  // 设置token
  const setToken = (newToken) => {
    token.value = newToken
    if (newToken) {
      localStorage.setItem('token', newToken)
      // 设置请求头
      request.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
    } else {
      localStorage.removeItem('token')
      delete request.defaults.headers.common['Authorization']
    }
  }

  // 设置用户信息
  const setUser = (userInfo) => {
    user.value = userInfo
  }

  // 用户登录
  const login = async (credentials) => {
    try {
      const data = await request.post('/api/auth/login', credentials)
      
      if (data.code === 200) {
        const { access_token, ...userInfo } = data.data
        setToken(access_token)
        setUser(userInfo)
        return userInfo
      } else {
        throw new Error(data.msg || '登录失败')
      }
    } catch (error) {
      console.error('Login error:', error)
      throw error.response?.data || error
    }
  }

  // 用户注册
  const register = async (userInfo) => {
    try {
      const response = await request.post('/api/auth/register', userInfo)
      
      if (response.data.code === 200) {
        return response.data.data
      } else {
        throw new Error(response.data.msg || '注册失败')
      }
    } catch (error) {
      console.error('Register error:', error)
      throw error.response?.data || error
    }
  }

  // 获取用户信息
  const fetchUserInfo = async () => {
    try {
      const response = await request.get('/api/auth/profile')
      
      if (response.data.code === 200) {
        setUser(response.data.data)
        return response.data.data
      } else {
        throw new Error(response.data.msg || '获取用户信息失败')
      }
    } catch (error) {
      console.error('Fetch user info error:', error)
      // 如果获取用户信息失败，清除token
      logout()
      throw error
    }
  }

  // 用户登出
  const logout = async () => {
    try {
      if (token.value) {
        await request.post('/api/auth/logout')
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      setToken(null)
      setUser(null)
    }
  }

  // 初始化时设置token到请求头
  if (token.value) {
    request.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  return {
    user,
    token,
    isLoggedIn,
    isAdmin,
    setToken,
    setUser,
    login,
    register,
    fetchUserInfo,
    logout
  }
})