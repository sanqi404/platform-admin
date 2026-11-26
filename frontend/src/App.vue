<template>
  <!-- 根层不绑定 key、不套过渡：子路由切换时布局必须常驻，否则整页重建会闪白 -->
  <router-view />
</template>

<script setup lang="ts">
// 根组件只承载路由出口
</script>
