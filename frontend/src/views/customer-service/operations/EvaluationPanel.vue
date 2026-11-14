<template>
  <el-alert v-if="error" :title="error" type="error" :closable="false" />
  <div class="operations-actions"><div><h2>RAG 评估</h2><p class="operations-description">四种策略在同一评估集检索前三篇知识。Recall / MRR 只统计有预期知识的题，覆盖度统计实际阈值以上的题。</p></div><el-button type="primary" :loading="isRunning" :disabled="isLoading || !cases.length" @click="run">运行评估</el-button></div>
  <template v-if="result">
    <p class="operations-description">{{ result.mode === 'demo' ? '演示检索' : '真实供应商检索' }} · {{ result.dataset_size }} 题 · {{ result.sources.join('、') }}</p>
    <el-table :data="result.strategies">
      <el-table-column label="策略" min-width="160"><template #default="{ row }">{{ strategies[row.strategy] }}</template></el-table-column>
      <el-table-column label="Recall@3"><template #default="{ row }">{{ (row.recall * 100).toFixed(1) }}%</template></el-table-column>
      <el-table-column label="MRR@3"><template #default="{ row }">{{ row.mrr.toFixed(3) }}</template></el-table-column>
      <el-table-column label="覆盖度"><template #default="{ row }">{{ (row.coverage * 100).toFixed(1) }}%</template></el-table-column>
      <el-table-column prop="count" label="检索题数" />
    </el-table>
    <p class="operations-description">推荐阈值 {{ result.recommended_threshold.toFixed(2) }} · 当前评估集门控准确率 {{ (result.threshold_accuracy * 100).toFixed(1) }}% · {{ result.created_at ? new Date(result.created_at).toLocaleString() : '' }}</p>
  </template>
  <el-empty v-else description="尚未运行评估" :image-size="70" />
  <div class="operations-actions evaluation-heading"><h2>评估数据 · {{ cases.length }} 题</h2><el-button :disabled="isBusy" @click="edit()">＋ 添加评估题</el-button></div>
  <form v-if="isEditing" class="operations-form" @submit.prevent="save">
    <label for="evaluation-question">问题</label><el-input id="evaluation-question" v-model="form.question" maxlength="1000" />
    <label for="evaluation-knowledge">预期命中的知识（未知问题留空）</label>
    <el-select id="evaluation-knowledge" v-model="form.expected_knowledge_id" clearable placeholder="未知问题"><el-option v-for="item in knowledge" :key="item.id" :value="item.id" :label="item.title" /></el-select>
    <label for="evaluation-intent">标注意图</label><el-select id="evaluation-intent" v-model="form.intent"><el-option v-for="intent in intents" :key="intent" :value="intent" :label="intent" /></el-select>
    <label for="evaluation-source">数据来源</label><el-input id="evaluation-source" v-model="form.source" maxlength="120" />
    <el-button :disabled="isBusy" @click="isEditing = false">取消</el-button><el-button type="primary" native-type="submit" :loading="isSaving">保存评估题</el-button>
  </form>
  <el-table :data="cases" v-loading="isLoading"><el-table-column prop="question" label="问题" min-width="230" /><el-table-column prop="intent" label="意图" width="100" /><el-table-column prop="source" label="来源" min-width="170" /><el-table-column label="操作" width="90"><template #default="{ row }"><el-button text :disabled="isBusy" @click="edit(row)">编辑</el-button></template></el-table-column></el-table>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { components } from '../../../api/schema'
import { client, unwrap } from '../../../api/client'

type EvaluationInfo = components['schemas']['EvaluationInfo']
defineProps<{ result: components['schemas']['EvaluationResult'] | null }>()
const emit = defineEmits<{ changed: [] }>()
const cases = ref<EvaluationInfo[]>([])
const knowledge = ref<components['schemas']['KnowledgeInfo'][]>([])
const form = reactive<components['schemas']['EvaluationInput']>({ question: '', expected_knowledge_id: null, intent: 'knowledge', source: '运营录入' })
const selectedId = ref('')
const isEditing = ref(false)
const isLoading = ref(false)
const isSaving = ref(false)
const isRunning = ref(false)
const isBusy = computed(() => isLoading.value || isSaving.value || isRunning.value)
const error = ref('')
const intents = ['knowledge', 'order', 'logistics', 'refund', 'greeting']
const strategies: Record<string, string> = { keyword: '关键词', vector: '向量', hybrid: '混合', hybrid_rerank: '混合 + 重排' }
onMounted(load)
async function load() {
  isLoading.value = true
  try {
    cases.value = unwrap(await client.GET('/api/support/admin/evaluation-cases'))
    knowledge.value = unwrap(await client.GET('/api/support/admin/knowledge'))
  } catch (cause) { showError(cause) }
  finally { isLoading.value = false }
}
function showError(cause: unknown) { error.value = cause instanceof Error ? cause.message : '请求失败' }
function edit(item?: EvaluationInfo) {
  selectedId.value = item?.id ?? ''
  Object.assign(form, { question: item?.question ?? '', expected_knowledge_id: item?.expected_knowledge_id ?? null, intent: item?.intent ?? 'knowledge', source: item?.source ?? '运营录入' })
  isEditing.value = true
}
async function save() {
  if (isBusy.value || !form.question.trim()) return
  isSaving.value = true
  error.value = ''
  try {
    const body = { ...form, expected_knowledge_id: form.expected_knowledge_id || null }
    if (selectedId.value) unwrap(await client.PUT('/api/support/admin/evaluation-cases/{case_id}', { params: { path: { case_id: selectedId.value } }, body }))
    else unwrap(await client.POST('/api/support/admin/evaluation-cases', { body }))
    isEditing.value = false
    await load()
  } catch (cause) { showError(cause) }
  finally { isSaving.value = false }
}
async function run() {
  if (isBusy.value) return
  isRunning.value = true
  error.value = ''
  try { unwrap(await client.POST('/api/support/admin/evaluate')); await load(); emit('changed') }
  catch (cause) { showError(cause) }
  finally { isRunning.value = false }
}
</script>

<style scoped>
.evaluation-heading { margin-top: 36px; padding-top: 24px; border-top: 1px solid var(--app-line); }
</style>
