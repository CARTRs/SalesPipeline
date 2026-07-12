<template>
  <el-container class="main-layout">
    <!-- Jira 风格深色侧边栏 -->
    <el-aside :width="sidebarWidth" class="sidebar">
      <div class="sidebar-header">
        <div class="logo-icon">S</div>
        <span class="logo-text" v-show="!collapsed">商机跟踪</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        background-color="#0747A6"
        text-color="#FFFFFF"
        active-text-color="#FFFFFF"
        :unique-opened="true"
        router
      >
        <el-menu-item index="/opportunities">
          <el-icon><List /></el-icon>
          <template #title>商机列表</template>
        </el-menu-item>
        <el-menu-item index="/opportunities/create">
          <el-icon><Plus /></el-icon>
          <template #title>新建商机</template>
        </el-menu-item>
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>数据看板</template>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>系统设置</template>
        </el-menu-item>
        <el-menu-item index="/logs">
          <el-icon><Document /></el-icon>
          <template #title>操作日志</template>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-footer" :class="{ collapsed }" @click="collapsed = !collapsed">
        <!-- 展开/收起图标（阿里风格内联SVG） -->
        <svg class="collapse-icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path v-if="!collapsed" d="M10 3L5 8L10 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          <path v-else d="M6 3L11 8L6 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span class="collapse-text" v-show="!collapsed">收起侧栏</span>
      </div>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="main-container">
      <!-- 顶栏 -->
      <header class="top-bar">
        <div class="top-bar-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="pageTitle">{{ pageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="top-bar-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="28" style="background-color: #0052CC; vertical-align: middle;">
                {{ userName?.charAt(0) || 'U' }}
              </el-avatar>
              <span class="user-name">{{ userName || '用户' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人设置</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="page-content">
        <router-view />
      </main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { List, Plus, DataAnalysis, Setting, Document, ArrowDown } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const collapsed = ref(false)
const sidebarWidth = computed(() => (collapsed.value ? '64px' : '240px'))

const pageTitle = computed(() => {
  const map = {
    'OpportunityList': '商机列表',
    'OpportunityCreate': '新建商机',
    'OpportunityEdit': '编辑商机',
    'OpportunityDetail': '商机详情',
    'Dashboard': '数据看板',
  }
  return map[route.name] || ''
})

const activeMenu = computed(() => route.path)

const userName = localStorage.getItem('real_name') || ''

function handleCommand(command) {
  if (command === 'logout') {
    localStorage.removeItem('token')
    localStorage.removeItem('real_name')
    router.push('/login')
  }
}
</script>

<style scoped>
.main-layout { height: 100vh; }
.sidebar {
  background-color: #0747A6;
  display: flex;
  flex-direction: column;
  transition: width 0.2s;
  overflow: hidden;
}
.sidebar-header {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 10px;
  border-bottom: 1px solid rgba(255,255,255,0.12);
}
.logo-icon {
  width: 32px;
  height: 32px;
  background: rgba(255,255,255,0.2);
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
  color: #fff;
  flex-shrink: 0;
}
.logo-text { color: #fff; font-size: 16px; font-weight: 600; white-space: nowrap; }
.sidebar .el-menu { border-right: none; }
.sidebar .el-menu .el-menu-item {
  transition: all 0.15s ease;
  border-left: 3px solid transparent;
}
.sidebar .el-menu .el-menu-item.is-active {
  border-left-color: rgba(255,255,255,0.7);
  background: linear-gradient(90deg, rgba(255,255,255,0.12) 0%, transparent 100%);
}
.sidebar .el-menu .el-menu-item:hover {
  background: rgba(255,255,255,0.1) !important;
}
.sidebar-footer {
  margin-top: auto;
  padding: 10px 16px;
  border-top: 1px solid rgba(255,255,255,0.12);
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: rgba(255,255,255,0.7);
  transition: all 0.15s ease;
  user-select: none;
}
.sidebar-footer:hover {
  color: #fff;
  background: rgba(255,255,255,0.08);
}
.sidebar-footer.collapsed {
  justify-content: center;
  padding: 10px 0;
}
.collapse-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
.collapse-text {
  font-size: 13px;
  white-space: nowrap;
}
.main-container { display: flex; flex-direction: column; }
.top-bar {
  height: 56px;
  background: #fff;
  border-bottom: 1px solid var(--ds-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}
.top-bar-left { display: flex; align-items: center; gap: 16px; }
.top-bar-right { display: flex; align-items: center; }
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 3px;
  transition: background 0.15s;
}
.user-info:hover { background: #EBECF0; }
.user-name { font-size: 14px; color: var(--ds-text); }
.page-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  background-color: var(--ds-background-default);
}
</style>
