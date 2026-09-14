<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, CircleCheck, Clock, Collection, DataAnalysis, Picture, Tickets, UploadFilled, VideoPlay } from '@element-plus/icons-vue'
import { api, errorMessage, executeInspection, getInspections } from '../api'
import type { Inspection } from '../types'
import ModelEvidencePanel from '../components/ModelEvidencePanel.vue'

interface VideoEvent {
  event_type: string
  label: string
  evidence: string
  severity: string
  track_id?: number
}

interface VideoAnalyticsResult {
  result_video_url: string
  processed_frames: number
  frame_stride: number
  max_people_in_frame: number
  max_vehicles_in_frame: number
  unique_people_tracks: number
  unique_vehicle_tracks: number
  wrong_way_count: number
  tracker: string
  model_name: string
  allowed_direction_label: string
  duration_ms: number
  events: VideoEvent[]
}

const router = useRouter()
const form = reactive({ location: '', area_type: '校门口', description: '', inspector_name: '' })
const mode = ref<'image' | 'video'>('image')
const allowedDirection = ref('left_to_right')
const file = ref<File>()
const preview = ref('')
const submitting = ref(false)
const analysisSeconds = ref(0)
const videoResult = ref<VideoAnalyticsResult>()
const recentTasks = ref<Inspection[]>([])
const runtime = ref<Record<string, any>>()
const areas = ['校门口', '停车场', '校园主干道', '宿舍区', '食堂周边', '教学楼路口', '消防通道', '其他']
const directions = [
  { value: 'left_to_right', label: '从左向右' },
  { value: 'right_to_left', label: '从右向左' },
  { value: 'top_to_bottom', label: '从上向下' },
  { value: 'bottom_to_top', label: '从下向上' },
]
const workflowSteps = computed(() => mode.value === 'video'
  ? ['输入与视频校验', '等比缩放与采样', 'YOLO26 人员车辆识别', 'ByteTrack 连续轨迹', '聚集与方向规则', '结果视频与事件展示']
  : ['输入与文件校验', '图片质量检查', '双 YOLO26 视觉识别', '校园知识检索', '旁挂视觉证据（受隐私闸门约束）', 'DeepSeek 风险研判', '人工复核与报告归档'])
const readinessItems = computed(() => [
  { label: '巡检地点', hint: form.location.trim() || '等待填写具体位置', done: Boolean(form.location.trim()) },
  { label: mode.value === 'video' ? '巡检视频' : '巡检图片', hint: file.value?.name || '等待选择现场文件', done: Boolean(file.value) },
  { label: mode.value === 'video' ? '允许方向' : '区域类型', hint: mode.value === 'video' ? directions.find(item => item.value === allowedDirection.value)?.label || '' : form.area_type, done: true },
])
const readinessCount = computed(() => readinessItems.value.filter(item => item.done).length)
const activeCapabilities = computed(() => mode.value === 'video'
  ? ['人员与五类车辆', 'ByteTrack 连续轨迹', '人员聚集候选', '逆行方向规则']
  : ['TT100K 交通标志', '人员与五类车辆', '人员聚集候选', '知识增强研判'])
const runtimeItems = computed(() => [
  { label: '交通标志模型', value: runtime.value?.services?.yolo?.configured ? runtime.value.services.yolo.model_name : '未配置', ready: Boolean(runtime.value?.services?.yolo?.configured) },
  { label: '人员车辆模型', value: runtime.value?.services?.general_yolo?.configured ? runtime.value.services.general_yolo.model_name : '未配置', ready: Boolean(runtime.value?.services?.general_yolo?.configured) },
  { label: '知识检索', value: runtime.value?.services?.qdrant?.status === 'ok' ? 'Qdrant 就绪' : '状态未知', ready: runtime.value?.services?.qdrant?.status === 'ok' },
  { label: '旁挂视觉研判', value: !runtime.value?.services?.vision_llm ? '状态未知' : runtime.value.services.vision_llm.enabled ? runtime.value.services.vision_llm.model || '未配置' : '已关闭', ready: Boolean(runtime.value?.services?.vision_llm?.enabled && runtime.value?.services?.vision_llm?.configured) },
  { label: '风险研判', value: runtime.value?.services?.llm?.configured ? runtime.value.services.llm.model : '未配置', ready: Boolean(runtime.value?.services?.llm?.configured) },
])
const fileDetails = computed(() => file.value ? [
  { label: '文件类型', value: file.value.type || '浏览器未提供' },
  { label: '文件大小', value: `${(file.value.size / 1024 / 1024).toFixed(2)} MB` },
  { label: '分析模式', value: mode.value === 'video' ? '连续轨迹分析' : '静态证据分析' },
] : [])

function changeMode(next: 'image' | 'video') {
  mode.value = next
  file.value = undefined
  videoResult.value = undefined
  if (preview.value) URL.revokeObjectURL(preview.value)
  preview.value = ''
}

function selectFile(event: Event) {
  const selected = (event.target as HTMLInputElement).files?.[0]
  if (!selected) return
  file.value = selected
  if (preview.value) URL.revokeObjectURL(preview.value)
  preview.value = URL.createObjectURL(selected)
}

async function submit() {
  if (!form.location.trim() || !file.value) return ElMessage.warning(`请填写地点并选择巡检${mode.value === 'video' ? '视频' : '图片'}`)
  submitting.value = true
  analysisSeconds.value = 0
  const analysisTimer = mode.value === 'video'
    ? window.setInterval(() => { analysisSeconds.value += 1 }, 1_000)
    : undefined
  try {
    const body = new FormData()
    body.append('file', file.value)
    if (mode.value === 'video') {
      body.append('location', form.location)
      body.append('allowed_direction', allowedDirection.value)
      videoResult.value = (await api.post('/video-analytics', body, { timeout: 600_000 })).data
      ElMessage.success('视频跟踪分析完成')
    } else {
      Object.entries(form).forEach(([key, value]) => value && body.append(key, value))
      const task = (await api.post('/inspections', body)).data
      await executeInspection(task.id)
      ElMessage.success('巡检任务已启动')
      await router.push(`/inspection/${task.id}`)
    }
  } catch (error) {
    ElMessage.error(errorMessage(error))
  } finally {
    if (analysisTimer !== undefined) window.clearInterval(analysisTimer)
    submitting.value = false
  }
}

function formatTaskTime(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false })
}

onMounted(async () => {
  await Promise.all([
    getInspections().then(result => { recentTasks.value = result.items.slice(0, 5) }).catch(() => { recentTasks.value = [] }),
    api.get('/health').then(response => { runtime.value = response.data }).catch(() => { runtime.value = undefined }),
  ])
})
</script>

<template>
  <div class="standard-page">
    <section class="page-toolbar">
      <div><p class="page-kicker">智能识别任务</p><h1>创建现场巡检</h1><p>图片支持双模型识别与人员聚集候选；视频通过 ByteTrack 连续轨迹分析人员聚集和逆行。</p></div>
    </section>
    <section class="inspection-context-bar" aria-label="巡检运行链路状态">
      <div v-for="item in runtimeItems" :key="item.label" :class="{ ready: item.ready }"><i></i><span>{{ item.label }}</span><strong>{{ item.value }}</strong></div>
    </section>
    <div class="inspection-workbench">
      <main class="inspection-primary">
        <el-radio-group :model-value="mode" class="inspection-mode-switch" @change="changeMode($event as 'image' | 'video')">
          <el-radio-button value="image">图片智能巡检</el-radio-button>
          <el-radio-button value="video">视频轨迹分析</el-radio-button>
        </el-radio-group>
        <div class="two-column-form">
          <section class="content-card form-card">
            <div class="section-title"><div><p class="eyebrow">NEW INSPECTION</p><h3>填写巡检任务</h3></div><span>步骤 1 / 2</span></div>
            <el-form label-position="top" :model="form">
              <el-form-item label="巡检地点（必填）"><el-input v-model="form.location" placeholder="例如：学校大门东侧入口" /></el-form-item>
              <el-form-item label="区域类型"><el-select v-model="form.area_type" class="block-select" aria-label="区域类型"><el-option v-for="area in areas" :key="area" :label="area" :value="area" /></el-select></el-form-item>
              <template v-if="mode === 'image'">
                <el-form-item label="现场说明"><el-input v-model="form.description" type="textarea" :rows="4" placeholder="记录遮挡、车流、拍摄角度等现场信息" /></el-form-item>
                <el-form-item label="巡检人员"><el-input v-model="form.inspector_name" placeholder="选填" /></el-form-item>
              </template>
              <el-form-item v-else label="道路允许通行方向（用于逆行判断）">
                <el-select v-model="allowedDirection" class="block-select" aria-label="道路允许通行方向"><el-option v-for="item in directions" :key="item.value" :label="item.label" :value="item.value" /></el-select>
              </el-form-item>
            </el-form>
            <div class="guardrail-note"><strong>智能体边界</strong><p v-if="mode === 'image'">静态图片可以统计人员，但只能形成聚集候选；风险结论仍需地点、知识依据和人工复核。</p><p v-else>逆行必须依据连续目标轨迹判断。道路方向设置错误会直接影响结果，所有事件仍需人工核对。</p></div>
          </section>
          <section class="content-card upload-card">
            <div class="section-title upload-title"><div><p class="eyebrow">FIELD EVIDENCE</p><h3>上传现场证据</h3></div><span>步骤 2 / 2</span></div>
            <div class="upload-zone" :class="{ filled: preview }">
              <img v-if="preview && mode === 'image'" :src="preview" alt="巡检图片预览" />
              <video v-else-if="preview" :src="preview" controls muted aria-label="巡检视频预览"></video>
              <div v-else><span class="upload-icon"><el-icon><UploadFilled /></el-icon></span><h3>上传巡检{{ mode === 'video' ? '视频' : '图片' }}</h3><p>{{ mode === 'video' ? '支持 MP4、AVI、MOV、MKV、WebM，最大 100 MB' : '支持 JPG、PNG、BMP、WebP，最大 20 MB' }}</p></div>
              <input v-if="mode === 'image'" type="file" accept="image/jpeg,image/png,image/bmp,image/webp" aria-label="选择巡检现场图片" @change="selectFile" />
              <input v-else type="file" accept="video/mp4,video/avi,video/quicktime,video/x-matroska,video/webm" aria-label="选择巡检现场视频" @change="selectFile" />
            </div>
            <div class="upload-meta" v-if="file"><span>{{ file.name }}</span><span>{{ (file.size / 1024 / 1024).toFixed(2) }} MB</span></div>
            <div v-if="fileDetails.length" class="evidence-facts"><span v-for="item in fileDetails" :key="item.label"><small>{{ item.label }}</small><strong>{{ item.value }}</strong></span></div>
            <el-button class="primary-action" type="primary" size="large" :loading="submitting" @click="submit">{{ submitting && mode === 'video' ? `正在逐帧分析 · ${analysisSeconds}s` : mode === 'video' ? '开始视频轨迹分析' : '开始智能巡检' }}</el-button>
            <p v-if="submitting && mode === 'video'" class="video-analysis-hint">正在上传并执行 YOLO26m + ByteTrack。4K 视频会自动等比缩放后分析，请勿重复提交。</p>
            <p class="privacy-hint">演示{{ mode === 'video' ? '视频' : '图片' }}请避开或脱敏清晰人脸、车牌等个人信息。</p>
          </section>
        </div>
        <section v-if="videoResult" class="content-card video-result-panel">
          <div class="section-title"><div><p class="eyebrow">TRACKING RESULT</p><h3>视频轨迹分析结果</h3></div><span>{{ videoResult.model_name }} · {{ videoResult.tracker }}</span></div>
          <div class="video-result-grid">
            <video :src="videoResult.result_video_url" controls muted aria-label="视频轨迹分析结果"></video>
            <div>
              <div class="video-metrics">
                <div><span>最大同帧人数</span><strong>{{ videoResult.max_people_in_frame }}</strong></div>
                <div><span>人员轨迹</span><strong>{{ videoResult.unique_people_tracks }}</strong></div>
                <div><span>车辆轨迹</span><strong>{{ videoResult.unique_vehicle_tracks }}</strong></div>
                <div><span>逆行轨迹</span><strong>{{ videoResult.wrong_way_count }}</strong></div>
              </div>
              <p class="video-rule-summary">允许方向：{{ videoResult.allowed_direction_label }} · 已分析 {{ videoResult.processed_frames }} 帧 · 间隔 {{ videoResult.frame_stride }} 帧采样</p>
              <div class="video-event-list">
                <article v-for="event in videoResult.events" :key="`${event.event_type}-${event.track_id || 0}`" :class="event.severity"><strong>{{ event.label }}</strong><p>{{ event.evidence }}</p><span>需人工复核</span></article>
                <el-empty v-if="!videoResult.events.length" description="未触发人员聚集或逆行规则" :image-size="58" />
              </div>
            </div>
          </div>
        </section>
        <section class="content-card recent-inspections-panel">
          <div class="section-title"><div><p class="eyebrow">RECENT TASKS</p><h3>最近真实巡检</h3></div><el-button text @click="router.push('/inspections')">查看全部<el-icon><ArrowRight /></el-icon></el-button></div>
          <div class="recent-inspection-grid">
            <article v-for="item in recentTasks" :key="item.id" tabindex="0" @click="router.push(`/inspection/${item.id}`)" @keydown.enter="router.push(`/inspection/${item.id}`)"><span class="recent-task-icon"><el-icon><Clock /></el-icon></span><div><strong>{{ item.location }}</strong><p>{{ item.area_type }} · {{ formatTaskTime(item.created_at) }}</p></div><em :class="`status-${item.status}`">{{ item.status === 'review' ? '待复核' : item.status === 'completed' ? '已完成' : item.status === 'running' ? '运行中' : item.status }}</em></article>
            <div v-if="!recentTasks.length" class="recent-empty">暂无巡检记录，提交首个现场文件后将在这里显示。</div>
          </div>
        </section>
        <ModelEvidencePanel v-if="mode === 'image'" :services="runtime?.services" />
      </main>
      <aside class="inspection-rail">
        <section class="content-card rail-card readiness-card">
          <div class="rail-heading"><el-icon><CircleCheck /></el-icon><div><strong>提交准备度</strong><span>{{ readinessCount }} / 3 已就绪</span></div></div>
          <el-progress :percentage="Math.round(readinessCount / 3 * 100)" :show-text="false" :stroke-width="6" />
          <div class="readiness-list"><div v-for="item in readinessItems" :key="item.label" :class="{ done: item.done }"><el-icon><CircleCheck /></el-icon><span><strong>{{ item.label }}</strong><small>{{ item.hint }}</small></span></div></div>
        </section>
        <section class="content-card rail-card workflow-card">
          <div class="rail-heading"><el-icon><Tickets /></el-icon><div><strong>智能体执行链</strong><span>提交后自动完成</span></div></div>
          <ol class="workflow-list"><li v-for="(step, index) in workflowSteps" :key="step"><span>{{ index + 1 }}</span><strong>{{ step }}</strong></li></ol>
        </section>
        <section class="content-card rail-card capability-card">
          <div class="rail-heading"><el-icon><DataAnalysis /></el-icon><div><strong>当前识别范围</strong><span>{{ mode === 'video' ? '视频轨迹模式' : '静态图片模式' }}</span></div></div>
          <div class="capability-list"><span v-for="item in activeCapabilities" :key="item"><el-icon><Collection /></el-icon>{{ item }}</span></div>
        </section>
        <section class="content-card rail-card evidence-policy-card">
          <div class="rail-heading"><el-icon><Picture v-if="mode === 'image'" /><VideoPlay v-else /></el-icon><div><strong>证据使用说明</strong><span>与后端校验规则一致</span></div></div>
          <ul><li>现场文件仅在提交后上传到后端</li><li>模型结果保留置信度与检测框</li><li>高风险和不确定结果进入人工复核</li></ul>
        </section>
      </aside>
    </div>
  </div>
</template>
