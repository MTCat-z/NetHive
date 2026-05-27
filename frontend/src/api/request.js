import axios from 'axios'
import { ElMessage } from 'element-plus'
const request = axios.create({ baseURL: '/api/v1', timeout: 30000 })
request.interceptors.response.use(
  (r) => r.data,
  (e) => { ElMessage.error(e.response?.data?.detail || e.message || '请求失败'); return Promise.reject(e) }
)
export default request
