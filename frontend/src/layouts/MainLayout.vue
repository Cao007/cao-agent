<template>
  <div class="app-layout">
    <aside class="app-layout__sidebar">
      <RouterLink to="/support" class="app-layout__brand"><span>✳</span> MewHelp<small>每个问题，都值得回应</small></RouterLink>
      <p class="app-layout__label">客户服务</p>
      <RouterLink to="/support" class="app-layout__link">✧ <span>智能客服<small>知识、订单与售后</small></span></RouterLink>
      <RouterLink v-if="isOperator" to="/operations" class="app-layout__link">▦ <span>运营工作台<small>知识与服务质量</small></span></RouterLink>
      <div class="app-layout__note"><strong>有依据的回答</strong><p>引用知识，核实订单。无法确认时，交给人工处理。</p></div>
      <div class="app-layout__footer">
        <span>{{ auth.user?.username }}</span>
        <el-button text @click="handleLogout">退出</el-button>
      </div>
    </aside>
    <main class="app-layout__main">
      <header class="app-layout__header">
        <span>MewHelp / {{ route.path === '/operations' ? '运营工作台' : '智能客服' }}</span>
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
const isOperator = ref(false)
onMounted(async () => {
  const response = await client.GET('/api/health').catch(() => null)
  mode.value = (response?.data as { mode?: string })?.mode ?? ''
  const profile = await client.GET('/api/support/profile').catch(() => null)
  isOperator.value = profile?.data?.is_operator ?? false
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
