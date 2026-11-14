<template>
  <main class="auth-page">
    <section class="auth-page__intro">
      <div class="auth-page__brand">✦ Cao AI</div>
      <h1>让 AI 成为<br />业务的一部分。</h1>
      <p>从连续对话到文档抽取，<br />在同一个工作空间完成你的任务。</p>
      <span>FASTAPI · LANGGRAPH · VUE</span>
    </section>
    <section class="auth-page__form">
      <h2>{{ isRegister ? '创建账户' : '欢迎回来' }}</h2>
      <p>登录后保存你的会话与处理记录。</p>
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
      <el-form label-position="top" @submit.prevent="handleSubmit">
        <el-form-item label="用户名">
          <el-input v-model="username" autocomplete="username" placeholder="至少 3 位字母、数字或下划线" :maxlength="64" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" show-password
            :autocomplete="isRegister ? 'new-password' : 'current-password'" placeholder="至少 10 个字符" :maxlength="128" />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="isLoading" class="auth-page__submit">
          {{ isRegister ? '注册并进入' : '登录' }}
        </el-button>
      </el-form>
      <el-button text :disabled="isLoading" @click="isRegister = !isRegister; error = ''">
        {{ isRegister ? '已有账户？去登录' : '首次使用？创建账户' }}
      </el-button>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const username = ref('')
const password = ref('')
const isRegister = ref(false)
const isLoading = ref(false)
const error = ref('')
const router = useRouter()
const auth = useAuthStore()
async function handleSubmit() {
  if (isLoading.value) return
  error.value = ''
  isLoading.value = true
  try {
    await auth.login(username.value, password.value, isRegister.value)
    password.value = ''
    await router.push('/chat')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '登录失败，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}
</script>
