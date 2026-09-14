<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, Coin, Document, Refresh, Search, UploadFilled } from '@element-plus/icons-vue'
import { api, errorMessage, getKnowledgeDocuments } from '../api'
import type { KnowledgeDocument } from '../types'

const documents = ref<KnowledgeDocument[]>([])
const file = ref<File>()
const query = ref('')
const hits = ref<Array<{ document_name: string; content: string; score: number }>>([])
const busy = ref(false)
const selectedDocumentId = ref('')
const loadFailure = ref('')
const health = ref<Record<string, any>>()
const totalChunks = computed(() => documents.value.reduce((sum, item) => sum + (item.chunk_count || 0), 0))
const readyDocuments = computed(() => documents.value.filter(item => item.status === 'ready').length)
const selectedDocument = computed(() => documents.value.find(item => item.id === selectedDocumentId.value) || documents.value[0])
const qdrantStatus = computed(() => health.value?.services?.qdrant)
const searchSuggestions = ['校门口高峰期发生人员聚集如何处置？', '消防通道被车辆占用时的整改流程是什么？', '校园道路交通标志被遮挡应如何处理？']

async function load() {
  loadFailure.value = ''
  try {
    const result = await getKnowledgeDocuments()
    documents.value = result
    if (!result.some(item => item.id === selectedDocumentId.value)) selectedDocumentId.value = result[0]?.id || ''
  } catch (error) {
    documents.value = []
    loadFailure.value = errorMessage(error)
  }
}
async function upload() {
  if (!file.value) return ElMessage.warning('请选择知识文档')
  busy.value = true
  try { const body = new FormData(); body.append('file', file.value); await api.post('/knowledge/documents', body); ElMessage.success('知识文档已入库'); file.value = undefined; await load() }
  catch (error) { ElMessage.error(errorMessage(error)) } finally { busy.value = false }
}
async function search() {
  if (!query.value.trim()) return ElMessage.info('请输入需要检索的安全问题')
  try { hits.value = (await api.post('/knowledge/search', { query: query.value, top_k: 5 })).data.hits }
  catch (error) {
    hits.value = []
    ElMessage.error(`知识检索失败：${errorMessage(error)}`)
  }
}
async function useSuggestion(value: string) {
  query.value = value
  await search()
}
function selectKnowledgeFile(event: Event) { file.value = (event.target as HTMLInputElement).files?.[0] }
function formatTime(value?: string) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}
onMounted(async () => {
  await Promise.all([
    load(),
    api.get('/health').then(response => { health.value = response.data }).catch(() => { health.value = undefined }),
  ])
})
</script>

<template>
  <div class="standard-page">
    <section class="page-toolbar">
      <div><p class="page-kicker">检索增强知识</p><h1>校园交通安全知识库</h1><p>维护制度、处置规范和校园规则，为风险研判提供可追溯依据。</p></div>
      <div class="toolbar-actions"><el-button :icon="Refresh" @click="load">刷新索引</el-button></div>
    </section>
    <section class="knowledge-summary archive-summary">
      <article><span>知识文档</span><strong>{{ documents.length }}</strong><small>份来源</small></article>
      <article><span>索引就绪</span><strong class="success">{{ readyDocuments }}</strong><small>可用于检索</small></article>
      <article><span>知识片段</span><strong>{{ totalChunks }}</strong><small>个语义块</small></article>
      <article><span>向量服务</span><strong class="settings-word" :class="{ success: qdrantStatus?.status === 'ok' }">{{ qdrantStatus?.status === 'ok' ? 'Qdrant 正常' : '状态未知' }}</strong><small>{{ qdrantStatus?.mode === 'embedded' ? '本地嵌入模式' : '由健康接口返回' }}</small></article>
    </section>
    <div v-if="loadFailure" class="inline-error">知识库接口加载失败：{{ loadFailure }}</div>
    <div class="knowledge-workbench">
      <div class="knowledge-column">
      <section class="content-card knowledge-source-card">
        <div class="section-title"><div><p class="eyebrow">RAG SOURCES</p><h3>制度与处置依据</h3></div><span>{{ documents.length }} 份文档</span></div>
        <div class="knowledge-upload">
          <label class="knowledge-file-picker">
            <input type="file" accept=".pdf,.docx,.txt,.md,.markdown" aria-label="选择知识库文档" @change="selectKnowledgeFile" />
            <el-icon><Document /></el-icon><span>{{ file?.name || '选择知识文档' }}</span>
          </label>
          <el-button type="primary" :icon="UploadFilled" :loading="busy" @click="upload">解析入库</el-button>
        </div>
        <div class="document-list"><article v-for="doc in documents" :key="doc.id" :class="{ selected: selectedDocument?.id === doc.id }" role="button" :aria-pressed="selectedDocument?.id === doc.id" tabindex="0" @click="selectedDocumentId = doc.id" @keydown.enter="selectedDocumentId = doc.id" @keydown.space.prevent="selectedDocumentId = doc.id"><span class="file-mark"><el-icon><Document /></el-icon></span><div><strong>{{ doc.name }}</strong><p>{{ doc.chunk_count }} 个知识片段 · {{ doc.status === 'ready' ? '索引就绪' : doc.status }}</p></div><el-icon v-if="doc.status === 'ready'" class="doc-ready"><CircleCheck /></el-icon></article><el-empty v-if="!documents.length" description="当前知识库暂无文档" :image-size="60" /></div>
      </section>
      <section class="content-card rail-card knowledge-flow-card">
        <div class="rail-heading"><div><strong>索引流水线</strong><span>从制度文件到可追溯风险依据</span></div><b>{{ readyDocuments }}/{{ documents.length }}</b></div>
        <ol class="review-step-list"><li><span>1</span><p>上传制度与处置规范</p></li><li><span>2</span><p>解析、分段并写入向量库</p></li><li><span>3</span><p>按现场问题召回相关条款</p></li><li><span>4</span><p>连同视觉证据送入风险研判</p></li></ol>
      </section>
      </div>
      <div class="knowledge-column">
      <section class="content-card knowledge-preview-card">
        <div class="section-title"><div><p class="eyebrow">SOURCE INSPECTOR</p><h3>来源与索引详情</h3></div><span>真实元数据</span></div>
        <template v-if="selectedDocument">
          <div class="selected-doc-hero"><span class="file-mark"><el-icon><Document /></el-icon></span><div><strong>{{ selectedDocument.name }}</strong><p>{{ selectedDocument.mime_type }}</p></div></div>
          <dl class="document-metadata"><div><dt>索引状态</dt><dd class="success">{{ selectedDocument.status === 'ready' ? '已就绪' : selectedDocument.status }}</dd></div><div><dt>知识片段</dt><dd>{{ selectedDocument.chunk_count }}</dd></div><div><dt>入库时间</dt><dd>{{ formatTime(selectedDocument.created_at) }}</dd></div><div><dt>文档标识</dt><dd class="mono">{{ selectedDocument.id }}</dd></div></dl>
          <div class="source-boundary"><el-icon><Coin /></el-icon><div><strong>正文不在列表接口下发</strong><p>当前后端仅返回文档元数据；需要核对具体条款时，请在右侧发起真实 RAG 检索并查看命中文本与相似度。</p></div></div>
        </template>
        <el-empty v-else description="选择文档后查看索引元数据" :image-size="60" />
      </section>
      <section class="content-card rail-card index-health-card">
        <div class="rail-heading"><div><strong>索引状态</strong><span>{{ documents.length ? (readyDocuments === documents.length ? '全部文档可检索' : '部分文档尚未就绪') : '暂无已入库文档' }}</span></div><b>{{ documents.length ? Math.round(readyDocuments / documents.length * 100) : 0 }}%</b></div>
        <el-progress :percentage="documents.length ? Math.round(readyDocuments / documents.length * 100) : 0" :show-text="false" :stroke-width="7" />
        <div class="rail-metrics"><span><small>文档来源</small><strong>{{ documents.length }}</strong></span><span><small>知识片段</small><strong>{{ totalChunks }}</strong></span></div>
      </section>
      </div>
      <div class="knowledge-column">
      <section class="content-card knowledge-search-card">
        <div class="section-title"><div><p class="eyebrow">RETRIEVAL TEST</p><h3>检索效果测试</h3></div><span>Top {{ hits.length }}</span></div>
        <div class="search-row"><el-input v-model="query" placeholder="例如：停车场标志被遮挡如何处置？" @keyup.enter="search"><template #prefix><el-icon><Search /></el-icon></template></el-input><el-button @click="search">检索</el-button></div>
        <div class="hit-list"><article v-for="(hit, index) in hits" :key="hit.document_name + hit.content"><div><i>{{ index + 1 }}</i><strong>{{ hit.document_name }}</strong><span>{{ hit.score.toFixed(3) }}</span></div><p>{{ hit.content }}</p></article></div>
        <div v-if="!hits.length" class="search-empty-state"><strong>试试这些校园安全问题</strong><p>点击问题会直接检索当前知识库，不会修改文档内容。</p><button v-for="item in searchSuggestions" :key="item" type="button" @click="useSuggestion(item)">{{ item }}</button></div>
      </section>
        <section class="content-card rail-card suitable-source-card">
          <div class="rail-heading"><div><strong>建议纳入资料</strong><span>让研判更贴合本校规则</span></div></div>
          <ul><li>校园交通与停车管理制度</li><li>消防通道和应急处置预案</li><li>校门高峰期值守工作规范</li><li>电动车通行及充电管理办法</li></ul>
        </section>
      </div>
    </div>
  </div>
</template>
