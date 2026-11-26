<template>
  <div class="err">
    <div class="err__code">404</div>
    <h2>页面不存在</h2>
    <p class="text-muted">请求的地址没有对应页面，或已被移除</p>
    <div class="err__actions">
      <el-button type="primary" @click="$router.replace('/dashboard')">回到工作台</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
// 路由未匹配时展示
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
  background: linear-gradient(135deg, #94a3b8, #6366f1);
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
</style>
