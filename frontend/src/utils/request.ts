import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiResponse } from '@/types'

export const TOKEN_KEY = 'rbac_access_token'
export const REFRESH_KEY = 'rbac_refresh_token'

const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let redirecting = false

/** 401 统一跳登录，避免多处重复处理 */
function toLogin(): void {
  if (redirecting) return
  redirecting = true
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
  const back = encodeURIComponent(location.pathname + location.search)
  location.replace(`/login?redirect=${back}`)
}

http.interceptors.response.use(
  (resp) => {
    const body = resp.data as ApiResponse
    if (body && typeof body.code === 'number' && body.code !== 0) {
      ElMessage.error(body.msg || '请求失败')
      return Promise.reject(new Error(body.msg || '请求失败'))
    }
    return resp
  },
  (error) => {
    const status = error?.response?.status
    const msg = error?.response?.data?.msg as string | undefined
    if (status === 401) {
      ElMessage.error(msg || '登录状态已失效，请重新登录')
      toLogin()
      return Promise.reject(error)
    }
    if (status === 403) {
      ElMessage.error(msg || '无操作权限')
      return Promise.reject(error)
    }
    ElMessage.error(msg || error.message || '网络异常')
    return Promise.reject(error)
  },
)

/** 统一解包 data */
export async function request<T>(
  config: Parameters<AxiosInstance['request']>[0],
): Promise<T> {
  const resp = await http.request<ApiResponse<T>>(config)
  return resp.data.data
}

export default http
