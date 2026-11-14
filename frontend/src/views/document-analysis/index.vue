<template>
  <div class="page-heading"><div><span>DOCUMENT ANALYSIS</span><h1>文档抽取</h1><p>把长文本整理为摘要、关键要点和行动项。</p></div></div>
  <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
  <div class="analysis-workspace">
    <section class="analysis-workspace__input">
      <h2>待处理文本</h2>
      <label class="sr-only" for="source">原文</label>
      <textarea id="source" v-model="text" rows="13" maxlength="32000" :disabled="isRunning"
        placeholder="粘贴会议笔记、需求说明或业务文档…"></textarea>
      <el-checkbox v-model="requireReview" :disabled="isRunning">抽取后由我审核，再保存正式结果</el-checkbox>
      <div class="analysis-workspace__actions">
        <el-button v-if="isRunning" @click="controller?.abort()">停止</el-button>
        <el-button type="primary" :loading="isRunning" :disabled="!text.trim() || isLoading" @click="handleCreate">开始抽取 ↗</el-button>
      </div>
      <h3>最近处理记录 <el-button text :disabled="isRunning || isLoading" @click="loadRecords">刷新</el-button></h3>
      <button v-for="record in records" :key="record.id" class="analysis-record"
        :class="{ 'is-selected': selected?.id === record.id }" :disabled="isRunning || isLoading" @click="selectRecord(record)">
        <strong>{{ record.title }}</strong><small>{{ statusName(record.status) }}</small>
      </button>
    </section>
    <section class="analysis-workspace__output" aria-live="polite">
      <div v-if="!selected" class="analysis-workspace__empty"><span>≡</span><h2>让信息更清晰</h2><p>输入文本后，结构化结果会显示在这里。</p></div>
      <template v-else>
        <el-tag>{{ isRunning ? progress || '处理中' : statusName(selected.status) }}</el-tag>
        <ExtractionResult v-if="selected.review || selected.result" :result="(selected.review || selected.result)!" />
        <div v-if="selected.review" class="analysis-review">
          <p>请核对候选结果。通过后将保存为正式结果。</p>
          <el-button :disabled="isRunning" @click="handleReview(false)">拒绝</el-button>
          <el-button type="primary" :disabled="isRunning" @click="handleReview(true)">审核通过</el-button>
        </div>
        <el-button v-else-if="['idle', 'cancelled', 'error'].includes(selected.status)" :disabled="isRunning" @click="execute(false)">继续处理</el-button>
        <p v-else-if="selected.status === 'complete' && !selected.result">此结果已拒绝，未保存正式输出。</p>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { client, getCsrfToken, unwrap, type AnalysisInfo } from '../../api/client'
import { streamRun } from '../../api/stream'
import ExtractionResult from '../../components/ai/ExtractionResult.vue'

const text = ref('')
const requireReview = ref(true)
const records = ref<AnalysisInfo[]>([])
const selected = ref<AnalysisInfo | null>(null)
const isRunning = ref(false)
const isLoading = ref(false)
const progress = ref('')
const error = ref('')
let controller: AbortController | undefined
onMounted(loadRecords)
onUnmounted(() => controller?.abort())

function statusName(status: string) {
  return ({ idle: '待处理', running: '处理中', paused: '待审核', complete: '已完成',
    cancelled: '已停止', error: '运行失败' } as Record<string, string>)[status] ?? status
}
async function loadRecords() {
  isLoading.value = true
  try { records.value = unwrap(await client.GET('/api/analyses')) }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '加载失败' }
  finally { isLoading.value = false }
}
function selectRecord(record: AnalysisInfo) {
  selected.value = record
  text.value = record.text
  requireReview.value = record.require_review
  error.value = ''
}
async function handleCreate() {
  if (isRunning.value || isLoading.value || !text.value.trim()) return
  error.value = ''
  isRunning.value = true
  try {
    selected.value = unwrap(await client.POST('/api/analyses', {
      body: { text: text.value, require_review: requireReview.value },
    }))
    await execute(false)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '创建失败'
  } finally { isRunning.value = false }
}
async function handleReview(approved: boolean) { await execute(true, approved) }
async function execute(isResume: boolean, approved = false) {
  if (!selected.value) return
  isRunning.value = true
  error.value = ''
  progress.value = ''
  controller = new AbortController()
  const id = selected.value.id
  try {
    await streamRun(`/api/analyses/${id}/${isResume ? 'resume' : 'run'}`,
      isResume ? { approved } : {}, getCsrfToken(), controller.signal, (event) => {
        if (event.type === 'progress') progress.value = event.message
        if (event.type === 'paused' && 'review' in event && selected.value) {
          selected.value.review = event.review
          selected.value.status = 'paused'
        }
        if (event.type === 'result' && selected.value) {
          selected.value.result = event.result
          selected.value.review = null
        }
        if (event.type === 'done' && selected.value) selected.value.status = 'complete'
      })
  } catch (cause) {
    error.value = controller.signal.aborted ? '已停止。刷新记录后可继续处理。'
      : cause instanceof Error ? cause.message : '运行失败'
  } finally {
    controller = undefined
    await loadRecords()
    selected.value = records.value.find((record) => record.id === id) ?? selected.value
    isRunning.value = false
  }
}
</script>
