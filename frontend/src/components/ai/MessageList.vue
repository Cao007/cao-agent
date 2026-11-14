<template>
  <div ref="container" class="chat-messages" role="log" aria-label="对话消息">
    <div v-if="!messages.length" class="chat-messages__empty">
      <span>✦</span><h2>今天，一起做点什么？</h2><p>写下一个问题，开始新的对话。</p>
    </div>
    <article v-for="(message, index) in messages" :key="index" class="chat-messages__item"
      :class="{ 'chat-messages__item--user': message.role === 'user' }">
      <span class="chat-messages__avatar">{{ message.role === 'user' ? '你' : '✦' }}</span>
      <div><strong>{{ message.role === 'user' ? '你' : '对话助手' }}</strong>
        <p>{{ message.content || '正在生成…' }}</p></div>
    </article>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
const props = defineProps<{ messages: { role: 'user' | 'assistant'; content: string }[] }>()
const container = ref<HTMLElement>()
// 页面传来的流式变化会触发 DOM 更新，滚动在更新后进行。
watch(() => props.messages.map((message) => message.content).join(''), async () => {
  await nextTick()
  container.value?.scrollTo({ top: container.value.scrollHeight })
}, { flush: 'post' })
</script>
