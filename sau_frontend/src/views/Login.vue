<template>
  <div class="login-container">
    <div class="login-form">
      <div class="logo-section">
        <img src="/vite.svg" alt="Logo" class="logo" />
        <h1>自媒体自动化运营系统</h1>
        <p>Social Auto Upload</p>
      </div>
      
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form-content"
        @keyup.enter="handleLogin"
      >
        <h2>用户登录</h2>
        
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            clearable
          />
        </el-form-item>
        
        <el-form-item>
          <el-checkbox v-model="loginForm.rememberMe">
            记住密码
          </el-checkbox>
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="tips">
        <p>默认账号：admin</p>
        <p>默认密码：admin123</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// 表单引用
const loginFormRef = ref()

// 加载状态
const loading = ref(false)

// 登录表单数据
const loginForm = reactive({
  username: '',
  password: '',
  rememberMe: false
})

// 表单验证规则
const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度在 2 到 20 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度在 6 到 20 个字符', trigger: 'blur' }
  ]
}

// 处理登录
const handleLogin = async () => {
  if (!loginFormRef.value) return

  try {
    await loginFormRef.value.validate()
    loading.value = true
    
    await authStore.login({
      username: loginForm.username,
      password: loginForm.password,
      rememberMe: loginForm.rememberMe
    })
    
    ElMessage.success('登录成功！')
    
    // 跳转到首页或之前访问的页面
    const redirect = router.currentRoute.value.query.redirect || '/'
    router.push(redirect)
    
  } catch (error) {
    console.error('登录失败:', error)
    ElMessage.error(error.message || '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}

// 组件挂载时检查是否已登录
onMounted(() => {
  if (authStore.isLoggedIn) {
    router.push('/')
  }
  
  // 如果记住密码，自动填充
  const savedUsername = localStorage.getItem('saved_username')
  const savedPassword = localStorage.getItem('saved_password')
  if (savedUsername && savedPassword) {
    loginForm.username = savedUsername
    loginForm.password = savedPassword
    loginForm.rememberMe = true
  }
})
</script>

<style lang="scss" scoped>
.login-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.login-form {
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
  
  .logo-section {
    text-align: center;
    margin-bottom: 30px;
    
    .logo {
      width: 60px;
      height: 60px;
      margin-bottom: 16px;
    }
    
    h1 {
      font-size: 24px;
      color: #333;
      margin: 0 0 8px 0;
      font-weight: 600;
    }
    
    p {
      color: #666;
      margin: 0;
      font-size: 14px;
    }
  }
  
  .login-form-content {
    h2 {
      text-align: center;
      margin-bottom: 30px;
      color: #333;
      font-weight: 500;
    }
    
    .el-form-item {
      margin-bottom: 20px;
    }
    
    .login-btn {
      width: 100%;
      height: 45px;
      font-size: 16px;
      font-weight: 500;
    }
  }
  
  .tips {
    margin-top: 20px;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 6px;
    text-align: center;
    
    p {
      margin: 2px 0;
      font-size: 12px;
      color: #666;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .login-container {
    padding: 16px;
  }
  
  .login-form {
    padding: 32px 24px;
    max-width: 100%;
    
    .logo-section {
      margin-bottom: 24px;
      
      .logo {
        width: 50px;
        height: 50px;
        margin-bottom: 12px;
      }
      
      h1 {
        font-size: 20px;
      }
      
      p {
        font-size: 13px;
      }
    }
    
    .login-form-content {
      h2 {
        font-size: 18px;
        margin-bottom: 24px;
      }
      
      .el-form-item {
        margin-bottom: 16px;
      }
      
      .login-btn {
        height: 42px;
        font-size: 15px;
      }
    }
    
    .tips {
      margin-top: 16px;
      padding: 12px;
      
      p {
        font-size: 11px;
      }
    }
  }
}

@media (max-width: 480px) {
  .login-container {
    padding: 12px;
  }
  
  .login-form {
    padding: 24px 16px;
    margin: 8px;
    
    .logo-section {
      margin-bottom: 20px;
      
      .logo {
        width: 45px;
        height: 45px;
        margin-bottom: 10px;
      }
      
      h1 {
        font-size: 18px;
      }
      
      p {
        font-size: 12px;
      }
    }
    
    .login-form-content {
      h2 {
        font-size: 16px;
        margin-bottom: 20px;
      }
      
      .el-form-item {
        margin-bottom: 14px;
      }
      
      .login-btn {
        height: 40px;
        font-size: 14px;
      }
    }
    
    .tips {
      margin-top: 14px;
      padding: 10px;
      
      p {
        font-size: 10px;
      }
    }
  }
}
</style>
