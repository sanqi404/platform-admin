/** 后端统一响应与领域类型 */

export interface ApiResponse<T = unknown> {
  code: number
  msg: string
  data: T
}

export interface PageResult<T> {
  total: number
  items: T[]
}

export interface TokenPayload {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface RoleBrief {
  id: number
  code: string
  name: string
}

export interface UserInfo {
  id: number
  tenant_id: number
  dept_id: number | null
  username: string
  nickname: string
  email: string | null
  phone: string | null
  avatar: string | null
  status: number
  is_superuser: boolean
  last_login_at: string | null
  roles?: RoleBrief[]
}

export interface MenuNode {
  id: number
  parent_id: number
  title: string
  name: string
  path: string
  component: string
  icon: string | null
  type: 'dir' | 'menu' | 'button'
  perm_code: string | null
  sort: number
  visible: boolean
  keep_alive: boolean
  is_ext: boolean
  children: MenuNode[]
}

export interface PermissionItem {
  id: number
  code: string
  name: string
  module: string
  group: string
  sort: number
}

export interface RoleItem {
  id: number
  tenant_id: number
  code: string
  name: string
  data_scope: number
  custom_dept_ids: number[]
  status: number
  is_system: boolean
  is_all_perm: boolean
  sort: number
  remark: string | null
}

export interface RoleGrants {
  permission_ids: number[]
  menu_ids: number[]
  data_scope?: number
  is_all_perm?: boolean
}

export interface TenantItem {
  id: number
  code: string
  name: string
  contact: string | null
  phone: string | null
  status: number
  expire_at: string | null
  remark: string | null
}

export interface Profile {
  user: UserInfo
  tenant: Record<string, unknown>
  roles: string[]
  permissions: string[]
  menus: MenuNode[]
  data_scope: number
}

/** 日志审计 */
export interface LoginLogItem {
  id: number
  tenant_id: number
  user_id: number | null
  username: string
  login_type: string
  status: number
  fail_reason: string | null
  ip: string
  ip_region: string | null
  os: string | null
  browser: string | null
  device: string | null
  user_agent: string | null
  login_at: string | null
}

export interface OperationLogItem {
  id: number
  tenant_id: number
  user_id: number | null
  username: string | null
  module: string
  action: string
  action_label: string
  method: string
  path: string
  query: string | null
  target: string | null
  params: string | null
  status_code: number
  success: boolean
  error_msg: string | null
  duration_ms: number
  ip: string
  ip_region: string | null
  os: string | null
  browser: string | null
  device: string | null
  user_agent: string | null
  created_at: string | null
}

/** 数据范围枚举，与后端 Role.data_scope 对齐 */
export const DATA_SCOPE_OPTIONS = [
  { value: 1, label: '全部数据' },
  { value: 2, label: '本部门数据' },
  { value: 3, label: '本部门及以下' },
  { value: 4, label: '仅本人数据' },
  { value: 5, label: '自定义部门' },
] as const

/** 界面可选的数据范围：2/3/5 依赖部门树，部门管理未启用前只开放「全部 / 仅本人」 */
// 平台侧默认并统一使用「全部数据」，不再提供「仅本人」等行级裁剪档位
export const DATA_SCOPE_SELECTABLE = DATA_SCOPE_OPTIONS.filter((o) => o.value === 1)
