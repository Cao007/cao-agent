<template>
  <el-alert v-if="error" :title="error" type="error" :closable="false" />
  <div class="operations-actions"><div><h2>飞轮待审</h2><p class="operations-description">核实未知问题与负反馈。通过后，补充答案自动加入知识库并索引。</p></div><el-button :loading="isLoading" @click="load">刷新</el-button></div>
  <div class="review-filters"><el-radio-group v-model="filter"><el-radio-button value="pending">待审核</el-radio-button><el-radio-button value="all">全部记录</el-radio-button></el-radio-group></div>
  <article v-for="item in visibleItems" :key="item.id" class="review-item">
    <div class="review-item__heading"><strong>{{ item.question }}</strong><el-tag>{{ names[item.review_status ?? ''] ?? item.review_status }}</el-tag></div>
    <small>{{ new Date(item.created_at).toLocaleString() }} · {{ item.intent }} {{ item.handoff ? '· 人工工单' : '' }} {{ item.feedback === 'down' ? '· 负反馈' : '' }}</small>
    <p class="review-item__answer">原回答：{{ item.answer }}</p>
    <p v-if="item.correction">补充知识：{{ item.correction }}</p>
    <form v-if="item.review_status === 'pending'" @submit.prevent="review(item.id, 'approve')">
      <label :for="`correction-${item.id}`">已核实的可靠答案</label><textarea :id="`correction-${item.id}`" v-model="corrections[item.id]" rows="3" maxlength="32000" placeholder="填写准确答案后，审核通过并加入知识库…" />
      <div class="review-item__actions"><el-button :disabled="isBusy" @click="review(item.id, 'expire')">过期</el-button><el-button :disabled="isBusy" @click="review(item.id, 'reject')">驳回</el-button><el-button type="primary" native-type="submit" :disabled="isBusy || !corrections[item.id]?.trim()">通过并入库</el-button></div>
    </form>
  </article>
  <el-empty v-if="!visibleItems.length && !isLoading" description="当前没有待处理的问题" />
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { components } from '../../../api/schema'
import { client, unwrap } from '../../../api/client'

const emit = defineEmits<{ changed: [] }>()
const items = ref<components['schemas']['TurnInfo'][]>([])
const corrections = reactive<Record<string, string>>({})
const filter = ref('pending')
const isLoading = ref(false)
const isSaving = ref(false)
const isBusy = computed(() => isLoading.value || isSaving.value)
const error = ref('')
const names: Record<string, string> = { pending: '待审核', approved: '已入库', rejected: '已驳回', expired: '已过期' }
const visibleItems = computed(() => items.value.filter(item => filter.value === 'all' || item.review_status === 'pending'))
onMounted(load)
async function load() {
  isLoading.value = true
  try { items.value = unwrap(await client.GET('/api/support/admin/reviews')) }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '加载失败' }
  finally { isLoading.value = false }
}
async function review(id: string, action: 'approve' | 'reject' | 'expire') {
  if (isBusy.value) return
  isSaving.value = true
  error.value = ''
  try {
    unwrap(await client.POST('/api/support/admin/reviews/{turn_id}', { params: { path: { turn_id: id } }, body: { action, answer: corrections[id] ?? '' } }))
    ElMessage.success(action === 'approve' ? '已审核并加入知识库' : '已处理')
    await load()
    emit('changed')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '审核失败' }
  finally { isSaving.value = false }
}
</script>

<style scoped>
.review-filters { margin-bottom: 20px; }.review-item { border: 1px solid var(--app-line); border-radius: 10px; padding: 22px; margin-top: 14px; }
.review-item__heading { display: flex; justify-content: space-between; gap: 20px; align-items: center; margin-bottom: 10px; font-size: 14px; }
.review-item > small { font-size: 11px; }.review-item p { font-size: 12px; line-height: 1.8; white-space: pre-wrap; }
.review-item__answer { color: var(--app-muted); }.review-item label { display: block; font-size: 12px; margin-bottom: 10px; }.review-item__actions { display: flex; justify-content: flex-end; margin-top: 14px; }
</style>
