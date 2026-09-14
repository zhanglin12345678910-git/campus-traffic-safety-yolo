<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, Close, Loading } from '@element-plus/icons-vue'
import { api, errorMessage, executeInspection, getInspection, getTrace, inspectionStreamUrl } from '../api'
import RiskBadge from '../components/RiskBadge.vue'
import type { Inspection, TraceStep } from '../types'

const route = useRoute()
const router = useRouter()
const id = String(route.params.id)
const task = ref<Inspection>()
const trace = ref<TraceStep[]>([])
const loading = ref(true)
const executing = ref(false)
let stream: EventSource | undefined
const finished = computed(() => ['completed', 'review', 'error', 'rejected'].includes(task.value?.status || ''))
const trafficSignCount = computed(() => task.value?.detections?.filter(item => item.model_role !== 'general_object').length || 0)
const generalObjectCount = computed(() => task.value?.detections?.filter(item => item.model_role === 'general_object').length || 0)
const personCount = computed(() => task.value?.detections?.filter(item => item.model_role === 'general_object' && item.class_name === 'person').length || 0)
const vehicleCount = computed(() => task.value?.detections?.filter(item => item.model_role === 'general_object' && ['bicycle', 'car', 'motorcycle', 'bus', 'truck'].includes(item.class_name)).length || 0)
const succeededSteps = computed(() => trace.value.filter(item => item.status === 'success').length)
const traceProgress = computed(() => trace.value.length ? Math.round(succeededSteps.value / trace.value.length * 100) : 0)
const traceDuration = computed(() => task.value?.total_duration_ms || trace.value.reduce((sum, item) => sum + (item.duration_ms || 0), 0))
const knowledgeReferences = computed(() => task.value?.risk_result?.knowledge_references || [])
const detectedModels = computed(() => {
  const models = new Map<string, { name: string; role: string }>()
  for (const item of task.value?.detections || []) {
    const name = item.model_name || '兼容旧记录'
    models.set(`${item.model_role || 'traffic_sign'}-${name}`, { name, role: modelLabel(item.model_role) })
  }
  return [...models.values()]
})
const statusText = computed(() => ({ pending: '待执行', queued: '排队中', running: '执行中', completed: '已完成', review: '待复核', rejected: '已驳回', error: '异常' } as Record<string, string>)[task.value?.status || ''] || task.value?.status || '—')
const createdText = computed(() => {
  const value = task.value?.created_at
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
})

function modelLabel(role?: string) { return role === 'general_object' ? '人员车辆模型' : '交通标志模型' }

const nodeLabels: Record<string, string> = {
  validate_input: '校验输入', check_image_quality: '图片质量分析', detect_traffic_signs: '调用 YOLO26 视觉工具',
  check_detection_result: '检查检测可信度', retrieve_knowledge: '检索校园知识库', evaluate_risk: '风险研判',
  generate_recommendations: '生成整改建议', generate_report: '生成巡检报告', save_result: '保存巡检记录',
  manual_review: '进入人工复核', handle_error: '异常安全分支',
}

async function refresh() {
  task.value = await getInspection(id)
  trace.value = await getTrace(id)
}

function connectStream() {
  stream?.close()
  stream = new EventSource(inspectionStreamUrl(id))
  stream.addEventListener('step', async () => { await refresh() })
  stream.addEventListener('done', async () => { stream?.close(); await refresh() })
  stream.onerror = () => stream?.close()
}

async function execute() {
  executing.value = true
  try { await executeInspection(id); await refresh(); connectStream() }
  catch (error) { ElMessage.error(errorMessage(error)) }
  finally { executing.value = false }
}

async function confirmReview() {
  try {
    await api.post(`/inspections/${id}/review`, { action: 'confirm', reviewer: '系统管理员', comment: '已人工核对现场与检测结果' })
    ElMessage.success('人工复核已确认')
    await refresh()
  } catch (error) { ElMessage.error(errorMessage(error)) }
}

onMounted(async () => {
  try { await refresh(); if (!finished.value) connectStream() }
  finally { loading.value = false }
})
onBeforeUnmount(() => stream?.close())
</script>

<template>
  <div v-loading="loading" v-if="task" class="standard-page detail-page">
    <section class="task-header content-card">
      <div class="review-heading"><p class="eyebrow">人工复核&nbsp; › &nbsp;证据审查</p><h1>人工复核 <span>证据审查</span></h1><p>{{ task.location }} · {{ task.area_type }} · {{ task.description || '无补充说明' }}</p></div>
      <div class="task-actions"><el-button @click="router.push('/reviews')">返回任务列表</el-button><RiskBadge :level="task.risk_level" /><el-button :loading="executing" @click="execute">重新执行</el-button><el-button v-if="task.review_required" type="primary" @click="confirmReview">人工确认</el-button></div>
    </section>
    <section class="task-meta-strip" aria-label="巡检任务元数据">
      <div><span>任务编号</span><strong>{{ task.task_no }}</strong></div>
      <div><span>事件位置</span><strong>{{ task.location }}</strong></div>
      <div><span>抓拍时间</span><strong>{{ createdText }}</strong></div>
      <div><span>流程状态</span><strong :class="`status-${task.status}`">{{ statusText }}</strong></div>
      <div><span>巡检人员</span><strong>{{ task.inspector_name || '未填写' }}</strong></div>
      <div><span>链路耗时</span><strong>{{ traceDuration ? `${traceDuration.toFixed(0)} ms` : '—' }}</strong></div>
    </section>
    <section class="inspection-grid">
      <div class="detail-main-stack">
        <article class="content-card visual-card">
          <div class="section-title"><div><p class="eyebrow">MULTI-MODEL VISION</p><h3>双模型视觉检测</h3></div><span>{{ task.detections?.length || 0 }} 个目标</span></div>
          <div class="vision-stat-grid">
            <div><span>交通标志</span><strong>{{ trafficSignCount }}</strong><small>校园标志专用模型</small></div>
            <div><span>人员目标</span><strong>{{ personCount }}</strong><small>COCO 通用模型</small></div>
            <div><span>车辆目标</span><strong>{{ vehicleCount }}</strong><small>五类校园车辆</small></div>
            <div><span>通用目标</span><strong>{{ generalObjectCount }}</strong><small>人员与车辆白名单</small></div>
          </div>
          <div class="image-compare">
            <figure><img :src="task.original_image_url" alt="原始巡检图片" /><figcaption>原始图片</figcaption></figure>
            <figure><img :src="task.result_image_url || task.original_image_url" alt="检测结果图片" /><figcaption>蓝色：交通标志 · 绿色：人员车辆</figcaption></figure>
          </div>
        </article>
        <section class="review-evidence-grid">
          <div class="detail-action-stack">
          <article class="content-card trace-card review-trace-card">
            <div class="section-title"><div><p class="eyebrow">WORKFLOW TRACE</p><h3>巡检执行轨迹</h3></div><span class="live-badge" v-if="!finished">● 实时执行</span></div>
            <div class="trace-summary"><div><small>完成节点</small><strong>{{ succeededSteps }}/{{ trace.length }}</strong></div><div><small>链路进度</small><strong>{{ traceProgress }}%</strong></div><div><small>任务耗时</small><strong>{{ traceDuration.toFixed(0) }} ms</strong></div><div><small>复核状态</small><strong>{{ task.review_required ? '待人工确认' : '无需复核' }}</strong></div></div>
            <el-progress :percentage="traceProgress" :show-text="false" :stroke-width="6" />
            <div class="trace-list trace-list-horizontal">
              <div v-for="step in trace" :key="step.id" class="trace-item" :class="step.status">
                <span class="trace-dot" :aria-label="step.status"><el-icon><Check v-if="step.status === 'success'" /><Close v-else-if="step.status === 'error'" /><Loading v-else /></el-icon></span>
                <div><strong>{{ nodeLabels[step.node_name] || step.node_name }}</strong><small>{{ step.duration_ms != null ? `${step.duration_ms.toFixed(0)} ms` : '执行中' }}</small><p v-if="step.error_message">{{ step.error_message }}</p></div>
              </div>
              <el-empty v-if="!trace.length" description="Agent 尚未执行" :image-size="72" />
            </div>
            <div class="trace-context"><div><span>风险研判</span><strong>{{ task.risk_result?.analysis_mode || '等待执行' }}</strong></div><div><span>知识依据</span><strong>{{ task.risk_result?.knowledge_references.length || 0 }} 条</strong></div><div><span>报告归档</span><strong>{{ task.report_id ? '已生成' : '尚未生成' }}</strong></div></div>
          </article>
          <article v-if="task.risk_result" class="content-card recommendation-card">
            <div class="section-title"><div><p class="eyebrow">RECOMMENDED ACTIONS</p><h3>整改建议</h3></div><span>{{ task.risk_result.recommendations.length }} 条</span></div>
            <ol class="recommendations"><li v-for="(item, index) in task.risk_result.recommendations" :key="index"><span>{{ item }}</span></li></ol>
            <p v-if="!task.risk_result.recommendations.length" class="detail-empty-copy">本次研判未返回整改建议，请结合现场证据人工核对。</p>
          </article>
          </div>
          <article class="content-card structured-evidence-card">
            <div class="section-title"><div><p class="eyebrow">STRUCTURED EVIDENCE</p><h3>结构化检测结果</h3></div><span>{{ task.detections?.length || 0 }} 条</span></div>
            <el-table :data="task.detections || []" size="small" empty-text="未检测到目标" max-height="590">
              <el-table-column label="类别"><template #default="scope"><strong>{{ scope.row.display_name || scope.row.class_name }}</strong><small class="class-code">{{ scope.row.class_name }}</small></template></el-table-column>
              <el-table-column label="模型来源" min-width="150"><template #default="scope"><span class="model-source" :class="scope.row.model_role">{{ modelLabel(scope.row.model_role) }}</span><small class="model-file">{{ scope.row.model_name || '兼容旧记录' }}</small></template></el-table-column>
              <el-table-column label="置信度"><template #default="scope">{{ (scope.row.confidence * 100).toFixed(1) }}%</template></el-table-column>
              <el-table-column label="坐标" min-width="180"><template #default="scope"><span class="detection-coordinates">{{ scope.row.bbox_xyxy?.join(', ') }}</span></template></el-table-column>
            </el-table>
            <div v-if="task.vision_events?.length" class="vision-events compact-events">
              <article v-for="event in task.vision_events" :key="event.event_type" class="vision-event-card" :class="event.severity">
                <div class="event-value"><strong>{{ event.object_count }}</strong><span>/ 阈值 {{ event.threshold }}</span></div>
                <div><h4>{{ event.label }}</h4><p>{{ event.evidence }}</p><small>{{ event.requires_video_confirmation ? '静态图片仅形成候选，需结合连续视频确认持续时间' : '规则已满足' }}</small></div>
                <span class="event-status">{{ event.status === 'candidate' ? '待复核' : '已确认' }}</span>
              </article>
            </div>
          </article>
        </section>
        <section v-if="task.report_id" class="content-card report-link"><div><p class="eyebrow">REPORT READY</p><h3>巡检报告已生成并归档</h3></div><el-button type="primary" tag="a" :href="`/api/v1/reports/${task.report_id}/view`" target="_blank">打开报告</el-button></section>
      </div>
      <aside class="detail-side-stack">
        <article v-if="task.risk_result" class="content-card risk-summary">
          <p class="eyebrow">RISK ASSESSMENT</p>
          <div class="score-line"><strong>{{ task.risk_result.risk_score }}</strong><RiskBadge :level="task.risk_result.risk_level" /></div>
          <p class="risk-summary-copy">{{ task.risk_result.problem_summary }}</p>
          <small>分析模式：{{ task.risk_result.analysis_mode }}</small>
        </article>
        <article class="content-card detail-rail-card">
          <div class="detail-rail-title"><p class="eyebrow">KNOWLEDGE BASIS</p><h3>知识依据</h3></div>
          <div class="detail-knowledge-list">
            <details v-for="(item, index) in knowledgeReferences" :key="item.document + item.content" :open="index === 0">
              <summary><strong>{{ item.document }}</strong></summary>
              <p>{{ item.content }}</p>
            </details>
            <p v-if="!knowledgeReferences.length" class="detail-empty-copy">本次研判未返回知识库引用。</p>
          </div>
        </article>
        <article class="content-card detail-rail-card">
          <div class="detail-rail-title"><p class="eyebrow">UNCERTAINTY</p><h3>不确定性说明</h3></div>
          <p class="detail-uncertainty">{{ task.risk_result?.uncertainty_note || '本次任务未记录额外不确定性说明。' }}</p>
        </article>
        <article class="content-card detail-rail-card">
          <div class="detail-rail-title"><p class="eyebrow">MODEL SOURCES</p><h3>本次模型来源</h3></div>
          <div class="detail-model-list"><article v-for="model in detectedModels" :key="model.role + model.name"><strong>{{ model.role }}</strong><span>{{ model.name }}</span></article><p v-if="!detectedModels.length" class="detail-empty-copy">本次任务没有模型检测产出。</p></div>
        </article>
      </aside>
    </section>
  </div>
</template>
