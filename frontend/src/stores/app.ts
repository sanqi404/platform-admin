import { defineStore } from 'pinia'

const COLLAPSE_KEY = 'rbac_sidebar_collapsed'

export const useAppStore = defineStore('app', {
  state: () => ({
    sidebarCollapsed: localStorage.getItem(COLLAPSE_KEY) === '1',
    pageLoading: false,
    /** keep-alive 缓存代次：变化后所有页面缓存失效重建（登出/切换账号时清理） */
    cacheEpoch: 0,
  }),

  actions: {
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
      localStorage.setItem(COLLAPSE_KEY, this.sidebarCollapsed ? '1' : '0')
    },

    /** 清空页面缓存：登出或其他需要强制重建页面的场景调用 */
    bumpCache() {
      this.cacheEpoch += 1
    },
  },
})
