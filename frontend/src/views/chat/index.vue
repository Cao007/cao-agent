<template>
  <div class="page-heading"><div><span>CONVERSATION</span><h1>对话助手</h1><p>讨论想法，解释问题，让每次对话接着上次继续。</p></div>
    <el-button :disabled="isRunning || isLoading" @click="createThread">＋ 新会话</el-button></div>
  <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
  <section class="chat-workspace">
    <aside class="chat-workspace__history">
      <h3>最近会话</h3>
      <button v-for="thread in threads" :key="thread.id" :class="{ 'is-selected': selected?.id === thread.id }"
        :disabled="isRunning || isLoading" @click="loadThread(thread.id)">
        <strong>{{ thread.title }}</strong><small>{{ new Date(thread.created_at).toLocaleDateString() }}</small>
      </button>
      <p v-if="!threads.length">还没有会话</p>
    </aside>
    <div class="chat-workspace__conversation">
      <div class="chat-workspace__title">{{ selected?.title ?? '新对话' }}<small>{{ isRunning ? '生成中…' : '对话历史自动保存' }}</small></div>
      <MessageList :messages="messages" />
      <form class="chat-composer" @submit.prevent="handleSend">
        <label class="sr-only" for="message">对话内容</label>
        <textarea id="message" v-model="draft" placeholder="输入你的问题…" rows="3" maxlength="16000"
          :disabled="isRunning || isLoading" @keydown.ctrl.enter.prevent="handleSend"></textarea>
        <div><small>Ctrl + Enter 发送</small>
          <el-button v-if="isRunning" @click="controller?.abort()">停止生成</el-button>
          <el-button v-else type="primary" native-type="submit" :disabled="!draft.trim() || isLoading">发送 ↗</el-button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { client, getCsrfToken, unwrap, type ThreadInfo, type ThreadDetail } from '../../api/client'
import { streamRun } from '../../api/stream'
import MessageList from '../../components/ai/MessageList.vue'

const threads = ref<ThreadInfo[]>([])
const selected = ref<ThreadDetail | null>(null)
const messages = ref<ThreadDetail['messages']>([])
const draft = ref('')
const error = ref('')
const isRunning = ref(false)
const isLoading = ref(false)
let controller: AbortController | undefined
onMounted(loadThreads)
onUnmounted(() => controller?.abort())

async function loadThreads() {
  isLoading.value = true
  try {
    threads.value = unwrap(await client.GET('/api/chat/threads'))
    if (threads.value[0]) await loadThread(threads.value[0].id)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '加载失败'
  } finally { isLoading.value = false }
}
async function loadThread(id: string) {
  isLoading.value = true
  error.value = ''
  try {
    selected.value = unwrap(await client.GET('/api/chat/threads/{thread_id}', { params: { path: { thread_id: id } } }))
    messages.value = [...selected.value.messages]
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '加载失败'
  } finally { isLoading.value = false }
}
async function createThread() {
  if (isLoading.value) return
  isLoading.value = true
  error.value = ''
  try {
    const thread = unwrap(await client.POST('/api/chat/threads', { body: { title: draft.value.trim().slice(0, 80) || '新会话' } }))
    threads.value.unshift(thread)
    selected.value = { ...thread, messages: [] }
    messages.value = []
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '创建失败'
  } finally { isLoading.value = false }
}
async function handleSend() {
  if (isRunning.value || isLoading.value || !draft.value.trim()) return
  isRunning.value = true
  error.value = ''
  try {
    if (!selected.value) await createThread()
    if (!selected.value) return
    const text = draft.value.trim()
    draft.value = ''
    messages.value.push({ role: 'user', content: text }, { role: 'assistant', content: '' })
    const answer = messages.value[messages.value.length - 1]
    controller = new AbortController()
    await streamRun(`/api/chat/threads/${selected.value.id}/messages`, { message: text },
      getCsrfToken(), controller.signal, (event) => {
        if (event.type === 'token') answer.content += event.content
      })
  } catch (cause) {
    error.value = controller?.signal.aborted ? '已停止生成。已保存的内容可重新加载查看。'
      : cause instanceof Error ? cause.message : '运行失败'
  } finally {
    isRunning.value = false
    controller = undefined
  }
}
</script>
