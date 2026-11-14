<template>
  <el-alert v-if="error" :title="error" type="error" :closable="false" />
  <div class="operations-actions"><div><h2>知识库</h2><p class="operations-description">保存后自动切块与索引。归档知识不再参与检索。</p></div><el-button type="primary" :disabled="isBusy" @click="openForm()">＋ 录入知识</el-button></div>
  <form v-if="isEditing" class="operations-form" @submit.prevent="save">
    <label for="knowledge-title">知识标题</label><el-input id="knowledge-title" v-model="form.title" maxlength="120" />
    <label for="knowledge-category">类型</label><el-select id="knowledge-category" v-model="form.category"><el-option v-for="(label, value) in categories" :key="value" :value="value" :label="label" /></el-select>
    <label for="knowledge-content">可靠知识内容</label><textarea id="knowledge-content" v-model="form.content" rows="6" maxlength="32000" required />
    <el-button :disabled="isBusy" @click="isEditing = false">取消</el-button><el-button type="primary" native-type="submit" :loading="isBusy">保存并索引</el-button>
  </form>
  <el-table :data="items" v-loading="isLoading">
    <el-table-column prop="title" label="标题" min-width="220" /><el-table-column label="类型" width="90"><template #default="{ row }">{{ categories[row.category as keyof typeof categories] }}</template></el-table-column>
    <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.status === 'indexed' ? 'success' : 'info'">{{ row.status === 'indexed' ? '已索引' : row.status === 'archived' ? '已归档' : '草稿' }}</el-tag></template></el-table-column>
    <el-table-column prop="chunk_count" label="片段" width="70" /><el-table-column label="索引进度" width="120"><template #default="{ row }"><el-progress :percentage="row.progress" /></template></el-table-column>
    <el-table-column prop="index_mode" label="索引模式" min-width="100" />
    <el-table-column label="操作" width="155"><template #default="{ row }"><el-button text :disabled="isBusy" @click="openForm(row)">编辑</el-button><el-button text :disabled="isBusy || row.status === 'archived'" @click="archive(row.id)">归档</el-button></template></el-table-column>
  </el-table>
  <el-empty v-if="!items.length && !isLoading" description="录入第一篇可靠知识" />
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { components } from '../../../api/schema'
import { client, unwrap } from '../../../api/client'

type KnowledgeInfo = components['schemas']['KnowledgeInfo']
const emit = defineEmits<{ changed: [] }>()
const items = ref<KnowledgeInfo[]>([])
const form = reactive<components['schemas']['KnowledgeInput']>({ title: '', content: '', category: 'faq' })
const selectedId = ref('')
const isEditing = ref(false)
const isLoading = ref(false)
const isSaving = ref(false)
const isBusy = computed(() => isLoading.value || isSaving.value)
const error = ref('')
const categories = { faq: '常见问题', refund: '退货规则', shipping: '配送', product: '商品' }
onMounted(load)
async function load() {
  isLoading.value = true
  try { items.value = unwrap(await client.GET('/api/support/admin/knowledge')) }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '加载失败' }
  finally { isLoading.value = false }
}
function openForm(item?: KnowledgeInfo) {
  selectedId.value = item?.id ?? ''
  Object.assign(form, { title: item?.title ?? '', content: item?.content ?? '', category: item?.category ?? 'faq' })
  isEditing.value = true
}
async function save() {
  if (isBusy.value || !form.title.trim() || !form.content.trim()) return
  isSaving.value = true
  error.value = ''
  try {
    if (selectedId.value) unwrap(await client.PUT('/api/support/admin/knowledge/{knowledge_id}', { params: { path: { knowledge_id: selectedId.value } }, body: form }))
    else unwrap(await client.POST('/api/support/admin/knowledge', { body: form }))
    isEditing.value = false
    ElMessage.success('知识已保存并索引')
    await load()
    emit('changed')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '保存失败' }
  finally { isSaving.value = false }
}
async function archive(id: string) {
  isSaving.value = true
  try {
    unwrap(await client.POST('/api/support/admin/knowledge/{knowledge_id}/archive', { params: { path: { knowledge_id: id } } }))
    await load()
    emit('changed')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '归档失败' }
  finally { isSaving.value = false }
}
</script>
