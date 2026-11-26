import { request } from '@/utils/request'
import type {
  LoginLogItem, MenuNode, OperationLogItem, PageResult, PermissionItem, Profile,
  RoleGrants, RoleItem, TenantItem, TokenPayload, UserInfo,
} from '@/types'

/* ------------------------------ 认证 ------------------------------ */
export const authApi = {
  login: (data: { username: string; password: string; tenant_code: string }) =>
    request<TokenPayload>({ url: '/auth/login', method: 'post', data }),
  profile: () => request<Profile>({ url: '/auth/profile', method: 'get' }),
  logout: () => request<null>({ url: '/auth/logout', method: 'post' }),
  changePassword: (data: { old_password: string; new_password: string }) =>
    request<null>({ url: '/auth/password', method: 'put', data }),
}

/* ------------------------------ 用户 ------------------------------ */
export interface UserQuery {
  page?: number
  page_size?: number
  keyword?: string
  status?: number
}

export interface UserPayload {
  username?: string
  password?: string
  nickname?: string
  email?: string
  phone?: string
  dept_id?: number | null
  status?: number
  role_ids?: number[]
}

export const userApi = {
  list: (params: UserQuery) => request<PageResult<UserInfo>>({ url: '/users', method: 'get', params }),
  create: (data: UserPayload) => request<UserInfo>({ url: '/users', method: 'post', data }),
  update: (id: number, data: UserPayload) => request<UserInfo>({ url: `/users/${id}`, method: 'put', data }),
  remove: (id: number) => request<null>({ url: `/users/${id}`, method: 'delete' }),
  resetPassword: (id: number, password: string) =>
    request<null>({ url: `/users/${id}/password`, method: 'put', data: { password } }),
}

/* ------------------------------ 角色 ------------------------------ */
export const roleApi = {
  list: () => request<RoleItem[]>({ url: '/roles', method: 'get' }),
  create: (data: Partial<RoleItem>) => request<RoleItem>({ url: '/roles', method: 'post', data }),
  update: (id: number, data: Partial<RoleItem>) => request<RoleItem>({ url: `/roles/${id}`, method: 'put', data }),
  remove: (id: number) => request<null>({ url: `/roles/${id}`, method: 'delete' }),
  grants: (id: number) => request<RoleGrants>({ url: `/roles/${id}/grants`, method: 'get' }),
  saveGrants: (id: number, data: RoleGrants) =>
    request<null>({ url: `/roles/${id}/grants`, method: 'put', data }),
}

/* ------------------------------ 菜单 / 权限点 ------------------------------ */
export const menuApi = {
  tree: () => request<MenuNode[]>({ url: '/menus/tree', method: 'get' }),
  flat: () => request<Record<string, unknown>[]>({ url: '/menus', method: 'get' }),
  create: (data: Record<string, unknown>) => request<Record<string, unknown>>({ url: '/menus', method: 'post', data }),
  update: (id: number, data: Record<string, unknown>) =>
    request<null>({ url: `/menus/${id}`, method: 'put', data }),
  remove: (id: number) => request<null>({ url: `/menus/${id}`, method: 'delete' }),
  permissions: () => request<PermissionItem[]>({ url: '/permissions', method: 'get' }),
}

/* ------------------------------ 租户 ------------------------------ */
export const tenantApi = {
  list: (params: { page?: number; page_size?: number; keyword?: string }) =>
    request<PageResult<TenantItem>>({ url: '/tenants', method: 'get', params }),
  create: (data: Partial<TenantItem>) => request<TenantItem>({ url: '/tenants', method: 'post', data }),
  update: (id: number, data: Partial<TenantItem>) =>
    request<TenantItem>({ url: `/tenants/${id}`, method: 'put', data }),
  remove: (id: number) => request<null>({ url: `/tenants/${id}`, method: 'delete' }),
}

/* ------------------------------ 日志审计 ------------------------------ */
export interface LoginLogQuery {
  page?: number
  page_size?: number
  username?: string
  status?: number
  login_type?: string
  ip?: string
  start_at?: string
  end_at?: string
}

export interface OperationLogQuery {
  page?: number
  page_size?: number
  username?: string
  module?: string
  action?: string
  success?: boolean
  keyword?: string
  start_at?: string
  end_at?: string
}

export const logApi = {
  loginList: (params: LoginLogQuery) =>
    request<PageResult<LoginLogItem>>({ url: '/logs/login', method: 'get', params }),
  operationList: (params: OperationLogQuery) =>
    request<PageResult<OperationLogItem>>({ url: '/logs/operation', method: 'get', params }),
  operationDetail: (id: number) =>
    request<OperationLogItem>({ url: `/logs/operation/${id}`, method: 'get' }),
  removeLogin: (id: number) =>
    request<null>({ url: `/logs/login/${id}`, method: 'delete' }),
  removeOperation: (id: number) =>
    request<null>({ url: `/logs/operation/${id}`, method: 'delete' }),
  cleanLogin: (before: string) =>
    request<{ deleted: number }>({ url: '/logs/login/clean', method: 'post', data: { before } }),
  cleanOperation: (before: string) =>
    request<{ deleted: number }>({ url: '/logs/operation/clean', method: 'post', data: { before } }),
}
