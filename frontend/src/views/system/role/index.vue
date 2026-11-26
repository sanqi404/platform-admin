<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-head__title">角色权限</h1>
        <p class="page-head__desc">
          配置角色可用的功能权限、菜单权限与数据范围
        </p>
      </div>
      <el-button v-perm="'system:role:create'" type="primary" :icon="Plus" @click="openCreate">
        新建角色
      </el-button>
    </div>

    <div class="card card--pad">
      <div class="toolbar">
        <span class="text-muted">共 {{ roles.length }} 个角色</span>
        <div class="toolbar__spacer" />
        <el-button :icon="Refresh" plain @click="load">刷新</el-button>
      </div>

      <el-table v-loading="loading" :data="roles" style="margin-top: 14px" row-key="id">
        <el-table-column label="角色" min-width="200">
          <template #default="{ row }">
            <div class="role-cell">
              <span class="role-cell__name">{{ row.name }}</span>
              <el-tag v-if="row.is_system" size="small" type="warning" effect="light">内置</el-tag>
              <el-tag v-if="row.is_all_perm" size="small" type="danger" effect="light">全量权限</el-tag>
            </div>
            <span class="mono text-muted">{{ row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column label="数据范围" width="150">
          <template #default="{ row }">
            <el-tag size="small" effect="plain" :type="row.is_all_perm ? 'danger' : undefined">
              {{ scopeLabel(row.data_scope) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 1 ? 'success' : 'info'" effect="light">
              {{ row.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="180">
          <template #default="{ row }">{{ row.remark || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button v-perm="'system:role:grant'" link type="primary" @click="openGrant(row)">
              分配权限
            </el-button>
            <el-button v-perm="'system:role:update'" link type="primary" :disabled="row.is_system" @click="openEdit(row)">
              编辑
            </el-button>
            <el-button
              v-perm="'system:role:delete'"
              link
              type="danger"
              :disabled="row.is_system"
              @click="remove(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新建 / 编辑角色 -->
    <el-dialog v-model="dialog.visible" :title="dialog.isEdit ? '编辑角色' : '新建角色'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="92px">
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="form.name" placeholder="如：值班员" />
        </el-form-item>
        <el-form-item label="角色编码" prop="code">
          <el-input v-model="form.code" :disabled="dialog.isEdit" placeholder="如：ops_operator" />
        </el-form-item>
        <el-form-item label="全量权限">
          <el-switch v-model="form.is_all_perm" />
          <span class="text-muted" style="margin-left: 10px">开启后自动拥有全部权限点与菜单</span>
        </el-form-item>
        <el-form-item label="数据范围" prop="data_scope">
          <el-select v-model="form.data_scope" :disabled="!!form.is_all_perm" style="width: 100%">
            <el-option v-for="o in DATA_SCOPE_SELECTABLE" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" :max="999" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 授权抽屉 -->
    <el-drawer v-model="grant.visible" :title="`分配权限 · ${grant.roleName}`" size="640px">
      <div v-loading="grant.loading" class="grant">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="功能权限控制接口与按钮，菜单权限控制侧边栏可见性，二者独立配置"
        />

        <div class="grant__allperm">
          <div>
            <strong>全量权限</strong>
            <span class="text-muted" style="margin-left: 8px">开启后忽略下方勾选，直接拥有租户内全部权限点与菜单</span>
          </div>
          <el-switch v-model="grant.allPerm" />
        </div>

        <el-alert
          v-if="grant.allPerm"
          type="warning"
          :closable="false"
          show-icon
          title="当前为全量权限模式，下方明细不生效；关闭开关并保存后恢复按明细授权"
          style="margin-top: 10px"
        />

        <el-tabs v-model="grant.tab" class="grant__tabs" :class="{ 'grant__tabs--disabled': grant.allPerm }">
          <!-- 功能权限 -->
          <el-tab-pane label="功能权限" name="perm">
            <div class="grant__actions">
              <el-button size="small" plain @click="checkAllPerms(true)">全选</el-button>
              <el-button size="small" plain @click="checkAllPerms(false)">清空</el-button>
              <span class="text-muted">已选 {{ grant.permIds.length }} / {{ permissions.length }}</span>
            </div>
            <div class="perm-box">
              <div v-for="(items, group) in permGroups" :key="group" class="perm-block">
                <div class="perm-block__head">
                  <el-checkbox
                    :model-value="isGroupAllChecked(items)"
                    :indeterminate="isGroupPartial(items)"
                    @change="toggleGroup(items, $event as boolean)"
                  >
                    <span class="perm-block__title">{{ group }}</span>
                  </el-checkbox>
                  <span class="text-muted">{{ items.length }} 项</span>
                </div>
                <el-checkbox-group v-model="grant.permIds" class="perm-block__body">
                  <el-checkbox v-for="p in items" :key="p.id" :value="p.id">
                    <span class="perm-name">{{ p.name }}</span>
                    <span class="mono text-muted">{{ p.code }}</span>
                  </el-checkbox>
                </el-checkbox-group>
              </div>
              <el-empty v-if="!permissions.length" description="暂无权限点" :image-size="80" />
            </div>
          </el-tab-pane>

          <!-- 菜单权限 -->
          <el-tab-pane label="菜单权限" name="menu">
            <div class="grant__actions">
              <el-button size="small" plain @click="checkAllMenus(true)">全选</el-button>
              <el-button size="small" plain @click="checkAllMenus(false)">清空</el-button>
              <span class="text-muted">勾选目录会连带其子节点</span>
            </div>
            <el-tree
              ref="treeRef"
              :data="menuTree"
              node-key="id"
              show-checkbox
              default-expand-all
              :props="{ label: 'title', children: 'children' }"
              class="menu-tree"
            >
              <template #default="{ data }">
                <span class="tree-node">
                  <span>{{ data.title }}</span>
                  <el-tag v-if="data.type === 'button'" size="small" type="info" effect="plain">按钮</el-tag>
                  <span v-if="data.perm_code" class="mono text-muted">{{ data.perm_code }}</span>
                </span>
              </template>
            </el-tree>
          </el-tab-pane>

          <!-- 数据权限 -->
          <el-tab-pane label="数据范围" name="scope">
            <el-radio-group v-model="grant.dataScope" class="scope-group">
              <el-radio v-for="o in DATA_SCOPE_SELECTABLE" :key="o.value" :value="o.value" class="scope-item">
                <div class="scope-item__body">
                  <strong>{{ o.label }}</strong>
                  <span class="text-muted">{{ scopeDesc(o.value) }}</span>
                </div>
              </el-radio>
            </el-radio-group>
          </el-tab-pane>
        </el-tabs>
      </div>

      <template #footer>
        <el-button @click="grant.visible = false">取消</el-button>
        <el-button type="primary" :loading="grant.saving" @click="saveGrant">保存授权</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { menuApi, roleApi } from '@/api'
import { DATA_SCOPE_OPTIONS, DATA_SCOPE_SELECTABLE, type MenuNode, type PermissionItem, type RoleItem } from '@/types'

const loading = ref(false)
const saving = ref(false)
const roles = ref<RoleItem[]>([])
const permissions = ref<PermissionItem[]>([])
const menuTree = ref<MenuNode[]>([])

const formRef = ref<FormInstance>()
const dialog = reactive({ visible: false, isEdit: false, id: 0 })
const form = reactive<Partial<RoleItem>>({
  name: '', code: '', data_scope: 1, sort: 0, remark: '', is_all_perm: false,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  code: [
    { required: true, message: '请输入角色编码', trigger: 'blur' },
    { pattern: /^[a-z][a-z0-9_]{2,29}$/, message: '小写字母开头，3-30 位小写字母数字下划线', trigger: 'blur' },
  ],
}

function scopeLabel(v: number): string {
  return DATA_SCOPE_OPTIONS.find((o) => o.value === v)?.label ?? '未知'
}

function scopeDesc(v: number): string {
  return {
    1: '不受部门限制，可见租户内全部数据',
    2: '仅可见所属部门及成员创建的数据',
    3: '可见所属部门及所有下级部门的数据',
    4: '仅可见本人创建或负责的数据',
    5: '按勾选的部门集合放行（需配合部门树）',
  }[v] ?? ''
}

const permGroups = computed<Record<string, PermissionItem[]>>(() => {
  const map: Record<string, PermissionItem[]> = {}
  for (const p of permissions.value) {
    ;(map[p.group || '其他'] ||= []).push(p)
  }
  return map
})

async function load() {
  loading.value = true
  try {
    roles.value = await roleApi.list()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  dialog.isEdit = false
  dialog.id = 0
  Object.assign(form, { name: '', code: '', data_scope: 1, sort: 0, remark: '', is_all_perm: false })
  dialog.visible = true
  formRef.value?.clearValidate()
}

function openEdit(row: RoleItem) {
  dialog.isEdit = true
  dialog.id = row.id
  Object.assign(form, {
    name: row.name,
    code: row.code,
    data_scope: row.data_scope,
    is_all_perm: !!row.is_all_perm,
    sort: row.sort,
    remark: row.remark ?? '',
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
    if (dialog.isEdit) {
      await roleApi.update(dialog.id, { ...form })
    } else {
      await roleApi.create({ ...form, status: 1, is_system: false })
    }
    ElMessage.success('已保存')
    dialog.visible = false
    await load()
  } finally {
    saving.value = false
  }
}

async function remove(row: RoleItem) {
  await ElMessageBox.confirm(`确认删除角色「${row.name}」？已关联用户将失去该角色授权。`, '删除角色', {
    type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
  })
  await roleApi.remove(row.id)
  ElMessage.success('已删除')
  await load()
}

/* --------------------------- 授权 --------------------------- */
const treeRef = ref<{ setCheckedKeys: (k: number[]) => void; getCheckedKeys: (leaf?: boolean) => number[]; getHalfCheckedKeys: () => number[] }>()

const grant = reactive({
  visible: false,
  loading: false,
  saving: false,
  tab: 'perm',
  roleId: 0,
  roleName: '',
  permIds: [] as number[],
  dataScope: 4,
  allPerm: false,
})

async function openGrant(row: RoleItem) {
  grant.visible = true
  grant.loading = true
  grant.tab = 'perm'
  grant.roleId = row.id
  grant.roleName = row.name
  grant.permIds = []
  grant.dataScope = row.data_scope
  grant.allPerm = !!row.is_all_perm

  try {
    const [grants] = await Promise.all([roleApi.grants(row.id), ensureMeta()])
    grant.permIds = [...grants.permission_ids]
    await nextTick()
    treeRef.value?.setCheckedKeys(grants.menu_ids)
    grant.dataScope = row.data_scope
  } finally {
    grant.loading = false
  }
}

let metaLoaded = false
async function ensureMeta() {
  if (metaLoaded) return
  const [perms, tree] = await Promise.all([menuApi.permissions(), menuApi.tree()])
  permissions.value = perms
  menuTree.value = tree
  metaLoaded = true
}

function isGroupAllChecked(items: PermissionItem[]): boolean {
  return items.length > 0 && items.every((i) => grant.permIds.includes(i.id))
}

function isGroupPartial(items: PermissionItem[]): boolean {
  const n = items.filter((i) => grant.permIds.includes(i.id)).length
  return n > 0 && n < items.length
}

function toggleGroup(items: PermissionItem[], checked: boolean) {
  const ids = items.map((i) => i.id)
  if (checked) {
    grant.permIds = Array.from(new Set([...grant.permIds, ...ids]))
  } else {
    grant.permIds = grant.permIds.filter((id) => !ids.includes(id))
  }
}

function checkAllPerms(all: boolean) {
  grant.permIds = all ? permissions.value.map((p) => p.id) : []
}

function checkAllMenus(all: boolean) {
  treeRef.value?.setCheckedKeys(all ? menuTree.value.map((m) => m.id) : [])
}

async function saveGrant() {
  grant.saving = true
  try {
    const menuIds = [
      ...(treeRef.value?.getCheckedKeys(false) ?? []),
      ...(treeRef.value?.getHalfCheckedKeys() ?? []),
    ]
    await roleApi.saveGrants(grant.roleId, {
      permission_ids: grant.allPerm ? [] : grant.permIds,
      menu_ids: grant.allPerm ? [] : Array.from(new Set(menuIds)),
      data_scope: grant.dataScope,
      is_all_perm: grant.allPerm,
    })
    ElMessage.success('授权已保存，相关用户权限缓存已失效')
    grant.visible = false
    await load()
  } finally {
    grant.saving = false
  }
}

onActivated(async () => {
  await load()
  // 预取权限点与菜单树，抽屉打开即用
  ensureMeta().catch(() => undefined)
})
</script>

<style scoped lang="scss">
.role-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  line-height: 1.4;
}

.role-cell__name {
  font-weight: 550;
}

.grant {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.grant__allperm {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
}

.grant__tabs--disabled {
  opacity: 0.5;
  pointer-events: none;
}

.grant__tabs {
  margin-top: 12px;
  flex: 1;
  min-height: 0;
}

.grant__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  font-size: 12.5px;
}

.perm-box {
  max-height: calc(100vh - 300px);
  overflow: auto;
  padding-right: 6px;
}

.perm-block {
  padding: 12px 14px;
  margin-bottom: 10px;
  border: 1px solid #eef1f6;
  border-radius: var(--radius-sm);
  background: #fbfcff;
}

.perm-block__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
}

.perm-block__title {
  font-weight: 600;
}

.perm-block__body {
  display: grid;
  gap: 6px;
  margin-top: 10px;
  padding-left: 6px;
}

.perm-name {
  margin-right: 8px;
}

.menu-tree {
  max-height: calc(100vh - 300px);
  overflow: auto;
  padding: 8px 10px;
  border: 1px solid #eef1f6;
  border-radius: var(--radius-sm);
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.scope-group {
  display: grid;
  gap: 10px;
  align-items: start;
}

.scope-item {
  height: auto;
  margin-right: 0;
  padding: 10px 12px;
  border: 1px solid #eef1f6;
  border-radius: var(--radius-sm);
}

.scope-item__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.5;
}

.scope-item__body span {
  font-size: 12px;
}
</style>
