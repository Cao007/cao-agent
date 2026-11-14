<template>
  <div class="app-layout">
    <aside class="app-layout__sidebar">
      <RouterLink to="/chat" class="app-layout__brand"><span>✦</span> Cao AI<small>应用开发脚手架</small></RouterLink>
      <p class="app-layout__label">业务应用</p>
      <RouterLink to="/chat" class="app-layout__link">✦ <span>对话助手<small>连续对话与历史记录</small></span></RouterLink>
      <RouterLink to="/analysis" class="app-layout__link">≡ <span>文档抽取<small>结构化结果与人工审核</small></span></RouterLink>
      <div class="app-layout__footer">
        <span>{{ auth.user?.username }}</span>
        <el-button text @click="handleLogout">退出</el-button>
      </div>
    </aside>
    <main class="app-layout__main">
      <header class="app-layout__header">
        <span>工作空间 / {{ route.path === '/analysis' ? '文档抽取' : '对话助手' }}</span>
        <span v-if="mode === 'demo'" class="app-layout__demo">演示模式 · 不调用真实模型</span>
        <a href="/api/docs" target="_blank" rel="noopener noreferrer">API 文档 ↗</a>
      </header>
      <div class="app-layout__page"><slot /></div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { client } from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const mode = ref('')
onMounted(async () => {
  const response = await client.GET('/api/health').catch(() => null)
  mode.value = (response?.data as { mode?: string })?.mode ?? ''
})
async function handleLogout() {
  try {
    await auth.logout()
    await router.push('/login')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '退出失败')
  }
}
</script>
