<template>
  <el-container style="height: 100vh;">
    <el-aside width="220px" style="background: #001529;">
      <div style="height:64px;display:flex;align-items:center;padding:0 20px;color:#fff;font-size:15px;font-weight:600;border-bottom:1px solid #ffffff1a">内网运维平台</div>
      <el-menu :default-active="activeMenu" router background-color="#001529" text-color="#ffffffa6" active-text-color="#ffffff">
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="background:#fff;border-bottom:1px solid #f0f0f0;display:flex;align-items:center;justify-content:space-between;padding:0 24px;">
        <span style="font-weight:600;">{{ currentTitle }}</span>
        <div style="display:flex;align-items:center;gap:12px">
          <el-tag size="small" :type="authStore.isAdmin ? 'danger' : ''">{{ authStore.isAdmin ? '管理员' : '用户' }}</el-tag>
          <span style="font-size:14px;color:#333">{{ authStore.username }}</span>
          <el-button size="small" text @click="changePwdVisible = true">修改密码</el-button>
          <el-button size="small" text type="danger" @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main style="background:#f5f7fa;padding:20px;"><router-view /></el-main>
    </el-container>

    <!-- 修改密码对话框 -->
    <el-dialog v-model="changePwdVisible" title="修改密码" width="400px" :close-on-click-modal="!authStore.mustChangePassword" :close-on-press-escape="!authStore.mustChangePassword" :show-close="!authStore.mustChangePassword">
      <el-alert v-if="authStore.mustChangePassword" type="warning" :closable="false" style="margin-bottom:16px" title="首次登录请修改默认密码" />
      <el-form :model="pwdForm" label-width="80px">
        <el-form-item label="原密码"><el-input v-model="pwdForm.oldPassword" type="password" show-password /></el-form-item>
        <el-form-item label="新密码"><el-input v-model="pwdForm.newPassword" type="password" placeholder="至少 6 位" show-password /></el-form-item>
        <el-form-item label="确认密码"><el-input v-model="pwdForm.confirmPassword" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer>
        <el-button v-if="!authStore.mustChangePassword" @click="changePwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdSubmitting" @click="handleChangePassword">确定</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>
<script setup>
import { computed, ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const allMenuItems = [
  { path: '/assets', title: '资产管理', admin: false },
  { path: '/scan', title: 'Nmap 扫描', admin: false },
  { path: '/iperf', title: '性能测试', admin: false },
  { path: '/broadband', title: '宽带管理', admin: false },
  { path: '/topology', title: '网络拓扑', admin: false },
  { path: '/diagnostics', title: '网络诊断', admin: false },
  { path: '/zabbix', title: 'Zabbix监控', admin: false },
  { path: '/users', title: '用户管理', admin: true },
  { path: '/audit', title: '审计日志', admin: true },
]

const menuItems = computed(() => allMenuItems.filter(m => !m.admin || authStore.isAdmin))
const activeMenu = computed(() => route.path)
const currentTitle = computed(() => allMenuItems.find(m => route.path.startsWith(m.path))?.title ?? '')

// 修改密码
const changePwdVisible = ref(false)
const pwdSubmitting = ref(false)
const pwdForm = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })

async function handleChangePassword() {
  if (!pwdForm.oldPassword) return ElMessage.warning('请输入原密码')
  if (!pwdForm.newPassword || pwdForm.newPassword.length < 6) return ElMessage.warning('新密码至少 6 位')
  if (pwdForm.newPassword !== pwdForm.confirmPassword) return ElMessage.warning('两次密码不一致')
  pwdSubmitting.value = true
  try {
    await authStore.changePassword(pwdForm.oldPassword, pwdForm.newPassword)
    ElMessage.success('密码修改成功')
    changePwdVisible.value = false
    Object.assign(pwdForm, { oldPassword: '', newPassword: '', confirmPassword: '' })
  } catch (e) { /* handled by interceptor */ }
  finally { pwdSubmitting.value = false }
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

// 首次登录强制改密
onMounted(() => {
  if (authStore.mustChangePassword) {
    changePwdVisible.value = true
  }
})
</script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
</style>
