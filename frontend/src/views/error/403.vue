<template>
  <div class="err">
    <div class="err__code">403</div>
    <h2>无访问权限</h2>
    <p class="text-muted">
      当前账号未被授予该页面所需权限
      <template v-if="perm">（<span class="mono">{{ perm }}</span>）</template>
    </p>
    <div class="err__actions">
      <el-button type="primary" @click="$router.replace('/dashboard')">回到工作台</el-button>
      <el-button plain @click="$router.back()">返回上一页</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const perm = computed(() => (route.query.perm as string) || '')
</script>

<style scoped lang="scss">
.err {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
  text-align: center;
}

.err__code {
  font-size: 92px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.04em;
  background: linear-gradient(135deg, var(--brand-500), #8b5cf6);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.err h2 {
  margin: 16px 0 8px;
  font-size: 20px;
  font-weight: 650;
}

.err p {
  margin: 0 0 22px;
  font-size: 13.5px;
}

.err__actions {
  display: flex;
  gap: 10px;
}
</style>
