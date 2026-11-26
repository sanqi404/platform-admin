<template>
  <!-- 无权限的节点不进入 DOM（v-if 最小暴露），仅渲染允许访问的菜单 -->
  <template v-if="renderable">
    <el-sub-menu
      v-if="item.type === 'dir' && visibleChildren.length"
      :index="item.path || `dir-${item.id}`"
    >
      <template #title>
        <el-icon><component :is="item.icon || 'Folder'" /></el-icon>
        <span class="menu-title">{{ item.title }}</span>
      </template>
      <SidebarItem
        v-for="child in visibleChildren"
        :key="child.id"
        :item="child"
      />
    </el-sub-menu>

    <el-menu-item v-else-if="item.type !== 'dir'" :index="item.path">
      <el-icon><component :is="item.icon || 'Document'" /></el-icon>
      <template #title>
        <span class="menu-title">{{ item.title }}</span>
      </template>
    </el-menu-item>
  </template>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { MenuNode } from '@/types'
import { useUserStore } from '@/stores/user'

const props = defineProps<{
  item: MenuNode
}>()

const user = useUserStore()

/** 权限判定：按钮类与不可见菜单不参与侧栏渲染 */
const allowed = computed(() => user.canAccessMenu(props.item))

const renderable = computed(() => {
  const item = props.item
  if (item.type === 'button') return false
  if (item.visible === false) return false
  return allowed.value
})

const visibleChildren = computed(() =>
  (props.item.children || []).filter((c) => c.type !== 'button' && c.visible !== false),
)
</script>

<style scoped lang="scss">
.menu-title {
  margin-left: 2px;
}
</style>
