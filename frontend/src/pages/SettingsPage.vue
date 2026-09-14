<script setup lang="ts">
import { computed, onMounted, ref, type Component } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, DataAnalysis, Location, MagicStick, Monitor, Tickets } from '@element-plus/icons-vue'
import { api, getApiKey, saveApiKey } from '../api'
import ModelEvidencePanel from '../components/ModelEvidencePanel.vue'
const health = ref<Record<string, any>>()
const apiKey = ref(getApiKey())
const healthUnavailable = ref(false)
const serviceRows = computed(() => {
  const services = health.value?.services
  if (!services) return []
  return [
    { label: '业务数据库', value: services.database === 'ok' ? '已连接' : String(services.database || '未知'), ready: services.database === 'ok', detail: '任务、报告与复核记录', meta: 'SQLite 运行库', icon: Tickets },
    { label: 'Qdrant 向量库', value: services.qdrant?.status === 'ok' ? '已连接' : services.qdrant?.status || '未知', ready: services.qdrant?.status === 'ok', detail: '校园制度与法规知识检索', meta: services.qdrant?.mode === 'embedded' ? '本地嵌入模式' : String(services.qdrant?.mode || '模式未知'), icon: DataAnalysis },
    { label: '交通标志 YOLO26', value: services.yolo?.configured ? (services.yolo.loaded ? '已加载' : '已配置 · 按需加载') : '等待权重', ready: Boolean(services.yolo?.configured), detail: services.yolo?.model_name || 'TT100K 校园交通标志', meta: `加载次数 ${services.yolo?.load_count ?? 0}`, icon: Monitor },
    { label: '人员车辆 YOLO26', value: services.general_yolo?.configured ? (services.general_yolo.loaded ? '已加载' : '已配置 · 按需加载') : '等待权重', ready: Boolean(services.general_yolo?.configured), detail: services.general_yolo?.model_name || '人员与车辆白名单', meta: `加载次数 ${services.general_yolo?.load_count ?? 0}`, icon: Monitor },
    { label: 'DeepSeek 风险研判', value: services.llm?.configured ? '密钥已配置' : '等待填写密钥', ready: Boolean(services.llm?.configured), detail: services.llm?.model || '模型未配置', meta: '健康接口不代表已完成联网调用', icon: MagicStick },
    { label: '旁挂视觉研判 VLM', value: !services.vision_llm ? '状态未知' : !services.vision_llm.enabled ? '已关闭' : services.vision_llm.configured ? '已启用 · 已配置' : '等待配置', ready: Boolean(services.vision_llm?.enabled && services.vision_llm?.configured), detail: services.vision_llm?.model || '模型未配置', meta: '只提供视觉证据，不决定风险策略', icon: Monitor },
    { label: '高德地图 Web 服务', value: services.amap?.configured ? '密钥已配置' : '等待填写密钥', ready: Boolean(services.amap?.configured), detail: '地理编码、静态底图与天气', meta: '请求时验证可用性', icon: Location },
  ] as Array<{ label: string; value: string; ready: boolean; detail: string; meta: string; icon: Component }>
})
const readyServiceCount = computed(() => serviceRows.value.filter(item => item.ready).length)
const visualModelCount = computed(() => serviceRows.value.filter(item => item.label.includes('YOLO26') && item.ready).length)
const runtimeFacts = computed(() => {
  const services = health.value?.services
  if (!services) return []
  return [
    { label: '后端应用', value: health.value?.status === 'ok' ? '运行正常' : '状态未知' },
    { label: '交通标志模型', value: services.yolo?.loaded ? '驻留内存' : '首次任务时加载' },
    { label: '人员车辆模型', value: services.general_yolo?.loaded ? '驻留内存' : '首次任务时加载' },
    { label: '出站网络', value: services.network?.outbound_proxy_configured ? '已配置代理' : '系统直连' },
  ]
})

function persistApiKey() {
  saveApiKey(apiKey.value)
  ElMessage.success(apiKey.value.trim() ? 'API Key 已保存到当前浏览器会话' : 'API Key 已清除')
}
onMounted(async () => {
  try { health.value = (await api.get('/health')).data }
  catch {
    healthUnavailable.value = true
    health.value = { services: { database: '离线', qdrant: { status: '离线' }, yolo: { configured: false }, llm: { configured: false }, amap: { configured: false }, network: { outbound_proxy_configured: false } } }
  }
})
</script>

<template>
  <div class="standard-page">
    <section class="page-toolbar">
      <div><p class="page-kicker">系统管理</p><h1>服务与访问配置</h1><p>核对双 YOLO、旁挂视觉模型与风险研判服务的真实配置状态。</p></div>
    </section>
    <section class="settings-summary archive-summary">
      <article><span>状态项目</span><strong>{{ readyServiceCount }}/{{ serviceRows.length }}</strong><small>已连接或已配置</small></article>
      <article><span>视觉模型</span><strong class="success">{{ visualModelCount }}</strong><small>已配置 · 按需加载</small></article>
      <article><span>大模型配置</span><strong class="settings-word">{{ health?.services?.llm?.model || '未配置' }}</strong><small>服务端环境读取</small></article>
      <article><span>地图服务</span><strong class="settings-word">{{ health?.services?.amap?.configured ? 'AMap' : '未配置' }}</strong><small>高德 Web 服务</small></article>
    </section>
    <section class="settings-service-grid" aria-label="核心服务真实状态">
      <article v-for="item in serviceRows" :key="item.label" :class="{ ready: item.ready }"><span class="service-icon"><el-icon><component :is="item.icon" /></el-icon></span><div><strong>{{ item.label }}</strong><p>{{ item.detail }}</p></div><em><i></i>{{ item.value }}</em><small>{{ item.meta }}</small></article>
    </section>
    <div class="settings-workbench">
      <section class="content-card settings-status-card"><p class="eyebrow">RUNTIME FACTS</p><h3>运行态事实 <span v-if="healthUnavailable" class="demo-chip">后端离线</span></h3><div v-if="health" class="status-list"><div v-for="item in runtimeFacts" :key="item.label"><span><b>{{ item.label }}</b><small>由 /health 实时返回</small></span><strong>{{ item.value }}</strong></div></div><div class="network-state"><el-icon><Connection /></el-icon><span>状态口径</span><strong>“已配置”不等于“已联网调用”</strong></div></section>
      <section class="content-card settings-key-card"><p class="eyebrow">DEEPSEEK</p><h3>V4 Flash 已预设</h3><p>官方接口、模型名和非思考快速模式都已经配置。出于安全考虑，大模型密钥只从服务器环境读取，不会保存到浏览器。</p><div class="guardrail-note"><strong>唯一需要填写的一行</strong><p><code>LLM_API_KEY=你的DeepSeek密钥</code></p><p>位置：项目根目录 <code>.env</code>。保存后重启后端即可生效。</p></div><el-form label-position="top"><el-form-item label="系统接口访问 Key（不是 DeepSeek 密钥，可留空）"><el-input v-model="apiKey" type="password" show-password autocomplete="off" placeholder="仅当后端启用了 API_KEY 时填写" /></el-form-item><el-button type="primary" @click="persistApiKey">保存系统访问 Key</el-button></el-form></section>
      <aside class="content-card settings-flow-card"><p class="eyebrow">RUNTIME PIPELINE</p><h3>当前运行链路</h3><ol class="system-flow-list"><li><span>01</span><div><strong>现场证据进入后端</strong><p>浏览器只负责上传，密钥和模型路径不下发。</p></div></li><li><span>02</span><div><strong>双 YOLO26 协同识别</strong><p>交通标志、人员和车辆分别由对应模型处理。</p></div></li><li><span>03</span><div><strong>知识增强风险研判</strong><p>Qdrant 召回制度条款，DeepSeek 生成可解释结论。</p></div></li><li><span>04</span><div><strong>人工复核形成闭环</strong><p>高风险和不确定任务进入人工队列并归档。</p></div></li></ol><div class="security-boundaries"><span><strong>密钥边界</strong><small>仅服务端环境变量</small></span><span><strong>失败降级</strong><small>保留规则与人工复核</small></span><span><strong>访问控制</strong><small>系统 Key 按需启用</small></span></div></aside>
      <ModelEvidencePanel :services="healthUnavailable ? undefined : health?.services" />
    </div>
  </div>
</template>
