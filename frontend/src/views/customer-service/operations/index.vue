<template>
  <div class="page-heading"><div><span>SERVICE OPERATIONS</span><h1>把每一次服务，变得更好。</h1><p>从知识到反馈，用实际运行的数据发现下一步。</p></div><el-button :loading="isLoading" @click="load">刷新数据</el-button></div>
  <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
  <template v-if="data">
    <div class="operations-stats">
      <article><small>知识已索引</small><strong>{{ data.indexed_count }} <span>/ {{ data.knowledge_count }}</span></strong><p>可供客服检索的知识</p></article>
      <article><small>待处理反馈</small><strong>{{ data.pending_count }}</strong><p>将未知问题转化为知识</p></article>
      <article><small>已服务会话</small><strong>{{ data.conversations }}</strong><p>来自实际保存的客服会话</p></article>
      <article><small>人工工单</small><strong>{{ data.handoff_count }}</strong><p>客户主动申请的人工接管</p></article>
    </div>
    <el-alert v-if="data.mode === 'demo'" title="演示环境：评估来自本项目样例的实际运行；字符检索与演示重排不能代表真实语义 RAG 效果。" type="info" :closable="false" />
    <section class="operations-panel">
      <nav class="operations-tabs" aria-label="运营模块">
        <button v-for="(label, key) in tabs" :key="key" :class="{ 'is-active': tab === key }" @click="tab = key">{{ label }}</button>
      </nav>
      <div class="operations-panel__content">
        <KnowledgePanel v-if="tab === 'knowledge'" @changed="load" />
        <EvaluationPanel v-else-if="tab === 'evaluation'" :result="data.evaluation ?? null" @changed="load" />
        <ReviewPanel v-else-if="tab === 'reviews'" @changed="load" />
        <template v-else-if="tab === 'usage'">
          <h2>观测与成本</h2><p class="operations-description">调用数是完成的客服轮次；token 与模型调用数来自供应商返回。美元费用是配置单价估算，未配置单价或无模型用量时显示未知。</p>
          <el-table :data="data.usage">
            <el-table-column prop="intent" label="意图" /><el-table-column prop="calls" label="客服轮次" />
            <el-table-column prop="measured_calls" label="实测模型调用" /><el-table-column prop="input_tokens" label="输入 token" />
            <el-table-column prop="output_tokens" label="输出 token" />
            <el-table-column label="估算费用 USD"><template #default="{ row }">{{ row.estimated_cost_usd == null ? '未知' : row.estimated_cost_usd.toFixed(6) }}</template></el-table-column>
          </el-table>
          <div class="operations-threshold"><div><small>当前阈值</small><strong>{{ data.threshold.toFixed(2) }}</strong></div><div><small>评估推荐阈值</small><strong>{{ data.evaluation?.recommended_threshold.toFixed(2) ?? '未运行' }}</strong></div><p>推荐值由当前评估集计算；它不会自动修改在线阈值。</p></div>
        </template>
        <template v-else-if="tab === 'topics'">
          <h2>主题分布</h2><p class="operations-description">按实际客服轮次的分类统计。</p>
          <el-empty v-if="!Object.keys(data.topics).length" description="尚无会话数据" />
          <div v-for="(count, intent) in data.topics" :key="intent" class="operations-topic"><strong>{{ intent }}</strong><el-progress :percentage="Math.round(count / totalTopics * 100)" /><span>{{ count }} 次</span></div>
        </template>
        <template v-else>
          <h2>分类器验收</h2><p class="operations-description">使用评估题的标注意图对比在线分类路径；演示为关键词规则，真实模式为结构化模型分类。</p>
          <el-empty v-if="!data.evaluation" description="尚未运行评估" />
          <template v-else><p>准确率 <strong>{{ (data.evaluation.classifier_accuracy * 100).toFixed(1) }}%</strong> · {{ data.evaluation.dataset_size }} 题</p>
            <el-table :data="confusionRows"><el-table-column prop="expected" label="标注意图" /><el-table-column prop="predicted" label="预测意图" /><el-table-column prop="count" label="题数" /></el-table>
            <p class="operations-description">{{ data.evaluation.sources.join('、') }} · {{ data.evaluation.created_at ? new Date(data.evaluation.created_at).toLocaleString() : '' }}</p>
          </template>
        </template>
      </div>
    </section>
  </template>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { components } from '../../../api/schema'
import { client, unwrap } from '../../../api/client'
import KnowledgePanel from './KnowledgePanel.vue'
import EvaluationPanel from './EvaluationPanel.vue'
import ReviewPanel from './ReviewPanel.vue'

const data = ref<components['schemas']['Dashboard'] | null>(null)
const error = ref('')
const isLoading = ref(false)
const tab = ref('knowledge')
const tabs = { knowledge: '知识库', evaluation: 'RAG 评估', reviews: '飞轮待审', usage: '观测与成本', topics: '主题分布', classifier: '分类器验收' }
const totalTopics = computed(() => Object.values(data.value?.topics ?? {}).reduce((sum, n) => sum + n, 0) || 1)
const confusionRows = computed(() => Object.entries(data.value?.evaluation?.confusion ?? {}).flatMap(([expected, items]) =>
  Object.entries(items).map(([predicted, count]) => ({ expected, predicted, count }))))
onMounted(load)
async function load() {
  isLoading.value = true
  error.value = ''
  try { data.value = unwrap(await client.GET('/api/support/admin/dashboard')) }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '加载失败' }
  finally { isLoading.value = false }
}
</script>

<style>
.operations-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-bottom: 24px; }
.operations-stats article { border: 1px solid var(--app-line); border-radius: 12px; background: var(--app-surface); padding: 22px; }
.operations-stats small { font-size: 12px; }.operations-stats strong { display: block; margin: 14px 0; font-size: 32px; font-weight: 600; }
.operations-stats strong span { font-size: 16px; color: var(--app-muted); }.operations-stats p { margin: 0; color: var(--app-muted); font-size: 11px; }
.operations-panel { border: 1px solid var(--app-line); border-radius: 12px; background: var(--app-surface); overflow: hidden; }
.operations-tabs { display: flex; border-bottom: 1px solid var(--app-line); padding: 0 20px; overflow-x: auto; }
.operations-tabs button { border: 0; border-bottom: 2px solid transparent; background: transparent; padding: 20px 16px; color: var(--app-muted); white-space: nowrap; font-size: 13px; }
.operations-tabs .is-active { border-color: var(--app-primary); color: var(--app-primary); }
.operations-panel__content { padding: 26px; }.operations-panel h2 { font-size: 19px; margin: 0 0 14px; }
.operations-description { color: var(--app-muted); font-size: 12px; line-height: 1.8; }
.operations-actions { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 18px; }
.operations-form { background: var(--app-soft); border: 1px solid var(--app-line); border-radius: 10px; padding: 20px; margin-bottom: 24px; }
.operations-form label { display: block; font-size: 12px; margin-bottom: 8px; }.operations-form .el-input, .operations-form .el-select { margin-bottom: 14px; width: 100%; }
.operations-form textarea { margin-bottom: 14px; }.operations-threshold { display: flex; gap: 40px; margin-top: 30px; flex-wrap: wrap; }
.operations-threshold strong { display: block; margin-top: 10px; font-size: 24px; }.operations-threshold p { color: var(--app-muted); font-size: 12px; }
.operations-topic { display: grid; grid-template-columns: 100px 1fr 60px; gap: 20px; margin: 24px 0; font-size: 13px; }
@media (max-width: 900px) { .operations-stats { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 700px) { .operations-panel__content { padding: 16px; } .operations-tabs { padding: 0; } .operations-tabs button { padding: 16px 12px; } }
</style>
