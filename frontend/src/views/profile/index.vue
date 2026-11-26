<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-head__title">个人中心</h1>
        <p class="page-head__desc">账号信息与当前权限</p>
      </div>
      <el-button plain @click="pwdVisible = true">修改密码</el-button>
    </div>

    <div class="profile-grid">
      <div class="card card--pad identity">
        <el-avatar :size="64" class="identity__avatar">{{ (user.displayName || 'U').slice(0, 1) }}</el-avatar>
        <h2>{{ user.displayName }}</h2>
        <p class="mono text-muted">{{ user.user?.username }}</p>
        <div class="identity__tags">
          <el-tag v-for="r in user.roles" :key="r" size="small" effect="light" type="primary">{{ r }}</el-tag>
        </div>
      </div>

      <div class="card card--pad">
        <div class="section-head"><h3>账号信息</h3></div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="用户 ID">{{ user.user?.id }}</el-descriptions-item>
          <el-descriptions-item label="用户名">{{ user.user?.username }}</el-descriptions-item>
          <el-descriptions-item label="昵称">{{ user.user?.nickname || '—' }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ user.user?.email || '—' }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ user.user?.phone || '—' }}</el-descriptions-item>
          <el-descriptions-item label="租户">{{ user.tenant?.name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="租户编码">
            <span class="mono">{{ user.tenant?.code || '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="数据范围">{{ scopeLabel }}</el-descriptions-item>
          <el-descriptions-item label="最近登录" :span="2">
            <span class="mono">{{ user.user?.last_login_at || '—' }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="card card--pad" style="grid-column: 1 / -1">
        <div class="section-head">
          <h3>权限快照</h3>
          <span class="text-muted">登录时下发，角色变更后需重新登录或刷新</span>
        </div>
        <div class="perm-wrap">
          <el-tag v-for="p in user.perms" :key="p" size="small" effect="plain" class="mono">{{ p }}</el-tag>
          <el-empty v-if="!user.perms.length" description="暂无权限点" :image-size="70" />
        </div>
      </div>
    </div>

    <PasswordDialog v-model="pwdVisible" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import PasswordDialog from '@/components/PasswordDialog.vue'
import { useUserStore } from '@/stores/user'
import { DATA_SCOPE_OPTIONS } from '@/types'

const user = useUserStore()
const pwdVisible = ref(false)

const scopeLabel = computed(
  () => DATA_SCOPE_OPTIONS.find((o) => o.value === user.dataScope)?.label ?? '全部数据',
)
</script>

<style scoped lang="scss">
.profile-grid {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 14px;
}

@media (max-width: 900px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
}

.identity {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 26px 18px;
}

.identity__avatar {
  background: linear-gradient(135deg, var(--brand-500), #8b5cf6);
  color: #fff;
  font-size: 22px;
  font-weight: 600;
}

.identity h2 {
  margin: 14px 0 2px;
  font-size: 17px;
  font-weight: 650;
}

.identity__tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
  margin-top: 12px;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 650;
}

.section-head span {
  font-size: 12px;
}

.perm-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
