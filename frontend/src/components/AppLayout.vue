<template>
  <div class="layout" :class="{ 'is-collapsed': app.sidebarCollapsed }">
    <!-- ================= 侧边栏 ================= -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand__logo">{{ brand.logoText }}</div>
        <transition name="fade">
          <div v-show="!app.sidebarCollapsed" class="brand__text">
            <strong>{{ brand.title }}</strong>
            <span>{{ brand.subtitle }}</span>
          </div>
        </transition>
      </div>

      <el-scrollbar class="sidebar__scroll">
        <el-menu
          :default-active="activeMenu"
          :collapse="app.sidebarCollapsed"
          :collapse-transition="false"
          router
          unique-opened
          background-color="transparent"
          text-color="#cbd5e1"
          active-text-color="#ffffff"
        >
          <SidebarItem
            v-for="menu in user.menus"
            :key="menu.id"
            :item="menu"
          />
        </el-menu>

        <div v-if="!user.menus.length" class="sidebar__empty">
          暂无可访问菜单
        </div>
      </el-scrollbar>
    </aside>

    <!-- ================= 主区 ================= -->
    <div class="main">
      <header class="topbar">
        <el-button text class="topbar__icon" @click="app.toggleSidebar()">
          <el-icon :size="18">
            <component :is="app.sidebarCollapsed ? 'Expand' : 'Fold'" />
          </el-icon>
        </el-button>

        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ path: brand.homePath }">首页</el-breadcrumb-item>
          <el-breadcrumb-item v-if="parentTitle">{{ parentTitle }}</el-breadcrumb-item>
          <el-breadcrumb-item>{{ route.meta.title }}</el-breadcrumb-item>
        </el-breadcrumb>

        <div class="toolbar__spacer" />

        <el-dropdown trigger="click" @command="onCommand">
          <div class="user-chip">
            <el-avatar :size="30" class="user-chip__avatar">
              {{ (user.displayName || 'U').slice(0, 1) }}
            </el-avatar>
            <div class="user-chip__meta">
              <span class="user-chip__name">{{ user.displayName }}</span>
              <span class="user-chip__role">{{ user.roles.join(' / ') || '未分配角色' }}</span>
            </div>
            <el-icon><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人中心</el-dropdown-item>
              <el-dropdown-item command="password">修改密码</el-dropdown-item>
              <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>

      <el-scrollbar class="content">
        <router-view v-slot="{ Component, route: r }">
          <keep-alive :max="12">
            <component :is="Component" :key="`${app.cacheEpoch}-${r.path}`" />
          </keep-alive>
        </router-view>
      </el-scrollbar>
    </div>

    <PasswordDialog v-model="pwdVisible" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import SidebarItem from './SidebarItem.vue'
import PasswordDialog from './PasswordDialog.vue'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import { APP_BRAND } from '@/config/app'

const app = useAppStore()
const user = useUserStore()
const brand = APP_BRAND
const route = useRoute()
const router = useRouter()
const pwdVisible = ref(false)

const activeMenu = computed(() => route.path)

/** 面包屑父级：按菜单树反查 */
const parentTitle = computed(() => {
  for (const root of user.menus) {
    if ((root.children || []).some((c) => c.path === route.path)) return root.title
  }
  return ''
})

async function onCommand(cmd: string) {
  if (cmd === 'profile') {
    router.push('/profile')
  } else if (cmd === 'password') {
    pwdVisible.value = true
  } else if (cmd === 'logout') {
    await ElMessageBox.confirm('确认退出当前账号？', '退出登录', {
      type: 'warning',
      confirmButtonText: '退出',
      cancelButtonText: '取消',
    })
    await user.logout()
    router.replace('/login')
  }
}
</script>

<style scoped lang="scss">
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* ---------------- 侧边栏 ---------------- */
.sidebar {
  position: relative;
  display: flex;
  flex-direction: column;
  width: var(--sidebar-w);
  flex: 0 0 var(--sidebar-w);
  background:
    radial-gradient(1200px 300px at -10% -10%, rgba(99, 102, 241, 0.35), transparent 60%),
    linear-gradient(180deg, #111827 0%, #0b1220 100%);
  transition: width 0.22s ease, flex-basis 0.22s ease;
}

.is-collapsed .sidebar {
  width: var(--sidebar-w-collapsed);
  flex: 0 0 var(--sidebar-w-collapsed);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: var(--header-h);
  padding: 0 16px;
  overflow: hidden;
}

.brand__logo {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--brand-500), #8b5cf6);
  color: #fff;
  font-weight: 700;
  box-shadow: 0 6px 16px -6px rgba(99, 102, 241, 0.9);
}

.brand__text {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
  white-space: nowrap;
}

.brand__text strong {
  color: #f8fafc;
  font-size: 14px;
  letter-spacing: 0.02em;
}

.brand__text span {
  color: #7c8aa5;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.sidebar__scroll {
  flex: 1;
  min-height: 0;
  padding: 8px;
}

.sidebar__empty {
  padding: 24px 12px;
  color: #64748b;
  font-size: 12.5px;
  text-align: center;
}

:deep(.el-menu) {
  border-right: none;
}

:deep(.el-menu--collapse) {
  width: 100%;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  height: 42px;
  margin: 2px 0;
  border-radius: 10px;
  font-size: 13.5px;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  background: rgba(148, 163, 184, 0.12) !important;
}

:deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.9), rgba(139, 92, 246, 0.55)) !important;
  box-shadow: 0 10px 22px -14px rgba(99, 102, 241, 1);
}

:deep(.el-menu-item.is-disabled) {
  opacity: 0.45;
}

/* ---------------- 主区 ---------------- */
.main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  height: var(--header-h);
  padding: 0 20px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid #e9edf5;
}

.topbar__icon {
  color: var(--ink-500);
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px 4px 6px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.user-chip:hover {
  background: #f1f5f9;
}

.user-chip__avatar {
  background: linear-gradient(135deg, var(--brand-500), #8b5cf6);
  color: #fff;
  font-size: 13px;
}

.user-chip__meta {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.user-chip__name {
  font-size: 13px;
  font-weight: 600;
}

.user-chip__role {
  color: var(--ink-500);
  font-size: 11px;
}

.content {
  flex: 1;
  min-height: 0;
  background: var(--bg-page);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
