import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    redirect: '/assets',
    children: [
      { path: 'assets', name: 'Assets', component: () => import('@/views/assets/AssetList.vue'), meta: { title: '资产管理' } },
      { path: 'scan',   name: 'Scan',   component: () => import('@/views/scan/ScanPage.vue'),   meta: { title: 'Nmap扫描' } },
      { path: 'iperf',  name: 'Iperf',  component: () => import('@/views/iperf/IperfPage.vue'), meta: { title: '性能测试' } },
      { path: 'broadband', name: 'Broadband', component: () => import('@/views/broadband/BroadbandPage.vue'), meta: { title: '宽带管理' } },
      { path: 'topology', name: 'Topology', component: () => import('@/views/topology/TopologyPage.vue'), meta: { title: '网络拓扑' } },
      { path: 'diagnostics', name: 'Diagnostics', component: () => import('@/views/diagnostics/DiagnosticsPage.vue'), meta: { title: '网络诊断' } },
      { path: 'zabbix', name: 'Zabbix', component: () => import('@/views/zabbix/ZabbixDashboard.vue'), meta: { title: 'Zabbix监控' } },
      { path: 'zabbix/hosts', name: 'ZabbixHosts', component: () => import('@/views/zabbix/ZabbixHosts.vue'), meta: { title: 'Zabbix主机' } },
      { path: 'zabbix/hosts/:id', name: 'ZabbixHostDetail', component: () => import('@/views/zabbix/ZabbixHostDetail.vue'), meta: { title: 'Zabbix主机详情' } },
    ],
  },
  {
    path: '/terminal/:assetId',
    name: 'Terminal',
    component: () => import('@/views/terminal/TerminalPage.vue'),
    meta: { title: '终端' },
  },
]

const router = createRouter({ history: createWebHistory(), routes })
export default router
