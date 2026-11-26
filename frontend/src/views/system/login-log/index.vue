<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-head__title">登录日志</h1>
        <p class="page-head__desc">
          本租户账号的登录、登出记录，含时间、IP、设备与结果
        </p>
      </div>
      <el-button v-perm="'system:loginlog:delete'" :icon="Delete" @click="openClean">
        清理历史日志
      </el-button>
    </div>

    <div class="filter-bar">
      <el-input v-model="query.username" placeholder="账号" clearable style="width: 150px" @keyup.enter="search" />
      <el-select v-model="query.status" placeholder="结果" clearable style="width: 120px">
        <el-option label="成功" :value="1" />
        <el-option label="失败" :value="0" />
      </el-select>
      <el-select v-model="query.login_type" placeholder="类型" clearable style="width: 120px">
        <el-option label="登录" value="login" />
        <el-option label="登出" value="logout" />
      </el-select>
      <el-input v-model="query.ip" placeholder="IP 地址" clearable style="width: 160px" @keyup.enter="search" />
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
      <el-table-column prop="login_at" label="登录时间" min-width="170">
        <template #default="{ row }">{{ fmt(row.login_at) }}</template>
      </el-table-column>
      <el-table-column prop="username" label="账号" min-width="120" />
      <el-table-column label="类型" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.login_type === 'logout' ? 'info' : 'primary'" effect="light">
            {{ TYPE_LABEL[row.login_type] || row.login_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="结果" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 1 ? 'success' : 'danger'" effect="light">
            {{ row.status === 1 ? '成功' : '失败' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="fail_reason" label="失败原因" min-width="180">
        <template #default="{ row }">
          <span :class="{ 'text-muted': !row.fail_reason }">{{ row.fail_reason || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="ip" label="来源 IP" min-width="130">
        <template #default="{ row }">
          {{ row.ip }}
          <el-tag v-if="row.ip_region" size="small" type="info" effect="plain">{{ row.ip_region }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="os" label="操作系统" min-width="110">
        <template #default="{ row }">{{ row.os || '—' }}</template>
      </el-table-column>
      <el-table-column prop="browser" label="浏览器 / 客户端" min-width="140">
        <template #default="{ row }">{{ row.browser || '—' }}</template>
      </el-table-column>
      <el-table-column prop="device" label="设备" width="100">
        <template #default="{ row }">{{ row.device || '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button v-perm="'system:loginlog:delete'" link type="danger" @click="remove(row)">删除</el-button>
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
  </div>
</template>

<script setup lang="ts">
import { onActivated, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Refresh, Search } from '@element-plus/icons-vue'
import { logApi } from '@/api'
import type { LoginLogItem } from '@/types'

const TYPE_LABEL: Record<string, string> = {
  login: '登录',
  logout: '登出',
  refresh: '刷新令牌',
}

const loading = ref(false)
const rows = ref<LoginLogItem[]>([])
const total = ref(0)
const range = ref<[string, string] | null>(null)

const query = reactive({
  page: 1,
  page_size: 20,
  username: '',
  status: undefined as number | undefined,
  login_type: '',
  ip: '',
})

function fmt(v: string | null): string {
  if (!v) return '—'
  return v.replace('T', ' ').slice(0, 19)
}

async function load() {
  loading.value = true
  try {
    const res = await logApi.loginList({
      ...query,
      username: query.username || undefined,
      login_type: query.login_type || undefined,
      ip: query.ip || undefined,
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
  query.status = undefined
  query.login_type = ''
  query.ip = ''
  range.value = null
  query.page = 1
  load()
}

async function remove(row: LoginLogItem) {
  await ElMessageBox.confirm(`确认删除账号「${row.username}」的这条登录记录？`, '删除确认', {
    type: 'warning',
  })
  await logApi.removeLogin(row.id)
  ElMessage.success('已删除')
  load()
}

async function openClean() {
  const { value } = await ElMessageBox.prompt(
    '将删除该时间点之前的全部登录日志，此操作不可恢复',
    '清理历史日志',
    { inputValue: '', inputPlaceholder: 'YYYY-MM-DD HH:mm:ss' },
  )
  const before = value.trim().replace(' ', 'T')
  if (!before) return
  const res = await logApi.cleanLogin(before)
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
</style>
