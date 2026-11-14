<template>
  <div class="page-heading">
    <div><span>HERE TO HELP</span><h1>今天，有什么可以帮你？</h1><p>从一个问题开始。查询订单、了解规则，或把问题交给人工。</p></div>
    <el-button :disabled="isBusy" @click="createThread">＋ 新会话</el-button>
  </div>
  <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
  <div class="support-page">
    <section class="chat-workspace">
      <aside class="chat-workspace__history">
        <h3>我的会话</h3>
        <button v-for="thread in threads" :key="thread.id" :class="{ 'is-selected': selected?.id === thread.id }"
          :disabled="isBusy" @click="loadThread(thread.id)">
          <strong>{{ thread.title }}</strong><small>{{ new Date(thread.created_at).toLocaleDateString() }}</small>
        </button>
        <p v-if="!threads.length">第一段对话，从这里开始。</p>
      </aside>
      <div class="chat-workspace__conversation">
        <div class="chat-workspace__title"><strong>{{ selected?.title ?? 'MewHelp 智能客服' }}</strong><small>{{ progress || '会话自动保存' }}</small></div>
        <div ref="messageList" class="chat-messages" aria-live="polite">
          <div v-if="!messages.length" class="chat-messages__empty">
            <span>✳</span><h2>你好，我是 MewHelp</h2><p>关于商品、订单和售后，我会先核实，再回答。</p>
            <div class="support-page__suggestions">
              <button v-for="prompt in prompts" :key="prompt" :disabled="isBusy" @click="draft = prompt; handleSend()">{{ prompt }} ↗</button>
            </div>
          </div>
          <article v-for="(message, index) in messages" :key="message.turn_id ?? index" class="chat-messages__item"
            :class="{ 'chat-messages__item--user': message.role === 'user' }">
            <span class="chat-messages__avatar">{{ message.role === 'user' ? '我' : '✳' }}</span>
            <div class="support-page__message">
              <strong>{{ message.role === 'user' ? '你' : 'MewHelp' }}</strong><p>{{ message.content }}</p>
              <details v-for="citation in message.citations" :key="citation.number" class="support-page__citation">
                <summary>[{{ citation.number }}] {{ citation.title }} <small>查看依据</small></summary>
                <p>{{ citation.content }}</p><small>检索分数 {{ citation.score.toFixed(2) }}</small>
              </details>
              <div v-if="message.tools.length" class="support-page__tools">
                <span v-for="(tool, toolIndex) in message.tools" :key="toolIndex">✓ {{ tool === 'query_logistics' ? '查询物流' : '查询订单' }}</span>
                <small v-if="mode === 'demo'">演示工具流程</small>
              </div>
              <div v-if="message.turn_id" class="support-page__feedback">
                <el-button text size="small" :disabled="isBusy" :type="message.feedback === 'up' ? 'primary' : 'default'" @click="sendFeedback(message, 'up')">有帮助</el-button>
                <el-button text size="small" :disabled="isBusy" :type="message.feedback === 'down' ? 'primary' : 'default'" @click="sendFeedback(message, 'down')">待改进</el-button>
                <el-button text size="small" :disabled="isBusy || message.handoff" @click="handoff(message)">{{ message.handoff ? '已提交人工工单' : '申请人工接管' }}</el-button>
              </div>
            </div>
          </article>
          <div v-if="ordersToSelect.length" class="support-page__selection">
            <strong>你想咨询哪一笔订单？</strong><p>选择后，我会继续刚才的问题。</p>
            <button v-for="order in ordersToSelect" :key="order.id" :disabled="isBusy" @click="execute(order.id)">
              <strong>{{ order.product }}</strong><small>订单 {{ order.number }} · {{ order.status }}</small><span>选择 →</span>
            </button>
          </div>
        </div>
        <form class="chat-composer" @submit.prevent="handleSend">
          <el-alert v-if="selected?.can_retry" title="上次流程尚未完成，可以从保存的步骤重试。" type="warning" :closable="false" />
          <label class="sr-only" for="support-message">客服问题</label>
          <textarea id="support-message" v-model="draft" placeholder="输入问题，如「订单1001的物流到哪了」…" rows="2"
            maxlength="16000" :disabled="isBusy || !!ordersToSelect.length || selected?.can_retry" @keydown.ctrl.enter.prevent="handleSend"></textarea>
          <div><small>{{ ordersToSelect.length ? '请先选择上方订单' : 'Ctrl + Enter 发送 · 仅查询与研判，不提交退款' }}</small>
            <el-button v-if="isRunning" @click="controller?.abort()">停止</el-button>
            <el-button v-else-if="selected?.can_retry" type="primary" :disabled="isBusy" @click="execute(undefined, true)">重试上次流程</el-button>
            <el-button v-else type="primary" native-type="submit" :disabled="!draft.trim() || isBusy || !!ordersToSelect.length">发送 ↗</el-button>
          </div>
        </form>
      </div>
    </section>
    <aside class="support-page__orders">
      <span class="support-page__eyebrow">YOUR ORDERS</span><h2>我的订单</h2><p>咨询订单时，可直接使用订单编号。</p>
      <article v-for="order in orders" :key="order.id">
        <small>#{{ order.number }}</small><h3>{{ order.product }}</h3><el-tag size="small">{{ order.status }}</el-tag>
        <p>签收 {{ order.delivered_days }} 天 · {{ order.opened ? '已拆封' : '未拆封' }}</p>
        <el-button text size="small" :disabled="isBusy || !!ordersToSelect.length" @click="draft = `订单${order.number}物流到哪了`; handleSend()">查询物流 ↗</el-button>
      </article>
      <el-empty v-if="!orders.length" description="暂无订单" :image-size="60" />
      <el-button v-if="mode === 'demo' && !orders.length" :disabled="isBusy" @click="createDemoOrders">加载本人演示订单</el-button>
      <small v-if="mode === 'demo'" class="support-page__demo-note">当前为演示数据。检索采用字符哈希，模型回答与工具选择为演示流程。</small>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { components } from '../../api/schema'
import { client, getCsrfToken, unwrap, type ThreadInfo } from '../../api/client'
import { streamRun } from '../../api/stream'

type SupportMessage = components['schemas']['SupportMessage']
type OrderInfo = components['schemas']['OrderInfo']
const threads = ref<ThreadInfo[]>([])
const selected = ref<components['schemas']['SupportThread'] | null>(null)
const messages = ref<SupportMessage[]>([])
const orders = ref<OrderInfo[]>([])
const ordersToSelect = ref<OrderInfo[]>([])
const mode = ref('')
const draft = ref('')
const error = ref('')
const progress = ref('')
const isRunning = ref(false)
const isLoading = ref(false)
const isBusy = computed(() => isRunning.value || isLoading.value)
const messageList = ref<HTMLElement>()
const prompts = ['配送多久到？', '保温杯怎么清洗？', '我买的东西能退吗？']
let controller: AbortController | undefined
onMounted(load)
onUnmounted(() => controller?.abort())

async function load() {
  isLoading.value = true
  try {
    mode.value = unwrap(await client.GET('/api/support/profile')).mode
    orders.value = unwrap(await client.GET('/api/support/orders'))
    threads.value = unwrap(await client.GET('/api/support/threads'))
    if (threads.value[0]) await loadThread(threads.value[0].id)
  } catch (cause) { showError(cause) }
  finally { isLoading.value = false }
}
function showError(cause: unknown) { error.value = cause instanceof Error ? cause.message : '请求失败' }
async function loadThread(id: string) {
  isLoading.value = true
  error.value = ''
  try {
    selected.value = unwrap(await client.GET('/api/support/threads/{thread_id}', { params: { path: { thread_id: id } } }))
    messages.value = [...selected.value.messages]
    ordersToSelect.value = selected.value.orders_to_select
    await scrollToEnd()
  } catch (cause) { showError(cause) }
  finally { isLoading.value = false }
}
async function createThread() {
  isLoading.value = true
  error.value = ''
  try {
    const thread = unwrap(await client.POST('/api/support/threads', { body: { title: draft.value.trim().slice(0, 80) || '新的咨询' } }))
    threads.value.unshift(thread)
    selected.value = { ...thread, messages: [], orders_to_select: [], can_retry: false }
    messages.value = []
    ordersToSelect.value = []
  } catch (cause) { showError(cause) }
  finally { isLoading.value = false }
}
async function createDemoOrders() {
  isLoading.value = true
  try { orders.value = unwrap(await client.POST('/api/support/demo-orders')) }
  catch (cause) { showError(cause) }
  finally { isLoading.value = false }
}
async function handleSend() {
  if (isBusy.value || !draft.value.trim() || ordersToSelect.value.length || selected.value?.can_retry) return
  if (!selected.value) await createThread()
  if (selected.value) await execute()
}
async function execute(orderId?: string, isRetry = false) {
  if (!selected.value || isBusy.value) return
  const id = selected.value.id
  const text = draft.value.trim()
  isRunning.value = true
  error.value = ''
  controller = new AbortController()
  if (!orderId && !isRetry) {
    messages.value.push({ role: 'user', content: text, citations: [], tools: [], handoff: false })
    draft.value = ''
  }
  try {
    await streamRun(`/api/support/threads/${id}/${isRetry ? 'retry' : orderId ? 'resume' : 'messages'}`,
      isRetry ? {} : orderId ? { order_id: orderId } : { message: text }, getCsrfToken(), controller.signal, (event) => {
        if (event.type === 'progress') progress.value = event.message
        if (event.type === 'support_answer') { messages.value.push(event.answer); ordersToSelect.value = [] }
        if (event.type === 'paused' && 'orders' in event) ordersToSelect.value = event.orders
        void scrollToEnd()
      })
  } catch (cause) {
    if (controller.signal.aborted) error.value = '已停止。重新加载会话可查看保存状态。'
    else showError(cause)
  } finally {
    controller = undefined
    isRunning.value = false
    progress.value = ''
    await loadThread(id)
  }
}
async function scrollToEnd() {
  await nextTick()
  messageList.value?.scrollTo({ top: messageList.value.scrollHeight, behavior: 'smooth' })
}
async function sendFeedback(message: SupportMessage, value: 'up' | 'down') {
  if (!message.turn_id) return
  try {
    const result = unwrap(await client.POST('/api/support/turns/{turn_id}/feedback', { params: { path: { turn_id: message.turn_id } }, body: { value } }))
    message.feedback = result.feedback
    ElMessage.success(value === 'down' ? '已提交改进反馈' : '谢谢你的反馈')
  } catch (cause) { showError(cause) }
}
async function handoff(message: SupportMessage) {
  if (!message.turn_id) return
  try {
    unwrap(await client.POST('/api/support/turns/{turn_id}/handoff', { params: { path: { turn_id: message.turn_id } } }))
    message.handoff = true
    ElMessage.success('人工工单已进入客服待审队列')
  } catch (cause) { showError(cause) }
}
</script>

<style scoped>
.support-page { display: grid; grid-template-columns: minmax(0, 1fr) 230px; gap: 22px; }
.support-page .chat-workspace { height: 680px; }
.support-page .chat-workspace__conversation, .support-page .chat-messages { min-height: 0; }
.support-page .chat-workspace__history { width: 160px; }
.support-page__orders { background: var(--app-surface); border: 1px solid var(--app-line); border-radius: 14px; padding: 22px; align-self: start; }
.support-page__eyebrow { font-size: 10px; letter-spacing: 2px; color: var(--app-primary); }
.support-page__orders h2 { font-size: 18px; margin: 12px 0; }
.support-page__orders p { color: var(--app-muted); font-size: 12px; line-height: 1.8; }
.support-page__orders article { border-top: 1px solid var(--app-line); padding: 18px 0 8px; }
.support-page__orders h3 { font-size: 14px; margin: 8px 0 12px; }
.support-page__demo-note { display: block; margin-top: 20px; font-size: 11px; line-height: 1.8; }
.support-page__message { min-width: 0; flex: 1; }
.support-page__citation { margin-top: 12px; background: var(--app-soft); border-radius: 8px; padding: 10px 12px; font-size: 12px; }
.support-page__citation summary { cursor: pointer; color: var(--app-primary); }
.support-page__citation p { font-size: 12px; }
.support-page__tools { display: flex; flex-wrap: wrap; gap: 10px; color: var(--app-primary); font-size: 11px; margin-top: 12px; }
.support-page__feedback { display: flex; flex-wrap: wrap; margin-top: 8px; }
.support-page__suggestions { display: grid; gap: 9px; max-width: 280px; margin: 24px auto; }
.support-page__suggestions button { background: var(--app-surface); border: 1px solid var(--app-line); border-radius: 8px; padding: 12px; color: var(--app-primary); text-align: left; font-size: 12px; }
.support-page__selection { border: 1px solid var(--app-line); border-radius: 12px; padding: 20px; background: var(--app-soft); }
.support-page__selection > p { color: var(--app-muted); font-size: 12px; }
.support-page__selection button { position: relative; width: 100%; text-align: left; border: 1px solid var(--app-line); background: var(--app-surface); border-radius: 8px; padding: 14px; margin-top: 8px; }
.support-page__selection small { display: block; margin-top: 6px; font-size: 11px; }
.support-page__selection button span { position: absolute; right: 14px; top: 22px; font-size: 12px; color: var(--app-primary); }
@media (max-width: 1200px) { .support-page { grid-template-columns: 1fr; } .support-page__orders { width: 100%; } }
@media (max-width: 700px) { .support-page .chat-workspace__history { width: 100%; } }
</style>
