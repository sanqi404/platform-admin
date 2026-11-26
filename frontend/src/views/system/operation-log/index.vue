<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-head__title">操作日志</h1>
        <p class="page-head__desc">
          本租户的新增、修改、删除、导出记录，参数已脱敏
        </p>
      </div>
      <el-button v-perm="'system:operlog:delete'" :icon="Delete" @click="openClean">
        清理历史日志
      </el-button>
    </div>

    <div class="filter-bar">
      <el-input v-model="query.username" placeholder="操作账号" clearable style="width: 140px" @keyup.enter="search" />
      <el-select v-model="query.module" placeholder="业务模块" clearable style="width: 140px">
        <el-option v-for="m in MODULES" :key="m" :label="m" :value="m" />
      </el-select>
      <el-select v-model="query.action" placeholder="动作" clearable style="width: 130px">
        <el-option v-for="a in ACTIONS" :key="a.value" :label="a.label" :value="a.value" />
      </el-select>
      <el-select v-model="query.success" placeholder="结果" clearable style="width: 110px">
        <el-option label="成功" :value="true" />
        <el-option label="失败" :value="false" />
      </el-select>
      <el-input v-model="query.keyword" placeholder="路径 / 对象关键字" clearable style="width: 180px" @keyup.enter="search" />
      <el-date-picker
        v-model="range"
        type="datetimerange"
        start-placeholder="开始时间"
        end-placeholder="结束时间"
        value-format="YYYY-MM-DDTHH:mm:ss"
        style="width: 360px"
      />
      <el-button type="primary" :icon="Search" @click="search">查询</el-button>
      <el-button :icon="Refresh" @click="reset">重置</el-button>
    </div>

    <el-table v-loading="loading" :data="rows" style="margin-top: 14px">
      <el-table-column label="操作时间" min-width="170">
        <template #default="{ row }">{{ fmt(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="username" label="操作账号" min-width="110">
        <template #default="{ row }">{{ row.username || '—' }}</template>
      </el-table-column>
      <el-table-column prop="action_label" label="操作" min-width="150">
        <template #default="{ row }">
          <span>{{ row.action_label || row.action }}</span>
          <el-tag size="small" type="info" effect="plain" style="margin-left: 6px">{{ row.method }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="module" label="业务模块" min-width="110" />
      <el-table-column prop="target" label="操作对象" min-width="150">
        <template #default="{ row }">
          <span :class="{ 'text-muted': !row.target }">{{ row.target || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="path" label="请求路径" min-width="220" show-overflow-tooltip />
      <el-table-column label="结果" width="130">
        <template #default="{ row }">
          <el-tag size="small" :type="row.success ? 'success' : 'danger'" effect="light">
            {{ row.success ? '成功' : '失败' }} {{ row.status_code }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="耗时" width="90">
        <template #default="{ row }">{{ row.duration_ms }} ms</template>
      </el-table-column>
      <el-table-column prop="ip" label="来源 IP" min-width="120" />
      <el-table-column label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          <el-button v-perm="'system:operlog:delete'" link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="query.page"
      v-model:page-size="query.page_size"
      :total="total"
      :page-sizes="[20, 50, 100]"
      layout="total, sizes, prev, pager, next"
      style="margin-top: 14px; justify-content: flex-end"
      @size-change="load"
      @current-change="load"
    />

    <el-drawer v-model="detailVisible" title="操作详情" size="560px">
      <el-descriptions v-if="detail" :column="1" border>
        <el-descriptions-item label="操作时间">{{ fmt(detail.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="操作账号">
          {{ detail.username || '—' }}（用户 ID {{ detail.user_id ?? '—' }}）
        </el-descriptions-item>
        <el-descriptions-item label="操作">{{ detail.action_label || detail.action }}</el-descriptions-item>
        <el-descriptions-item label="业务模块">{{ detail.module }}</el-descriptions-item>
        <el-descriptions-item label="操作对象">{{ detail.target || '—' }}</el-descriptions-item>
        <el-descriptions-item label="请求">
          {{ detail.method }} {{ detail.path }}
          <span v-if="detail.query" class="text-muted">?{{ detail.query }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="结果">
          <el-tag size="small" :type="detail.success ? 'success' : 'danger'" effect="light">
            {{ detail.success ? '成功' : '失败' }} {{ detail.status_code }}
          </el-tag>
          <span style="margin-left: 8px">{{ detail.duration_ms }} ms</span>
        </el-descriptions-item>
        <el-descriptions-item v-if="detail.error_msg" label="错误信息">
          {{ detail.error_msg }}
        </el-descriptions-item>
        <el-descriptions-item label="来源">
          {{ detail.ip }}<span v-if="detail.ip_region">（{{ detail.ip_region }}）</span>
        </el-descriptions-item>
        <el-descriptions-item label="客户端">
          {{ detail.os || '—' }} / {{ detail.browser || '—' }} / {{ detail.device || '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="User-Agent">
          <span class="ua">{{ detail.user_agent || '—' }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="请求参数">
          <pre class="params">{{ prettyParams }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Refresh, Search } from '@element-plus/icons-vue'
import { logApi } from '@/api'
import type { OperationLogItem } from '@/types'

const MODULES = ['认证', '用户管理', '角色权限', '菜单管理', '权限点', '租户管理', '日志审计', '部门管理']

const ACTIONS = [
  { value: 'create', label: '新增' },
  { value: 'update', label: '更新' },
  { value: 'delete', label: '删除' },
  { value: 'grant', label: '分配权限' },
  { value: 'assign_role', label: '分配角色' },
  { value: 'reset_password', label: '重置密码' },
  { value: 'export', label: '导出数据' },
]

const loading = ref(false)
const rows = ref<OperationLogItem[]>([])
const total = ref(0)
const range = ref<[string, string] | null>(null)
const detailVisible = ref(false)
const detail = ref<OperationLogItem | null>(null)

const query = reactive({
  page: 1,
  page_size: 20,
  username: '',
  module: '',
  action: '',
  success: undefined as boolean | undefined,
  keyword: '',
})

function fmt(v: string | null): string {
  if (!v) return '—'
  return v.replace('T', ' ').slice(0, 19)
}

const prettyParams = computed(() => {
  const raw = detail.value?.params
  if (!raw) return '（无）'
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
})

async function load() {
  loading.value = true
  try {
    const res = await logApi.operationList({
      ...query,
      username: query.username || undefined,
      module: query.module || undefined,
      action: query.action || undefined,
      keyword: query.keyword || undefined,
      start_at: range.value?.[0],
      end_at: range.value?.[1],
    })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function search() {
  query.page = 1
  load()
}

function reset() {
  query.username = ''
  query.module = ''
  query.action = ''
  query.success = undefined
  query.keyword = ''
  range.value = null
  query.page = 1
  load()
}

async function openDetail(row: OperationLogItem) {
  detail.value = await logApi.operationDetail(row.id)
  detailVisible.value = true
}

async function remove(row: OperationLogItem) {
  await ElMessageBox.confirm('确认删除这条操作日志？', '删除确认', { type: 'warning' })
  await logApi.removeOperation(row.id)
  ElMessage.success('已删除')
  load()
}

async function openClean() {
  const { value } = await ElMessageBox.prompt(
    '将删除该时间点之前的全部操作日志，此操作不可恢复',
    '清理历史日志',
    { inputValue: '', inputPlaceholder: 'YYYY-MM-DD HH:mm:ss' },
  )
  const before = value.trim().replace(' ', 'T')
  if (!before) return
  const res = await logApi.cleanOperation(before)
  ElMessage.success(`已清理 ${res.deleted} 条`)
  load()
}

onActivated(load)
</script>

<style scoped>
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-top: 14px;
}

.params {
  max-height: 260px;
  overflow: auto;
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.ua {
  font-size: 12px;
  word-break: break-all;
}
</style>
