<template>
  <div id="app">
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
            <el-menu-item index="/website">
              <el-icon><Monitor /></el-icon>
              <span>网站</span>
            </el-menu-item>
            <el-menu-item index="/data">
              <el-icon><DataAnalysis /></el-icon>
              <span>数据</span>
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
              <div v-if="userStore.isLoggedIn" class="user-info">
                <el-dropdown @command="handleCommand">
                  <div class="user-dropdown">
                    <el-avatar :size="32" class="user-avatar">
                      {{ userStore.user?.username?.charAt(0)?.toUpperCase() }}
                    </el-avatar>
                    <span class="username">{{ userStore.user?.username }}</span>
                    <el-icon class="el-icon--right"><arrow-down /></el-icon>
                  </div>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="profile">
                        <el-icon><User /></el-icon>
                        个人资料
                      </el-dropdown-item>
                      <el-dropdown-item v-if="userStore.isAdmin" command="users">
                        <el-icon><Setting /></el-icon>
                        用户管理
                      </el-dropdown-item>
                      <el-dropdown-item divided command="logout">
                        <el-icon><SwitchButton /></el-icon>
                        退出登录
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>
        </el-header>
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { 
  HomeFilled, User, Monitor, DataAnalysis, 
  Fold, Picture, Upload, ArrowDown, Setting, SwitchButton
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

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

// 处理下拉菜单命令
const handleCommand = async (command) => {
  switch (command) {
    case 'profile':
      // TODO: 显示个人资料弹窗
      ElMessage.info('个人资料功能待完善')
      break
    case 'users':
      // TODO: 跳转到用户管理页面
      ElMessage.info('用户管理功能待完善')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm(
          '确定要退出登录吗？',
          '提示',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning',
          }
        )
        await userStore.logout()
        ElMessage.success('已退出登录')
        router.push('/login')
      } catch (error) {
        // 用户取消操作
      }
      break
  }
}
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
      .user-info {
        .user-dropdown {
          display: flex;
          align-items: center;
          cursor: pointer;
          padding: 8px 12px;
          border-radius: 6px;
          transition: background-color 0.3s;
          
          &:hover {
            background-color: #f5f5f5;
          }
          
          .user-avatar {
            margin-right: 8px;
            background-color: $primary-color;
            color: white;
            font-weight: 600;
          }
          
          .username {
            margin-right: 8px;
            color: $text-regular;
            font-size: 14px;
          }
          
          .el-icon {
            font-size: 12px;
            color: $text-secondary;
          }
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
