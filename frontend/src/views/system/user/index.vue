<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-head__title">用户管理</h1>
        <p class="page-head__desc">
          维护本租户的账号、状态与角色分配
        </p>
      </div>
      <el-button v-perm="'system:user:create'" type="primary" :icon="Plus" @click="openCreate">
        新建用户
      </el-button>
    </div>

    <div class="card card--pad">
      <div class="toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="搜索用户名 / 昵称 / 手机号"
          clearable
          style="width: 260px"
          :prefix-icon="Search"
          @keyup.enter="reload"
          @clear="reload"
        />
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 120px" @change="reload">
          <el-option label="启用" :value="1" />
          <el-option label="停用" :value="0" />
        </el-select>
        <el-button type="primary" plain @click="reload">查询</el-button>
        <el-button :icon="Refresh" plain @click="reset">重置</el-button>
        <div class="toolbar__spacer" />
        <span class="text-muted">共 {{ total }} 个账号</span>
      </div>

      <el-table v-loading="loading" :data="rows" style="margin-top: 14px" row-key="id">
        <el-table-column label="用户" min-width="190">
          <template #default="{ row }">
            <div class="user-cell">
              <el-avatar :size="30" class="user-cell__avatar">{{ (row.nickname || row.username).slice(0, 1) }}</el-avatar>
              <div class="user-cell__meta">
                <span class="user-cell__name">
                  {{ row.nickname || row.username }}
                  <el-tag v-if="row.is_superuser" size="small" type="danger" effect="light">超管</el-tag>
                </span>
                <span class="user-cell__sub mono">{{ row.username }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <template v-if="row.roles && row.roles.length">
              <el-tag
                v-for="r in row.roles"
                :key="r.id"
                size="small"
                :type="r.code === 'super_admin' ? 'danger' : 'primary'"
                effect="light"
                style="margin-right: 6px"
              >
                {{ r.name }}
              </el-tag>
            </template>
            <span v-else class="text-muted">未分配</span>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="170">
          <template #default="{ row }">{{ row.email || '—' }}</template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" min-width="130">
          <template #default="{ row }">{{ row.phone || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 1 ? 'success' : 'info'" effect="light">
              {{ row.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最近登录" min-width="170">
          <template #default="{ row }"><span class="mono">{{ row.last_login_at || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button v-perm="'system:user:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'system:user:reset-pwd'" link type="warning" @click="resetPwd(row)">
              重置密码
            </el-button>
            <el-button
              v-perm="'system:user:delete'"
              link
              type="danger"
              :disabled="row.is_superuser"
              @click="remove(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @size-change="reload"
        @current-change="load"
      />
    </div>

    <!-- 新增 / 编辑 -->
    <el-dialog v-model="dialog.visible" :title="dialog.isEdit ? '编辑用户' : '新建用户'" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="88px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="dialog.isEdit" placeholder="登录账号，创建后不可改" />
        </el-form-item>
        <el-form-item v-if="!dialog.isEdit" label="初始密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="8-32 位，需含字母与数字" />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="form.nickname" placeholder="显示名称" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="选填" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="选填" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_ids" multiple filterable placeholder="选择角色" style="width: 100%">
            <el-option v-for="r in roles" :key="r.id" :label="`${r.name} (${r.code})`" :value="r.id" />
          </el-select>
          <div v-if="dialog.isEdit" class="form-hint">保存将按所选角色整体覆盖原授权</div>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" />
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
import { onActivated, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { roleApi, userApi, type UserPayload } from '@/api'
import type { RoleItem, UserInfo } from '@/types'

const loading = ref(false)
const saving = ref(false)
const rows = ref<UserInfo[]>([])
const total = ref(0)
const roles = ref<RoleItem[]>([])

const query = reactive({ page: 1, page_size: 10, keyword: '', status: undefined as number | undefined })

const formRef = ref<FormInstance>()
const dialog = reactive({ visible: false, isEdit: false, id: 0 })
const form = reactive<UserPayload & { status: number }>({
  username: '',
  password: '',
  nickname: '',
  email: '',
  phone: '',
  status: 1,
  role_ids: [],
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[a-zA-Z][a-zA-Z0-9_]{2,19}$/, message: '字母开头，3-20 位字母数字下划线', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入初始密码', trigger: 'blur' },
    { pattern: /^(?=.*[A-Za-z])(?=.*\d)[\S]{8,32}$/, message: '8-32 位，需含字母与数字', trigger: 'blur' },
  ],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  phone: [{ pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    const res = await userApi.list({ ...query })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function reload() {
  query.page = 1
  load()
}

function reset() {
  query.keyword = ''
  query.status = undefined
  reload()
}

async function loadRoles() {
  try {
    roles.value = await roleApi.list()
  } catch {
    roles.value = []
  }
}

function openCreate() {
  dialog.isEdit = false
  dialog.id = 0
  Object.assign(form, {
    username: '', password: '', nickname: '', email: '', phone: '', status: 1, role_ids: [],
  })
  dialog.visible = true
  formRef.value?.clearValidate()
}

function openEdit(row: UserInfo) {
  dialog.isEdit = true
  dialog.id = row.id
  Object.assign(form, {
    username: row.username,
    password: '',
    nickname: row.nickname,
    email: row.email ?? '',
    phone: row.phone ?? '',
    status: row.status,
    role_ids: (row.roles ?? []).map((r) => r.id),
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
    const payload: UserPayload = { ...form }
    if (dialog.isEdit) delete payload.password
    if (!payload.role_ids?.length) delete payload.role_ids

    if (dialog.isEdit) {
      await userApi.update(dialog.id, payload)
      ElMessage.success('已保存')
    } else {
      await userApi.create(payload)
      ElMessage.success('用户已创建')
    }
    dialog.visible = false
    await load()
  } finally {
    saving.value = false
  }
}

async function resetPwd(row: UserInfo) {
  const { value } = await ElMessageBox.prompt(
    `为 ${row.nickname || row.username} 设置新密码`,
    '重置密码',
    {
      inputType: 'password',
      inputPlaceholder: '8-32 位，需含字母与数字',
      inputValidator: (v: string) =>
        /^(?=.*[A-Za-z])(?=.*\d)[\S]{8,32}$/.test(v) || '8-32 位，需含字母与数字',
      confirmButtonText: '确认重置',
      cancelButtonText: '取消',
    },
  )
  await userApi.resetPassword(row.id, value)
  ElMessage.success('密码已重置')
}

async function remove(row: UserInfo) {
  await ElMessageBox.confirm(
    `确认删除用户「${row.nickname || row.username}」？该操作不可撤销。`,
    '删除用户',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
  )
  await userApi.remove(row.id)
  ElMessage.success('已删除')
  await load()
}

onActivated(async () => {
  await Promise.all([load(), loadRoles()])
})
</script>

<style scoped lang="scss">
.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-cell__avatar {
  background: linear-gradient(135deg, var(--brand-500), #8b5cf6);
  color: #fff;
  font-size: 12px;
}

.user-cell__meta {
  display: flex;
  flex-direction: column;
  line-height: 1.35;
}

.user-cell__name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 550;
}

.user-cell__sub {
  color: var(--ink-500);
}

.form-hint {
  margin-top: 4px;
  color: var(--ink-500);
  font-size: 12px;
}
</style>
