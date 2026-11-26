import { defineStore } from 'pinia'
import { authApi } from '@/api'
import { useAppStore } from '@/stores/app'
import type { MenuNode, Profile, UserInfo } from '@/types'
import { REFRESH_KEY, TOKEN_KEY } from '@/utils/request'

interface UserState {
  token: string
  user: UserInfo | null
  tenant: Record<string, unknown>
  roles: string[]
  perms: string[]
  menus: MenuNode[]
  dataScope: number
  loaded: boolean
}

/** 超管通配符，与后端 is_superuser 返回的 *:*:* 对齐 */
const WILDCARD = '*:*:*'

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: null,
    tenant: {},
    roles: [],
    perms: [],
    menus: [],
    dataScope: 4,
    loaded: false,
  }),

  getters: {
    isLogin: (s) => !!s.token,
    isSuperuser: (s) => s.perms.includes(WILDCARD),
    displayName: (s) => s.user?.nickname || s.user?.username || '',
    /** 单个权限判定：支持 *:*:* 超级通配与 模块:*:* 段位通配 */
    hasPerm: (s) => (code?: string | null): boolean => {
      if (!code) return true
      if (s.perms.includes(WILDCARD)) return true
      if (s.perms.includes(code)) return true
      const seg = code.split(':')
      for (let i = seg.length - 1; i > 0; i -= 1) {
        const pattern = [...seg.slice(0, i), '*'].join(':')
        if (s.perms.includes(pattern)) return true
      }
      return false
    },
    hasAnyPerm: (s) => (codes: string[]): boolean => {
      if (!codes.length) return true
      if (s.perms.includes(WILDCARD)) return true
      return codes.some((c) => s.perms.includes(c))
    },
    hasRole: (s) => (role: string | string[]): boolean => {
      const list = Array.isArray(role) ? role : [role]
      if (s.roles.includes('super_admin')) return true
      return list.some((r) => s.roles.includes(r))
    },
    /** 菜单可见性：无 perm_code 视为仅需登录，有则需权限命中 */
    canAccessMenu: (s) => (menu: MenuNode): boolean => {
      if (!menu.perm_code) return true
      if (s.perms.includes(WILDCARD)) return true
      return s.perms.includes(menu.perm_code)
    },
  },

  actions: {
    async login(payload: { username: string; password: string; tenant_code: string }) {
      const data = await authApi.login(payload)
      this.token = data.access_token
      localStorage.setItem(TOKEN_KEY, data.access_token)
      localStorage.setItem(REFRESH_KEY, data.refresh_token)
      await this.fetchProfile()
    },

    async fetchProfile(): Promise<Profile> {
      const profile = await authApi.profile()
      this.user = profile.user
      this.tenant = profile.tenant
      this.roles = profile.roles
      this.perms = profile.permissions
      this.menus = profile.menus
      this.dataScope = profile.data_scope
      this.loaded = true
      return profile
    },

    async logout() {
      try {
        await authApi.logout()
      } catch {
        // 登出失败不阻塞本地清理
      }
      this.clear()
    },

    clear() {
      // 先让页面缓存整体失效，避免换账号后残留上一账号的页面实例与数据
      useAppStore().bumpCache()
      this.token = ''
      this.user = null
      this.tenant = {}
      this.roles = []
      this.perms = []
      this.menus = []
      this.dataScope = 4
      this.loaded = false
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(REFRESH_KEY)
    },
  },
})
