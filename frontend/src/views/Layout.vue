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
      <el-header style="background:#fff;border-bottom:1px solid #f0f0f0;display:flex;align-items:center;padding:0 24px;">
        <span style="font-weight:600;">{{ currentTitle }}</span>
      </el-header>
      <el-main style="background:#f5f7fa;padding:20px;"><router-view /></el-main>
    </el-container>
  </el-container>
</template>
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
const route = useRoute()
const menuItems = [
  { path: '/assets', title: '资产管理' },
  { path: '/scan', title: 'Nmap 扫描' },
  { path: '/iperf', title: '性能测试' },
  { path: '/broadband', title: '宽带管理' },
  { path: '/topology', title: '网络拓扑' },
  { path: '/diagnostics', title: '网络诊断' },
  { path: '/zabbix', title: 'Zabbix监控' },
]
const activeMenu = computed(() => route.path)
const currentTitle = computed(() => menuItems.find(m => route.path.startsWith(m.path))?.title ?? '')
</script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
</style>
