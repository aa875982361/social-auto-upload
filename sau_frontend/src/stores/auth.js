import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { http } from '@/utils/request'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const token = ref(localStorage.getItem('auth_token') || '')
  const userInfo = ref({
    username: localStorage.getItem('username') || '',
    loginTime: localStorage.getItem('login_time') || ''
  })

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)

  // 登录方法
  const login = async (credentials) => {
    try {
      const response = await http.post('/api/auth/login', {
        username: credentials.username,
        password: credentials.password
      })

      if (response.code === 200) {
        // 保存token和用户信息
        token.value = response.data.token
        userInfo.value = {
          username: response.data.username,
          loginTime: new Date().toLocaleString(),
          expireHours: response.data.expire_hours
        }

        // 存储到localStorage
        localStorage.setItem('auth_token', token.value)
        localStorage.setItem('username', userInfo.value.username)
        localStorage.setItem('login_time', userInfo.value.loginTime)

        // 如果选择记住密码
        if (credentials.rememberMe) {
          localStorage.setItem('saved_username', credentials.username)
          localStorage.setItem('saved_password', credentials.password)
        } else {
          localStorage.removeItem('saved_username')
          localStorage.removeItem('saved_password')
        }

        return response.data
      } else {
        throw new Error(response.msg || '登录失败')
      }
    } catch (error) {
      console.error('登录错误:', error)
      throw error
    }
  }

  // 登出方法
  const logout = () => {
    // 清除状态
    token.value = ''
    userInfo.value = {
      username: '',
      loginTime: ''
    }

    // 清除localStorage
    localStorage.removeItem('auth_token')
    localStorage.removeItem('username')
    localStorage.removeItem('login_time')

    // 重载页面到登录页
    window.location.href = '/login'
  }

  // 验证token有效性
  const verifyToken = async () => {
    if (!token.value) {
      return false
    }

    try {
      const response = await http.get('/api/auth/verify')
      return response.code === 200
    } catch (error) {
      console.error('Token验证失败:', error)
      // 如果token无效，清除认证信息
      if (error.response?.status === 401) {
        logout()
      }
      return false
    }
  }

  // 初始化时验证token
  const initAuth = async () => {
    if (token.value) {
      const isValid = await verifyToken()
      if (!isValid) {
        logout()
      }
    }
  }

  // 获取token（供请求拦截器使用）
  const getToken = () => token.value

  return {
    token,
    userInfo,
    isLoggedIn,
    login,
    logout,
    verifyToken,
    initAuth,
    getToken
  }
})
