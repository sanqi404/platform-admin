<template>
  <div class="login">
    <!-- 左：品牌区 -->
    <section class="login__brand">
      <div class="brand-inner">
        <div class="brand-logo">
          <span>{{ brand.logoText }}</span>
        </div>
        <h1>{{ brand.title }}</h1>
        <p class="brand-sub">
          多租户、功能权限、菜单权限、数据权限<br />
          分层管控，权限判定前后端同源
        </p>

        <ul class="brand-points">
          <li><el-icon><Grid /></el-icon><span>租户之间数据隔离，越权请求在服务端拦截</span></li>
          <li><el-icon><Key /></el-icon><span>权限码按 <code>模块:资源:动作</code> 授权，支持通配</span></li>
          <li><el-icon><Menu /></el-icon><span>功能权限、菜单权限、数据范围分别配置</span></li>
          <li><el-icon><DataLine /></el-icon><span>登录与写操作全部落审计日志</span></li>
        </ul>
      </div>
      <div class="glow glow--1" />
      <div class="glow glow--2" />
    </section>

    <!-- 右：表单区 -->
    <section class="login__form">
      <div class="form-inner">
        <header class="form-head">
          <h2>账号登录</h2>
          <p>请使用租户编码 + 账号密码登录</p>
        </header>

        <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="submit">
          <el-form-item prop="tenant_code">
            <el-input v-model="form.tenant_code" placeholder="租户编码" clearable>
              <template #prefix><el-icon><OfficeBuilding /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item prop="username">
            <el-input v-model="form.username" placeholder="用户名" clearable>
              <template #prefix><el-icon><User /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item prop="password">
            <el-input v-model="form.password" type="password" placeholder="密码" show-password>
              <template #prefix><el-icon><Lock /></el-icon></template>
            </el-input>
          </el-form-item>

          <el-button type="primary" class="submit" :loading="loading" @click="submit">
            登 录
          </el-button>
        </el-form>

        <div class="quick">
          <span class="text-muted">默认账号</span>
          <div class="quick__btns">
            <el-button size="small" plain @click="fill('admin')">超管 admin</el-button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { APP_BRAND } from '@/config/app'

const brand = APP_BRAND
const user = useUserStore()
const route = useRoute()
const router = useRouter()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  tenant_code: 'platform',
  username: 'admin',
  password: 'Admin@123456',
})

const rules: FormRules = {
  tenant_code: [{ required: true, message: '请输入租户编码', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
}

function fill(name: string) {
  form.username = name
  form.password = 'Admin@123456'
  form.tenant_code = 'platform'
}

async function submit() {
  if (!formRef.value) return
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return

  loading.value = true
  try {
    await user.login({ ...form })
    ElMessage.success(`欢迎回来，${user.displayName}`)
    const redirect = (route.query.redirect as string) || '/dashboard'
    await router.replace(redirect)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login {
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  min-height: 100vh;
  background: #fff;
}

/* -------- 品牌区 -------- */
.login__brand {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  padding: 0 clamp(32px, 6vw, 88px);
  background:
    radial-gradient(900px 500px at 10% 0%, rgba(99, 102, 241, 0.55), transparent 60%),
    linear-gradient(150deg, #0b1220 0%, #131c33 60%, #0b1220 100%);
  color: #e2e8f0;
}

.brand-inner {
  position: relative;
  z-index: 2;
  max-width: 480px;
}

.brand-logo {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--brand-500), #8b5cf6);
  box-shadow: 0 14px 34px -14px rgba(99, 102, 241, 1);
  font-size: 20px;
  font-weight: 700;
  color: #fff;
}

.brand-inner h1 {
  margin: 22px 0 10px;
  font-size: clamp(26px, 2.4vw, 34px);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #f8fafc;
}

.brand-sub {
  margin: 0 0 30px;
  color: #94a3b8;
  font-size: 13.5px;
  line-height: 1.85;
}

.brand-points {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 14px;
}

.brand-points li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  color: #cbd5e1;
  font-size: 13px;
  line-height: 1.6;
}

.brand-points .el-icon {
  margin-top: 2px;
  color: var(--brand-300);
}

.brand-points code {
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(99, 102, 241, 0.22);
  color: #c7d2fe;
  font-size: 12px;
}

.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  opacity: 0.55;
}

.glow--1 {
  width: 320px;
  height: 320px;
  right: -80px;
  bottom: -60px;
  background: #6366f1;
}

.glow--2 {
  width: 220px;
  height: 220px;
  left: -60px;
  bottom: 120px;
  background: #8b5cf6;
  opacity: 0.35;
}

/* -------- 表单区 -------- */
.login__form {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

.form-inner {
  width: 100%;
  max-width: 380px;
}

.form-head h2 {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 680;
  letter-spacing: -0.02em;
}

.form-head p {
  margin: 0 0 26px;
  color: var(--ink-500);
  font-size: 13px;
}

.submit {
  width: 100%;
  height: 44px;
  margin-top: 4px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.2em;
  border-radius: 10px;
}

.quick {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 22px;
  font-size: 12.5px;
}

.quick__btns {
  display: flex;
  gap: 6px;
}

@media (max-width: 960px) {
  .login {
    grid-template-columns: 1fr;
  }

  .login__brand {
    display: none;
  }
}
</style>
