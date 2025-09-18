<template>
  <div id="app">
    <!-- 登录页面：无侧边栏布局 -->
    <template v-if="$route.path === '/login'">
      <router-view />
    </template>
    
    <!-- 主应用：带侧边栏布局 -->
    <template v-else>
      <el-container>
        <el-aside :width="isCollapse ? '64px' : '200px'">
          <div class="sidebar">
            <div class="logo">
              <img v-show="isCollapse" src="/vite.svg" alt="Logo" class="logo-img">
              <h2 v-show="!isCollapse">自媒体自动化运营系统</h2>
            </div>
            <el-menu
              :router="true"
              :default-active="activeMenu"
              :collapse="isCollapse"
              class="sidebar-menu"
              background-color="#001529"
              text-color="#fff"
              active-text-color="#409EFF"
            >
              <el-menu-item index="/">
                <el-icon><HomeFilled /></el-icon>
                <span>首页</span>
              </el-menu-item>
              <el-menu-item index="/account-management">
                <el-icon><User /></el-icon>
                <span>账号管理</span>
              </el-menu-item>
              <el-menu-item index="/material-management">
                <el-icon><Picture /></el-icon>
                <span>素材管理</span>
              </el-menu-item>
              <el-menu-item index="/publish-center">
                <el-icon><Upload /></el-icon>
                <span>发布中心</span>
              </el-menu-item>
              <el-menu-item index="/about">
                <el-icon><Monitor /></el-icon>
                <span>关于</span>
              </el-menu-item>
            </el-menu>
          </div>
        </el-aside>
        <el-container>
          <el-header>
            <div class="header-content">
              <div class="header-left">
                <el-icon class="toggle-sidebar" @click="toggleSidebar"><Fold /></el-icon>
              </div>
              <div class="header-right">
                <el-dropdown v-if="authStore.isLoggedIn" @command="handleCommand">
                  <div class="user-dropdown">
                    <el-icon><User /></el-icon>
                    <span class="username">{{ authStore.userInfo.username }}</span>
                    <el-icon><CaretBottom /></el-icon>
                  </div>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="profile">
                        <el-icon><User /></el-icon>
                        个人信息
                      </el-dropdown-item>
                      <el-dropdown-item command="logout" divided>
                        <el-icon><SwitchButton /></el-icon>
                        退出登录
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </el-header>
          <el-main>
            <router-view />
          </el-main>
        </el-container>
      </el-container>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { 
  HomeFilled, User, Monitor, DataAnalysis, 
  Fold, Picture, Upload, CaretBottom, SwitchButton
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// 当前激活的菜单项
const activeMenu = computed(() => {
  return route.path
})

// 侧边栏折叠状态
const isCollapse = ref(false)

// 切换侧边栏折叠状态
const toggleSidebar = () => {
  isCollapse.value = !isCollapse.value
}

// 处理用户下拉菜单命令
const handleCommand = async (command) => {
  switch (command) {
    case 'profile':
      // 暂时显示用户信息
      ElMessage.info(`当前用户：${authStore.userInfo.username}`)
      break
    case 'logout':
      try {
        await ElMessageBox.confirm(
          '确定要退出登录吗？',
          '退出确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        authStore.logout()
        ElMessage.success('已退出登录')
      } catch {
        // 用户取消
      }
      break
  }
}

// 组件挂载时初始化认证状态
onMounted(() => {
  authStore.initAuth()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

#app {
  min-height: 100vh;
}

.el-container {
  height: 100vh;
}

.el-aside {
  background-color: #001529;
  color: #fff;
  height: 100vh;
  overflow: hidden;
  transition: width 0.3s;
  
  .sidebar {
    display: flex;
    flex-direction: column;
    height: 100%;
    
    .logo {
      height: 60px;
      padding: 0 16px;
      display: flex;
      align-items: center;
      background-color: #002140;
      overflow: hidden;
      
      .logo-img {
        width: 32px;
        height: 32px;
        margin-right: 12px;
      }
      
      h2 {
        color: #fff;
        font-size: 16px;
        font-weight: 600;
        white-space: nowrap;
        margin: 0;
      }
    }
    
    .sidebar-menu {
      border-right: none;
      flex: 1;
      
      .el-menu-item {
        display: flex;
        align-items: center;
        
        .el-icon {
          margin-right: 10px;
          font-size: 18px;
        }
      }
    }
  }
}

.el-header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  padding: 0;
  height: 60px;
  
  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 100%;
    padding: 0 16px;
    
    .header-left {
      .toggle-sidebar {
        font-size: 20px;
        cursor: pointer;
        color: $text-regular;
        
        &:hover {
          color: $primary-color;
        }
      }
    }
    
    .header-right {
      .user-dropdown {
        display: flex;
        align-items: center;
        cursor: pointer;
        
        .username {
          margin: 0 8px;
          color: $text-regular;
        }
        
        .el-icon {
          font-size: 12px;
          color: $text-secondary;
        }
      }
    }
  }
}

.el-main {
  background-color: $bg-color-page;
  padding: 20px;
  overflow-y: auto;
}
</style>
