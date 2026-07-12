<template>
  <div class="login-page">
    <!-- Background decorative dots (inspired by Plane) -->
    <div class="bg-dots"></div>
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">S</div>
        <h1 class="login-title">商机智能跟踪系统</h1>
        <p class="login-subtitle">Opportunity Intelligence Tracking</p>
      </div>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { authApi } from '../api'

const router = useRouter()
const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const res = await authApi.login(form)
    localStorage.setItem('token', res.data.access_token)
    // Decode JWT to get user info (payload is base64url encoded)
    try {
      const payload = JSON.parse(atob(res.data.access_token.split('.')[1]))
      localStorage.setItem('user_role', payload.role || '')
      localStorage.setItem('user_name', payload.real_name || '')
    } catch { /* ignore decode errors */ }
    router.push('/')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0747A6 0%, #0052CC 50%, #0065FF 100%);
  overflow: hidden;
}

/* Animated background dots pattern (inspired by Plane) */
.bg-dots {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(255,255,255,0.08) 1px, transparent 1px);
  background-size: 32px 32px;
  animation: fadeIn 0.6s ease-out;
}

.login-card {
  width: 400px;
  background: rgba(255,255,255,0.98);
  border-radius: 12px;
  box-shadow: 0 16px 48px rgba(7,71,166,0.25);
  padding: 40px;
  animation: fadeInUp 0.5s ease-out;
  position: relative;
  backdrop-filter: blur(20px);
}

.login-header { text-align: center; margin-bottom: 32px; }
.login-logo {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #0052CC, #0065FF);
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 16px;
  animation: scaleIn 0.3s ease-out 0.1s both;
}
.login-title {
  font-size: 20px;
  color: var(--ds-text);
  margin: 0 0 4px;
  font-weight: 600;
  animation: fadeInUp 0.3s ease-out 0.15s both;
}
.login-subtitle {
  font-size: 13px;
  color: var(--ds-text-subtle);
  margin: 0;
  animation: fadeInUp 0.3s ease-out 0.2s both;
}
.login-form {
  margin-top: 8px;
  animation: fadeInUp 0.3s ease-out 0.25s both;
}
.login-btn { width: 100%; }
.login-btn:not(.is-loading) {
  transition: all 0.2s ease;
}
.login-btn:not(.is-loading):hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,82,204,0.4);
}
</style>
