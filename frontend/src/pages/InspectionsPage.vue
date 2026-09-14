<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage, getInspections } from '../api'
import RiskBadge from '../components/RiskBadge.vue'
import DataChart from '../components/DataChart.vue'
import type { EChartsCoreOption } from 'echarts/core'
import type { Inspection } from '../types'

const router = useRouter()
const items = ref<Inspection[]>([])
const loading = ref(false)
const loadFailure = ref('')
const filters = reactive({ status: '', risk_level: '' })
const statusLabels: Record<string, string> = { pending: '待执行', running: '运行中', completed: '已完成', review: '待复核', error: '异常', rejected: '已驳回' }
const visibleItems = computed(() => items.value.filter(item => (!filters.status || item.status === filters.status) && (!filters.risk_level || item.risk_level === filters.risk_level)))
const page = ref(1)
const pageSize = 10
const pagedItems = computed(() => visibleItems.value.slice((page.value - 1) * pageSize, page.value * pageSize))
watch(visibleItems, () => { page.value = 1 })
const summary = computed(() => ({
  total: visibleItems.value.length,
  high: visibleItems.value.filter(item => item.risk_level === 'high').length,
  review: visibleItems.value.filter(item => item.review_required).length,
  completed: visibleItems.value.filter(item => item.status === 'completed').length,
}))
const completionRate = computed(() => items.value.length ? Math.round(items.value.filter(item => item.status === 'completed').length / items.value.length * 100) : 0)
const averageDuration = computed(() => {
  const values = items.value.map(item => item.total_duration_ms).filter((value): value is number => typeof value === 'number')
  return values.length ? Math.round(values.reduce((sum, value) => sum + value, 0) / values.length) : 0
})
const statusDistribution = computed(() => ['completed', 'review', 'running', 'pending', 'error'].map(status => ({
  status,
  label: statusLabels[status],
  count: items.value.filter(item => item.status === status).length,
})).filter(item => item.count > 0))
const areaCoverage = computed(() => Array.from(new Set(items.value.map(item => item.area_type).filter(Boolean))).map(area => ({
  area,
  count: items.value.filter(item => item.area_type === area).length,
})))
const durationTasks = computed(() => visibleItems.value.filter(item => typeof item.total_duration_ms === 'number').slice(0, 12).reverse())
const designTokens = getComputedStyle(document.documentElement)
const chartColors = {
  text: designTokens.getPropertyValue('--text-2').trim(),
  line: designTokens.getPropertyValue('--line').trim(),
  soft: designTokens.getPropertyValue('--line-soft').trim(),
  blue: designTokens.getPropertyValue('--blue').trim(),
  font: designTokens.getPropertyValue('--font-ui').trim(),
}
const durationOption = computed<EChartsCoreOption>(() => ({
  aria: { enabled: true },
  textStyle: { fontFamily: chartColors.font },
  tooltip: { trigger: 'axis', valueFormatter: (value: unknown) => `${Number(value).toFixed(1)} 秒` },
  grid: { left: 50, right: 20, top: 20, bottom: 36 },
  xAxis: { type: 'category', data: durationTasks.value.map(item => item.task_no.slice(-6)), axisLabel: { color: chartColors.text, fontSize: 12 }, axisLine: { lineStyle: { color: chartColors.line } } },
  yAxis: { type: 'value', name: '秒', nameTextStyle: { color: chartColors.text }, axisLabel: { color: chartColors.text }, splitLine: { lineStyle: { color: chartColors.soft } } },
  series: [{ type: 'bar', data: durationTasks.value.map(item => Number(((item.total_duration_ms || 0) / 1000).toFixed(2))), itemStyle: { color: chartColors.blue, borderRadius: [3, 3, 0, 0] }, barMaxWidth: 36 }],
}))

async function load() {
  loading.value = true
  loadFailure.value = ''
  try {
    const result = await getInspections()
    items.value = result.items
  } catch (error) {
    items.value = []
    loadFailure.value = errorMessage(error)
  } finally { loading.value = false }
}
function openTask(row: Inspection) {
  router.push(`/inspection/${row.id}`)
}
function clearFilters() {
  filters.status = ''
  filters.risk_level = ''
}
onMounted(load)
</script>

<template>
  <div class="standard-page">
    <section class="page-toolbar">
      <div><p class="page-kicker">巡检档案</p><h1>历史巡检记录</h1><p>集中查询每次巡检的现场证据、风险结论、执行轨迹与归档状态。</p></div>
      <el-button type="primary" @click="router.push('/inspection/new')">新建巡检</el-button>
    </section>
    <section class="archive-summary">
      <article><span>当前记录</span><strong>{{ summary.total }}</strong><small>条任务</small></article>
      <article><span>高风险</span><strong class="danger">{{ summary.high }}</strong><small>优先处置</small></article>
      <article><span>待复核</span><strong class="warning">{{ summary.review }}</strong><small>人工确认</small></article>
      <article><span>已完成</span><strong class="success">{{ summary.completed }}</strong><small>闭环归档</small></article>
    </section>
    <div v-if="loadFailure" class="inline-error">档案接口加载失败：{{ loadFailure }}</div>
    <div class="archive-workbench">
      <main class="archive-primary">
      <section class="content-card archive-card">
        <div class="section-title compact"><div><h3>任务列表</h3><p>点击任务可查看后端保存的完整巡检详情</p></div><div class="filter-row"><el-select v-model="filters.status" clearable placeholder="任务状态" aria-label="按任务状态筛选"><el-option label="已完成" value="completed" /><el-option label="待复核" value="review" /><el-option label="运行中" value="running" /></el-select><el-select v-model="filters.risk_level" clearable placeholder="风险等级" aria-label="按风险等级筛选"><el-option label="低风险" value="low" /><el-option label="中风险" value="medium" /><el-option label="高风险" value="high" /><el-option label="待复核" value="review" /></el-select></div></div>
        <div class="archive-table">
          <el-table v-loading="loading" :data="pagedItems" empty-text="暂无符合条件的巡检任务" @row-click="openTask">
            <el-table-column prop="task_no" label="任务编号" min-width="150" />
            <el-table-column prop="location" label="地点" min-width="145" />
            <el-table-column prop="area_type" label="区域" width="112" />
            <el-table-column label="风险" width="92"><template #default="scope"><RiskBadge :level="scope.row.risk_level" /></template></el-table-column>
            <el-table-column label="状态" width="92"><template #default="scope"><span class="status-text" :class="`status-${scope.row.status}`">{{ statusLabels[scope.row.status] || scope.row.status }}</span></template></el-table-column>
            <el-table-column label="耗时" width="100"><template #default="scope">{{ scope.row.total_duration_ms == null ? '—' : `${Math.round(scope.row.total_duration_ms)} ms` }}</template></el-table-column>
            <el-table-column prop="created_at" label="创建时间" min-width="150" />
          </el-table>
        </div>
        <div class="mobile-archive-list">
          <article v-for="item in pagedItems" :key="item.id" tabindex="0" @click="openTask(item)" @keydown.enter="openTask(item)">
            <div><strong>{{ item.location }}</strong><RiskBadge :level="item.risk_level" /></div>
            <p>{{ item.task_no }} · {{ item.area_type }}</p>
            <footer><span :class="`status-${item.status}`">{{ statusLabels[item.status] || item.status }}</span><small>{{ item.total_duration_ms == null ? '耗时 —' : `${Math.round(item.total_duration_ms)} ms` }} · {{ item.created_at }}</small></footer>
          </article>
          <el-empty v-if="!visibleItems.length" description="暂无符合条件的巡检任务" :image-size="58" />
        </div>
        <footer class="archive-list-footer"><span>当前筛选 {{ visibleItems.length }} 条 · 点击记录查看证据与报告</span><el-pagination v-model:current-page="page" :page-size="pageSize" :total="visibleItems.length" layout="prev, pager, next" aria-label="巡检档案分页" /></footer>
      </section>
      <section class="content-card archive-duration-card"><div class="section-title"><div><p class="eyebrow">TASK LATENCY</p><h3>近期任务执行耗时</h3></div><span>当前筛选中最近 {{ durationTasks.length }} 条有耗时记录的任务</span></div><DataChart :option="durationOption" :empty="!durationTasks.length" :ariaLabel="'近期真实巡检执行耗时柱状图'" /><p class="chart-insight">耗时来自后端任务记录；历史基线与新版本任务可能混合，不作为模型准确率或性能提升的证明。</p></section>
      </main>
      <aside class="archive-rail">
        <section class="content-card rail-card completion-card">
          <div class="rail-heading"><div><strong>闭环完成度</strong><span>{{ summary.completed }} / {{ items.length }} 已归档</span></div><b>{{ completionRate }}%</b></div>
          <el-progress :percentage="completionRate" :show-text="false" :stroke-width="7" />
          <div class="rail-metrics"><span><small>平均任务耗时</small><strong>{{ averageDuration }} ms</strong></span><span><small>覆盖区域</small><strong>{{ areaCoverage.length }} 类</strong></span></div>
        </section>
        <section class="content-card rail-card">
          <div class="rail-heading"><div><strong>状态分布</strong><span>点击即可筛选任务</span></div><el-button text size="small" @click="clearFilters">重置</el-button></div>
          <div class="status-filter-list"><button v-for="item in statusDistribution" :key="item.status" type="button" :class="{ active: filters.status === item.status }" @click="filters.status = filters.status === item.status ? '' : item.status"><span :class="`status-${item.status}`">{{ item.label }}</span><strong>{{ item.count }}</strong></button></div>
        </section>
        <section class="content-card rail-card">
          <div class="rail-heading"><div><strong>区域覆盖</strong><span>按档案中的真实区域统计</span></div></div>
          <div class="area-coverage-list"><span v-for="item in areaCoverage" :key="item.area"><strong>{{ item.area }}</strong><small>{{ item.count }} 条</small></span></div>
        </section>
        <section class="content-card rail-card archive-capability-card">
          <div class="rail-heading"><div><strong>单份档案内容</strong><span>完整保留巡检证据链</span></div></div>
          <ul><li>原始图像与标注结果</li><li>双模型目标识别明细</li><li>Agent 节点执行轨迹</li><li>风险依据、建议与报告</li></ul>
        </section>
      </aside>
    </div>
  </div>
</template>
