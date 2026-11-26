<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-head__title">工作台</h1>
        <p class="page-head__desc">
          当前租户 <strong>{{ tenantName }}</strong> · 登录身份
          <strong>{{ user.displayName }}</strong> · 数据范围
          <el-tag size="small" type="primary" effect="light">{{ scopeLabel }}</el-tag>
        </p>
      </div>
      <el-button :icon="Refresh" plain @click="load">刷新</el-button>
    </div>

    <!-- 统计 -->
    <div class="stat-grid">
      <div v-for="s in stats" :key="s.label" class="stat">
        <div class="stat__label">{{ s.label }}</div>
        <div class="stat__value">{{ s.value }}</div>
        <div class="stat__hint">{{ s.hint }}</div>
      </div>
    </div>

    <div class="grid-2">
      <!-- 角色与身份 -->
      <div class="card card--pad">
        <div class="section-head">
          <h3>身份与角色</h3>
          <span class="text-muted">多角色权限叠加</span>
        </div>
        <div class="role-list">
          <el-tag
            v-for="r in user.roles"
            :key="r"
            :type="r === 'super_admin' ? 'danger' : 'info'"
            effect="light"
            size="large"
          >
            {{ r }}
          </el-tag>
          <span v-if="!user.roles.length" class="text-muted">未分配角色</span>
        </div>
        <el-divider />
        <div class="kv">
          <span>租户编码</span><span class="mono">{{ user.tenant?.code ?? '-' }}</span>
          <span>用户 ID</span><span class="mono">{{ user.user?.id }}</span>
          <span>超级管理员</span>
          <span>{{ user.isSuperuser ? '是' : '否' }}</span>
          <span>上次登录</span>
          <span class="mono">{{ user.user?.last_login_at || '-' }}</span>
        </div>
      </div>

      <!-- 权限点 -->
      <div class="card card--pad">
        <div class="section-head">
          <h3>已授予权限点</h3>
          <span class="text-muted">共 {{ user.perms.length }} 项</span>
        </div>
        <div class="perm-groups">
          <div v-for="(codes, mod) in permGroups" :key="mod" class="perm-group">
            <div class="perm-group__title">{{ mod }}</div>
            <div class="perm-group__codes">
              <el-tag v-for="c in codes" :key="c" size="small" effect="plain" class="mono">{{ c }}</el-tag>
            </div>
          </div>
          <el-empty v-if="!user.perms.length" description="无权限点" :image-size="70" />
        </div>
      </div>
    </div>

    <!-- 菜单权限 -->
    <div class="card card--pad">
      <div class="section-head">
        <h3>菜单授权结果</h3>
        <span class="text-muted">按当前账号的菜单权限过滤</span>
      </div>
      <el-table :data="menuRows" size="small" row-key="id" border default-expand-all>
        <el-table-column prop="title" label="菜单" min-width="200" />
        <el-table-column prop="path" label="路由" min-width="160">
          <template #default="{ row }"><span class="mono">{{ row.path || '-' }}</span></template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.type === 'dir' ? 'warning' : 'success'" effect="light">
              {{ row.type === 'dir' ? '目录' : row.type === 'menu' ? '菜单' : '按钮' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="perm_code" label="权限码" min-width="180">
          <template #default="{ row }">
            <span class="mono">{{ row.perm_code || '—' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { userApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { DATA_SCOPE_OPTIONS, type MenuNode } from '@/types'

const user = useUserStore()
const userTotal = ref<number | string>('—')

const tenantName = computed(
  () => (user.tenant?.name as string) || (user.tenant?.code as string) || '未知租户',
)

const scopeLabel = computed(
  () => DATA_SCOPE_OPTIONS.find((o) => o.value === user.dataScope)?.label ?? '全部数据',
)

function countMenus(nodes: MenuNode[]): number {
  return nodes.reduce(
    (acc, n) => acc + 1 + countMenus(n.children || []),
    0,
  )
}

const stats = computed(() => [
  { label: '已授予权限点', value: user.perms.length, hint: '含通配权限' },
  { label: '可见菜单节点', value: countMenus(user.menus), hint: '目录 + 菜单 + 按钮' },
  { label: '角色数量', value: user.roles.length, hint: user.roles.join(' / ') || '无' },
  { label: '本租户用户数', value: userTotal.value, hint: '按数据范围过滤' },
])

const permGroups = computed<Record<string, string[]>>(() => {
  const map: Record<string, string[]> = {}
  for (const code of user.perms) {
    const mod = code.split(':')[0] || 'other'
    ;(map[mod] ||= []).push(code)
  }
  return map
})

const menuRows = computed<MenuNode[]>(() => {
  const flat: MenuNode[] = []
  const walk = (nodes: MenuNode[]) => {
    nodes.forEach((n) => {
      flat.push({ ...n, children: [] })
      if (n.children?.length) walk(n.children)
    })
  }
  walk(user.menus)
  return flat
})

async function load() {
  await user.fetchProfile()
  try {
    const res = await userApi.list({ page: 1, page_size: 1 })
    userTotal.value = res.total
  } catch {
    userTotal.value = '无权查看'
  }
}

onActivated(load)
</script>

<style scoped lang="scss">
.grid-2 {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 14px;
  margin: 14px 0;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 650;
}

.section-head span {
  font-size: 12px;
}

.role-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.kv {
  display: grid;
  grid-template-columns: 96px 1fr;
  row-gap: 10px;
  font-size: 13px;
}

.kv > span:nth-child(odd) {
  color: var(--ink-500);
}

.perm-groups {
  max-height: 260px;
  overflow: auto;
  display: grid;
  gap: 12px;
}

.perm-group__title {
  margin-bottom: 6px;
  color: var(--ink-700);
  font-size: 12.5px;
  font-weight: 600;
}

.perm-group__codes {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
