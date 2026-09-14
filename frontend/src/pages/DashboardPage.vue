<script setup lang="ts">
import { computed, onMounted, reactive, ref, type Component } from 'vue'
import { useRouter } from 'vue-router'
import {
  Aim,
  ArrowRight,
  BellFilled,
  CameraFilled,
  Checked,
  CircleCheckFilled,
  Location,
  MapLocation,
  OfficeBuilding,
  TrendCharts,
  VideoCamera,
  WarningFilled,
  ZoomIn,
  ZoomOut,
} from '@element-plus/icons-vue'
import { getDashboard } from '../api'
import campusMap from '../assets/campus-gis-map.png'
import MiniSparkline from '../components/MiniSparkline.vue'
import { campusProfile, formatCoordinate } from '../config/campus'
import type { Dashboard } from '../types'

type IncidentLevel = 'high' | 'medium' | 'low' | 'review' | 'pending'
type MapPinType = 'risk' | 'camera' | 'gate'
type LayerName = 'cameras' | 'risks' | 'gates'
interface Incident {
  id: string
  taskId?: string
  title: string
  location: string
  time: string
  /** 百分比；没有检测结果时为 null，界面显示“—”。 */
  confidence: number | null
  level: IncidentLevel
  image: string
  statusText: string
  statusClass: string
  current?: boolean
}
interface PatrolRow {
  id: string
  name: string
  route: string
  /** null 表示接口没有提供可信进度（执行中的任务）。 */
  progress: number | null
  status: string
  owner: string
}
interface Metric {
  label: string
  value: number | string
  unit: string
  note: string
  tone: 'blue' | 'amber' | 'red' | 'cyan'
  icon: Component
  chart?: number[]
}
interface MapPin {
  id: string
  type: MapPinType
  x: number
  y: number
  title?: string
  subtitle?: string
  level?: IncidentLevel
}

const router = useRouter()
const loading = ref(true)
const apiReady = ref(false)
const loadFailure = ref('')
const dashboard = ref<Dashboard>({ total_tasks: 0, review_required: 0, completed_tasks: 0, risk_counts: {}, recent_tasks: [] })
const selectedIncidentId = ref('')
const queueFilter = ref<'all' | IncidentLevel>('all')
const mapZoom = ref(1)
const mapImageFailed = ref(false)
const campusFocused = ref(false)
const layers = reactive<Record<LayerName, boolean>>({ cameras: false, risks: false, gates: true })
const campusCenterText = formatCoordinate(campusProfile.center.gcj02)
const amapStaticMapUrl = computed(() => {
  const params = new URLSearchParams({
    lng: String(campusProfile.center.gcj02.lng),
    lat: String(campusProfile.center.gcj02.lat),
    zoom: String(campusProfile.defaultZoom),
    width: '1024',
    height: '640',
    traffic: 'false',
  })
  return `/api/v1/maps/static?${params}`
})

const levelLabels: Record<IncidentLevel, string> = { high: '高风险', medium: '中风险', low: '低风险', review: '待复核', pending: '未研判' }
// 门岗与校园地标来自项目校园基准；真实任务当前没有坐标，摄像头也没有业务接口。
const mapPins: MapPin[] = [
  { id: 'gate-north', type: 'gate', x: 43, y: 7, title: '北门' },
  { id: 'gate-west', type: 'gate', x: 4, y: 59, title: '西门' },
  { id: 'gate-south', type: 'gate', x: 39, y: 88, title: '南门' },
]

const incidents = computed<Incident[]>(() => {
  return dashboard.value.recent_tasks.slice(0, 5).map((item, index) => ({
    id: `task-${item.id}`,
    taskId: item.id,
    title: item.description || `${item.area_type}巡检`,
    location: item.location,
    time: formatTime(item.created_at),
    confidence: typeof item.max_confidence === 'number' ? Math.round(item.max_confidence * 100) : null,
    level: normalizeLevel(item.risk_level),
    image: item.result_image_url || item.original_image_url || '',
    statusText: statusLabel(item.status),
    statusClass: statusClass(item.status),
    current: index === 0,
  }))
})
const filteredIncidents = computed(() => queueFilter.value === 'all' ? incidents.value : incidents.value.filter(item => item.level === queueFilter.value))
const visiblePins = computed(() => mapPins.filter(pin => pin.type === 'gate' && layers.gates))
const metrics = computed<Metric[]>(() => {
  if (!apiReady.value) {
    return [
      { label: '今日巡检', value: '—', unit: '', note: '业务接口暂不可用', tone: 'blue', icon: CameraFilled },
      { label: '待复核', value: '—', unit: '', note: '业务接口暂不可用', tone: 'amber', icon: Checked },
      { label: '高风险事件', value: '—', unit: '', note: '业务接口暂不可用', tone: 'red', icon: WarningFilled },
      { label: '在线摄像头', value: '—', unit: '', note: '摄像头接口未接入', tone: 'cyan', icon: VideoCamera },
    ]
  }
  // An older backend (e.g. a stale container image) has no trend fields;
  // show "—" rather than a zero that looks like a real count.
  const trend = dashboard.value.daily_trend
  const totals = trend?.map(point => point.total)
  const reviews = trend?.map(point => point.review_required)
  const highs = trend?.map(point => point.high_risk)
  const missing = '后端未提供趋势数据'
  return [
    { label: '今日巡检', value: dashboard.value.today_tasks ?? '—', unit: dashboard.value.today_tasks == null ? '' : '次', note: totals ? dayOverDay(totals) : missing, tone: 'blue', icon: CameraFilled, chart: totals },
    { label: '待复核', value: dashboard.value.review_required, unit: '条', note: reviews ? `近 7 日 ${sum(reviews)} 条` : missing, tone: 'amber', icon: Checked, chart: reviews },
    { label: '高风险事件', value: dashboard.value.risk_counts.high || 0, unit: '起', note: highs ? `近 7 日 ${sum(highs)} 起` : missing, tone: 'red', icon: WarningFilled, chart: highs },
    { label: '在线摄像头', value: '—', unit: '', note: '摄像头接口未接入', tone: 'cyan', icon: VideoCamera },
  ]
})
const patrolTasks = computed<PatrolRow[]>(() => dashboard.value.recent_tasks.slice(0, 4).map(item => ({
  id: item.id,
  name: item.location,
  route: item.area_type,
  progress: progressOf(item.status),
  status: statusLabel(item.status),
  owner: item.inspector_name || '未填写',
})))

function sum(values: number[]) { return values.reduce((total, value) => total + value, 0) }
function dayOverDay(series: number[]) {
  if (series.length < 2) return '暂无昨日数据'
  const diff = series[series.length - 1] - series[series.length - 2]
  return diff === 0 ? '较昨日 持平' : `较昨日 ${diff > 0 ? '+' : ''}${diff}`
}
function normalizeLevel(level?: string | null): IncidentLevel {
  return level === 'high' || level === 'medium' || level === 'low' || level === 'review' ? level : 'pending'
}
function progressOf(status: string): number | null {
  if (['completed', 'review', 'rejected', 'error'].includes(status)) return 100
  if (status === 'pending' || status === 'queued') return 0
  return null
}
function formatConfidence(value: number | null) { return value == null ? '—' : `${value}%` }
function displayTitle(item: Incident) { return item.title.replace(item.location, '').trim() || item.title }
function formatTime(value: string) { const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleTimeString('zh-CN', { hour12: false }) }
function statusLabel(value: string) { return ({ pending: '待执行', queued: '排队中', running: '执行中', completed: '已完成', review: '待复核', error: '异常', rejected: '已驳回' } as Record<string, string>)[value] || value }
function statusClass(value: string) { return ({ completed: 'completed', review: 'state-review', error: 'state-high', rejected: 'state-high' } as Record<string, string>)[value] || '' }
function selectIncident(item: Incident) {
  selectedIncidentId.value = item.id
  campusFocused.value = false
  if (item.taskId) router.push(`/inspection/${item.taskId}`)
}
function setLayer(name: LayerName, event: Event) { layers[name] = (event.target as HTMLInputElement).checked }
function changeZoom(amount: number) { mapZoom.value = Math.min(1.35, Math.max(1, Number((mapZoom.value + amount).toFixed(2)))) }
function selectMapPin(pin: MapPin) {
  if (pin.type !== 'risk') return
  selectedIncidentId.value = pin.id
  campusFocused.value = false
}
function focusMap() {
  mapZoom.value = 1
  selectedIncidentId.value = ''
  campusFocused.value = true
}
function handleMapImageError() { mapImageFailed.value = true }

onMounted(async () => {
  try { dashboard.value = await getDashboard(); apiReady.value = true }
  catch { loadFailure.value = '无法读取态势数据，请确认后端服务已经启动。' }
  finally { loading.value = false }
})
</script>

<template>
  <div class="command-dashboard" v-loading="loading">
    <h1 class="sr-only">校园交通安全态势总览</h1>
    <div v-if="loadFailure" class="command-error"><el-icon><WarningFilled /></el-icon><span>{{ loadFailure }}</span></div>
    <section class="command-kpis" aria-label="核心态势指标">
      <article v-for="metric in metrics" :key="metric.label" class="command-kpi" :class="`tone-${metric.tone}`">
        <span class="kpi-icon"><el-icon><component :is="metric.icon" /></el-icon></span>
        <div class="kpi-copy"><span>{{ metric.label }}</span><strong>{{ metric.value }} <small v-if="metric.unit">{{ metric.unit }}</small></strong><em>{{ metric.note }}</em></div>
        <MiniSparkline v-if="metric.chart" :data="metric.chart" :color="metric.tone === 'red' ? '#ff4d57' : metric.tone === 'amber' ? '#f59e0b' : metric.tone === 'cyan' ? '#25c7d9' : '#4b8dff'" />
      </article>
    </section>

    <div class="command-body">
      <div class="command-left">
        <section class="gis-panel">
          <div
            class="gis-map"
            :class="{ 'is-campus-centered': campusFocused }"
            :style="{ '--map-zoom': mapZoom }"
            :data-center-lng="campusProfile.center.gcj02.lng"
            :data-center-lat="campusProfile.center.gcj02.lat"
            :aria-label="`${campusProfile.name} GIS 态势地图，默认中心 ${campusCenterText}`"
          >
            <img :src="mapImageFailed ? campusMap : amapStaticMapUrl" :alt="`${campusProfile.name} GIS 态势地图`" @error="handleMapImageError" />
            <div class="map-shade"></div>
            <div class="map-label label-road">学府路</div>
            <div class="map-label label-library">图书馆</div>
            <div class="map-label label-lab">实验楼</div>
            <div class="map-label label-teaching">教学楼 A</div>
            <div class="map-label label-dorm">学生宿舍区</div>
            <div class="map-label label-gym">体育馆</div>

            <button v-for="pin in visiblePins" :key="pin.id" class="map-pin" :aria-label="pin.title || (pin.type === 'camera' ? `摄像头 ${pin.id.replace('camera-', '')}` : pin.id)" :class="[`pin-${pin.type}`, pin.level && `level-${pin.level}`, { selected: selectedIncidentId === pin.id }]" :style="{ left: `${pin.x}%`, top: `${pin.y}%` }" @click="selectMapPin(pin)">
              <span class="pin-symbol"><el-icon><VideoCamera v-if="pin.type === 'camera'" /><OfficeBuilding v-else-if="pin.type === 'gate'" /><Location v-else /></el-icon></span>
              <span v-if="pin.title" class="pin-copy"><strong>{{ pin.title }}</strong><small v-if="pin.subtitle">{{ pin.subtitle }}</small></span>
            </button>

            <aside class="map-layers">
              <strong>图层</strong>
              <label class="is-disabled" title="摄像头接口未接入"><input type="checkbox" disabled /><span><el-icon><VideoCamera /></el-icon>摄像头</span></label>
              <label class="is-disabled" title="真实任务暂无地图坐标"><input type="checkbox" disabled /><span><el-icon><Location /></el-icon>风险事件</span></label>
              <label><input type="checkbox" :checked="layers.gates" @change="setLayer('gates', $event)" /><span><el-icon><OfficeBuilding /></el-icon>门岗</span></label>
              <label class="is-disabled" title="重点区域图层未接入"><input type="checkbox" disabled /><span><el-icon><MapLocation /></el-icon>重点区域</span></label>
            </aside>

            <div class="map-controls">
              <button title="放大" @click="changeZoom(.1)"><el-icon><ZoomIn /></el-icon></button>
              <button title="缩小" @click="changeZoom(-.1)"><el-icon><ZoomOut /></el-icon></button>
              <button :title="`回到 ${campusProfile.name} 默认中心`" :aria-label="`回到 ${campusProfile.name} 默认中心`" @click="focusMap"><el-icon><Aim /></el-icon></button>
            </div>
            <button class="map-campus-profile" :title="campusProfile.address" @click="focusMap">
              <span class="campus-profile-icon"><el-icon><MapLocation /></el-icon></span>
              <span class="campus-profile-copy">
                <strong>{{ campusProfile.name }}</strong>
                <small>GCJ-02 默认中心 · {{ campusCenterText }}</small>
              </span>
            </button>
            <span class="map-mode"><i></i>{{ mapImageFailed ? '校园 GIS 备用图' : '高德底图 · 校园基准' }}</span>
          </div>
        </section>

        <div class="command-tables">
          <section class="ops-panel patrol-panel">
            <header><h2>巡检任务 <span>({{ patrolTasks.length }})</span></h2><div class="panel-actions"><button @click="router.push('/inspections')">查看全部</button></div></header>
            <div class="ops-table">
              <div class="ops-row ops-head"><span>任务名称</span><span>路线/区域</span><span>进度</span><span>状态</span><span>负责人</span></div>
              <div v-for="task in patrolTasks" :key="task.id" class="ops-row">
                <strong>{{ task.name }}</strong><span>{{ task.route }}</span>
                <div class="progress-cell"><i><b :style="{ width: `${task.progress ?? 0}%` }"></b></i><span>{{ task.progress == null ? '—' : `${task.progress}%` }}</span></div>
                <em :class="{ completed: task.status === '已完成' }">{{ task.status }}</em><span>{{ task.owner }}</span>
              </div>
              <div v-if="!patrolTasks.length" class="ops-empty">暂无真实巡检任务</div>
            </div>
          </section>

          <section class="ops-panel detection-panel">
            <header><h2>近期检测 <span>({{ incidents.length }})</span></h2><span class="panel-source">巡检档案实时汇总</span></header>
            <div class="ops-table">
              <div class="ops-row ops-head"><span>时间</span><span>事件类型</span><span>位置</span><span>置信度</span><span>处置状态</span></div>
              <div v-for="item in incidents" :key="item.id" class="ops-row" @click="selectIncident(item)">
                <span>{{ item.time }}</span><strong><i :class="`risk-dot ${item.level}`"></i>{{ displayTitle(item) }}</strong><span>{{ item.location }}</span><span>{{ formatConfidence(item.confidence) }}</span><em :class="item.statusClass">{{ item.statusText }}</em>
              </div>
              <div v-if="!incidents.length" class="ops-empty">执行巡检后自动汇总识别结果</div>
            </div>
          </section>
        </div>
      </div>

      <aside class="incident-queue">
        <header><div><h2>风险事件队列 <span>({{ incidents.length }})</span></h2><small>来自后端真实巡检任务</small></div><el-select v-model="queueFilter" size="small" aria-label="按风险等级筛选事件"><el-option label="按风险等级" value="all" /><el-option label="仅高风险" value="high" /><el-option label="仅中风险" value="medium" /><el-option label="仅低风险" value="low" /><el-option label="仅待复核" value="review" /></el-select></header>
        <div class="incident-list">
          <article v-for="item in filteredIncidents" :key="item.id" :class="[`level-${item.level}`, { selected: selectedIncidentId === item.id }]" @click="selectIncident(item)">
            <div class="incident-info">
              <div class="incident-title"><el-icon><BellFilled /></el-icon><strong>{{ item.title }}</strong><span>{{ levelLabels[item.level] }}</span></div>
              <dl><div><dt><el-icon><Location /></el-icon></dt><dd>{{ item.location }}</dd></div><div><dt><el-icon><TrendCharts /></el-icon></dt><dd>{{ item.time }}</dd></div><div><dt><el-icon><CircleCheckFilled /></el-icon></dt><dd>置信度&nbsp; <strong>{{ formatConfidence(item.confidence) }}</strong></dd></div></dl>
            </div>
            <figure v-if="item.image"><img :src="item.image" :alt="item.location" /><figcaption v-if="item.current">当前事件</figcaption></figure>
          </article>
          <div v-if="!filteredIncidents.length" class="queue-empty"><strong>暂无匹配事件</strong><span>新巡检结果会从后端自动进入此队列。</span></div>
        </div>
        <button class="queue-footer" @click="router.push('/inspections')">查看全部事件<el-icon><ArrowRight /></el-icon></button>
      </aside>
    </div>
  </div>
</template>
