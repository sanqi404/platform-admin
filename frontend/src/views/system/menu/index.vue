<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-head__title">菜单管理</h1>
        <p class="page-head__desc">
          维护侧边栏菜单、页面路由与按钮级权限绑定
        </p>
      </div>
      <el-button v-perm="'system:menu:create'" type="primary" :icon="Plus" @click="openCreate(null)">
        新建菜单
      </el-button>
    </div>

    <div class="card card--pad">
      <div class="toolbar">
        <el-input v-model="keyword" placeholder="按名称 / 路由过滤" clearable style="width: 240px" :prefix-icon="Search" />
        <div class="toolbar__spacer" />
        <el-button :icon="Refresh" plain @click="load">刷新</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="filtered"
        row-key="id"
        default-expand-all
        :tree-props="{ children: 'children' }"
        style="margin-top: 14px"
      >
        <el-table-column prop="title" label="菜单名称" min-width="200">
          <template #default="{ row }">
            <span class="menu-name">
              <el-icon v-if="row.icon"><component :is="row.icon" /></el-icon>
              {{ row.title }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="typeTag(row.type)" effect="light">{{ typeText(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路由" min-width="150">
          <template #default="{ row }"><span class="mono">{{ row.path || '—' }}</span></template>
        </el-table-column>
        <el-table-column prop="component" label="组件" min-width="170">
          <template #default="{ row }"><span class="mono">{{ row.component || '—' }}</span></template>
        </el-table-column>
        <el-table-column prop="perm_code" label="权限码" min-width="170">
          <template #default="{ row }"><span class="mono">{{ row.perm_code || '—' }}</span></template>
        </el-table-column>
        <el-table-column prop="sort" label="排序" width="70" align="center" />
        <el-table-column label="可见" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.visible ? 'success' : 'info'" effect="plain">
              {{ row.visible ? '显示' : '隐藏' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button v-perm="'system:menu:create'" link type="primary" @click="openCreate(row)">加子项</el-button>
            <el-button v-perm="'system:menu:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'system:menu:delete'" link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialog.visible" :title="dialog.isEdit ? '编辑菜单' : '新建菜单'" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-form-item label="上级菜单">
          <el-tree-select
            v-model="form.parent_id"
            :data="parentOptions"
            :props="{ label: 'title', children: 'children' }"
            node-key="id"
            check-strictly
            placeholder="留空为顶级"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-radio-group v-model="form.type">
            <el-radio value="dir">目录</el-radio>
            <el-radio value="menu">菜单</el-radio>
            <el-radio value="button">按钮</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="名称" prop="title">
          <el-input v-model="form.title" placeholder="展示标题" />
        </el-form-item>
        <el-form-item label="路由路径" prop="path">
          <el-input v-model="form.path" placeholder="如 /system/user" />
        </el-form-item>
        <el-form-item v-if="form.type === 'menu'" label="组件路径">
          <el-input v-model="form.component" placeholder="如 system/user/index" />
        </el-form-item>
        <el-form-item label="权限码">
          <el-select
            v-model="form.perm_code"
            filterable
            allow-create
            clearable
            placeholder="选择或输入权限码"
            style="width: 100%"
          >
            <el-option v-for="p in permissions" :key="p.id" :label="`${p.code} · ${p.name}`" :value="p.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" placeholder="Element Plus 图标名，如 User" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" :max="999" />
          <el-checkbox v-model="form.visible" class="ml">侧栏显示</el-checkbox>
          <el-checkbox v-model="form.keep_alive">页面缓存</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { menuApi } from '@/api'
import type { MenuNode, PermissionItem } from '@/types'

const loading = ref(false)
const saving = ref(false)
const tree = ref<MenuNode[]>([])
const permissions = ref<PermissionItem[]>([])
const keyword = ref('')

const formRef = ref<FormInstance>()
const dialog = reactive({ visible: false, isEdit: false, id: 0 })

const form = reactive({
  parent_id: 0 as number | null,
  type: 'menu' as MenuNode['type'],
  title: '',
  name: '',
  path: '',
  component: '',
  perm_code: '' as string | null,
  icon: '',
  sort: 0,
  visible: true,
  keep_alive: false,
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入菜单名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
}

function typeText(t: string) {
  return t === 'dir' ? '目录' : t === 'menu' ? '菜单' : '按钮'
}

function typeTag(t: string): 'warning' | 'success' | 'info' {
  return t === 'dir' ? 'warning' : t === 'menu' ? 'success' : 'info'
}

const filtered = computed<MenuNode[]>(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return tree.value
  const walk = (nodes: MenuNode[]): MenuNode[] =>
    nodes
      .map((n) => ({ ...n, children: walk(n.children || []) }))
      .filter(
        (n) =>
          n.title.toLowerCase().includes(kw) ||
          (n.path || '').toLowerCase().includes(kw) ||
          (n.children?.length ?? 0) > 0,
      )
  return walk(tree.value)
})

const parentOptions = computed(() => [
  { id: 0, title: '顶级菜单', children: tree.value },
])

async function load() {
  loading.value = true
  try {
    const [t, p] = await Promise.all([menuApi.tree(), menuApi.permissions()])
    tree.value = t
    permissions.value = p
  } finally {
    loading.value = false
  }
}

function openCreate(parent: MenuNode | null) {
  dialog.isEdit = false
  dialog.id = 0
  Object.assign(form, {
    parent_id: parent?.id ?? 0,
    type: parent ? 'menu' : 'dir',
    title: '',
    name: '',
    path: parent ? `${parent.path}/` : '/',
    component: '',
    perm_code: null,
    icon: '',
    sort: 0,
    visible: true,
    keep_alive: false,
  })
  dialog.visible = true
  formRef.value?.clearValidate()
}

function openEdit(row: MenuNode) {
  dialog.isEdit = true
  dialog.id = row.id
  Object.assign(form, {
    parent_id: row.parent_id ?? 0,
    type: row.type,
    title: row.title,
    name: row.name,
    path: row.path,
    component: row.component,
    perm_code: row.perm_code,
    icon: row.icon ?? '',
    sort: row.sort,
    visible: row.visible,
    keep_alive: row.keep_alive,
  })
  dialog.visible = true
  formRef.value?.clearValidate()
}

async function save() {
  if (!formRef.value) return
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return

  saving.value = true
  try {
    const payload = {
      ...form,
      parent_id: form.parent_id ?? 0,
      name: form.name || form.title,
      perm_code: form.perm_code || null,
    }
    if (dialog.isEdit) {
      await menuApi.update(dialog.id, payload)
    } else {
      await menuApi.create(payload)
    }
    ElMessage.success('已保存，重新登录后菜单生效')
    dialog.visible = false
    await load()
  } finally {
    saving.value = false
  }
}

async function remove(row: MenuNode) {
  await ElMessageBox.confirm(
    `确认删除菜单「${row.title}」？子菜单将一并失效，请谨慎操作。`,
    '删除菜单',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
  )
  await menuApi.remove(row.id)
  ElMessage.success('已删除')
  await load()
}

onActivated(load)
</script>

<style scoped lang="scss">
.menu-name {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

code {
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--brand-50);
  color: var(--brand-700);
  font-size: 12px;
}

.ml {
  margin-left: 16px;
}

:deep(.el-checkbox) {
  margin-right: 12px;
}
</style>
