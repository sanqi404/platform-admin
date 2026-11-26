<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-head__title">租户管理</h1>
        <p class="page-head__desc">
          维护租户及其账号上限、到期时间与启用状态
        </p>
      </div>
      <el-button v-perm="'system:tenant:create'" type="primary" :icon="Plus" @click="openCreate">
        新建租户
      </el-button>
    </div>

    <div class="card card--pad">
      <div class="toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="搜索租户名称 / 编码"
          clearable
          style="width: 250px"
          :prefix-icon="Search"
          @keyup.enter="reload"
          @clear="reload"
        />
        <el-button type="primary" plain @click="reload">查询</el-button>
        <div class="toolbar__spacer" />
        <span class="text-muted">共 {{ total }} 个租户</span>
      </div>

      <el-table v-loading="loading" :data="rows" style="margin-top: 14px" row-key="id">
        <el-table-column label="租户" min-width="200">
          <template #default="{ row }">
            <div class="tenant-cell">
              <el-avatar :size="30" class="tenant-cell__avatar">{{ row.name.slice(0, 1) }}</el-avatar>
              <div class="tenant-cell__meta">
                <span class="tenant-cell__name">{{ row.name }}</span>
                <span class="mono text-muted">{{ row.code }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="contact" label="联系人" width="120">
          <template #default="{ row }">{{ row.contact || '—' }}</template>
        </el-table-column>
        <el-table-column prop="phone" label="联系电话" width="140">
          <template #default="{ row }">{{ row.phone || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 1 ? 'success' : 'info'" effect="light">
              {{ row.status === 1 ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expire_at" label="到期时间" min-width="170">
          <template #default="{ row }"><span class="mono">{{ row.expire_at || '长期' }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button v-perm="'system:tenant:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button
              v-perm="'system:tenant:delete'"
              link
              type="danger"
              :disabled="row.code === 'platform'"
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
        layout="total, sizes, prev, pager, next"
        background
        @size-change="reload"
        @current-change="load"
      />
    </div>

    <el-dialog v-model="dialog.visible" :title="dialog.isEdit ? '编辑租户' : '新建租户'" width="540px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="92px">
        <el-form-item label="租户编码" prop="code">
          <el-input v-model="form.code" :disabled="dialog.isEdit" placeholder="登录时使用，如 platform" />
        </el-form-item>
        <el-form-item label="租户名称" prop="name">
          <el-input v-model="form.name" placeholder="企业 / 部门名称" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="form.contact" placeholder="选填" />
        </el-form-item>
        <el-form-item label="联系电话" prop="phone">
          <el-input v-model="form.phone" placeholder="选填" />
        </el-form-item>
        <el-form-item label="到期时间">
          <el-date-picker
            v-model="form.expire_at"
            type="datetime"
            placeholder="留空表示长期有效"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="正常" />
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
  </div>
</template>

<script setup lang="ts">
import { onActivated, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { tenantApi } from '@/api'
import type { TenantItem } from '@/types'

const loading = ref(false)
const saving = ref(false)
const rows = ref<TenantItem[]>([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 10, keyword: '' })

const formRef = ref<FormInstance>()
const dialog = reactive({ visible: false, isEdit: false, id: 0 })
const form = reactive<Partial<TenantItem>>({
  code: '', name: '', contact: '', phone: '', status: 1, expire_at: null, remark: '',
})

const rules: FormRules = {
  code: [
    { required: true, message: '请输入租户编码', trigger: 'blur' },
    { pattern: /^[a-z][a-z0-9_-]{2,29}$/, message: '小写字母开头，3-30 位', trigger: 'blur' },
  ],
  name: [{ required: true, message: '请输入租户名称', trigger: 'blur' }],
  phone: [{ pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    const res = await tenantApi.list({ ...query })
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

function openCreate() {
  dialog.isEdit = false
  dialog.id = 0
  Object.assign(form, { code: '', name: '', contact: '', phone: '', status: 1, expire_at: null, remark: '' })
  dialog.visible = true
  formRef.value?.clearValidate()
}

function openEdit(row: TenantItem) {
  dialog.isEdit = true
  dialog.id = row.id
  Object.assign(form, {
    code: row.code,
    name: row.name,
    contact: row.contact ?? '',
    phone: row.phone ?? '',
    status: row.status,
    expire_at: row.expire_at,
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
      await tenantApi.update(dialog.id, { ...form })
    } else {
      await tenantApi.create({ ...form })
    }
    ElMessage.success('已保存')
    dialog.visible = false
    await load()
  } finally {
    saving.value = false
  }
}

async function remove(row: TenantItem) {
  await ElMessageBox.confirm(
    `确认删除租户「${row.name}」？该租户下账号与业务数据将不可访问。`,
    '删除租户',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
  )
  await tenantApi.remove(row.id)
  ElMessage.success('已删除')
  await load()
}

onActivated(load)
</script>

<style scoped lang="scss">
.tenant-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tenant-cell__avatar {
  background: linear-gradient(135deg, #0ea5e9, #6366f1);
  color: #fff;
  font-size: 12px;
}

.tenant-cell__meta {
  display: flex;
  flex-direction: column;
  line-height: 1.35;
}

.tenant-cell__name {
  font-weight: 550;
}
</style>
