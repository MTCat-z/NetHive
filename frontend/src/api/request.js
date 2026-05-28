import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({ baseURL: '/api/v1', timeout: 30000 })

// 请求拦截器：自动带 JWT token
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：处理 401 跳转登录
request.interceptors.response.use(
  (r) => r.data,
  (e) => {
    const status = e.response?.status
    const detail = e.response?.data?.detail || e.message || '请求失败'
    if (status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // 避免重复提示
      if (!window.__auth_redirecting) {
        window.__auth_redirecting = true
        ElMessage.error('登录已过期，请重新登录')
        setTimeout(() => {
          window.location.href = '/login'
          window.__auth_redirecting = false
        }, 500)
      }
    } else {
      ElMessage.error(detail)
    }
    return Promise.reject(e)
  }
)

export default request
