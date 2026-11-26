<template>
  <el-dialog
    :model-value="modelValue"
    title="修改密码"
    width="440px"
    :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)"
    @closed="reset"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="88px">
      <el-form-item label="原密码" prop="old_password">
        <el-input v-model="form.old_password" type="password" show-password autocomplete="off" />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="form.new_password" type="password" show-password autocomplete="off" />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirm">
        <el-input v-model="form.confirm" type="password" show-password autocomplete="off" />
      </el-form-item>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="密码需 8-32 位，且同时包含字母与数字；修改后需重新登录"
      />
    </el-form>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="submit">确认修改</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { authApi } from '@/api'
import { useUserStore } from '@/stores/user'

defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [boolean] }>()

const user = useUserStore()
const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({ old_password: '', new_password: '', confirm: '' })

const rules: FormRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { pattern: /^(?=.*[A-Za-z])(?=.*\d)[\S]{8,32}$/, message: '8-32 位，需含字母与数字', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_r, v, cb) => (v === form.new_password ? cb() : cb(new Error('两次输入不一致'))),
      trigger: 'blur',
    },
  ],
}

function reset() {
  form.old_password = ''
  form.new_password = ''
  form.confirm = ''
  formRef.value?.clearValidate()
}

async function submit() {
  if (!formRef.value) return
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return

  loading.value = true
  try {
    await authApi.changePassword({
      old_password: form.old_password,
      new_password: form.new_password,
    })
    ElMessage.success('密码已修改，请重新登录')
    emit('update:modelValue', false)
    await user.logout()
    router.replace('/login')
  } finally {
    loading.value = false
  }
}
</script>
