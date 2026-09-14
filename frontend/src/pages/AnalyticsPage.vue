<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  DataAnalysis,
  Histogram,
  Location,
  PieChart,
  Refresh,
  Stopwatch,
  TrendCharts,
  WarningFilled,
} from '@element-plus/icons-vue'
import type { EChartsCoreOption } from 'echarts/core'
import { errorMessage, getAnalyticsOverview } from '../api'
import DataChart from '../components/DataChart.vue'
import type { AnalyticsOverview } from '../types'

const router = useRouter()
const loading = ref(true)
const failure = ref('')
const analytics = ref<AnalyticsOverview>({
  summary: {
    total_tasks: 0,
    completed_tasks: 0,
    review_required: 0,
    completion_rate: 0,
    review_rate: 0,
    average_duration_ms: 0,
  },
  daily_trend: [],
  risk_counts: {},
  status_counts: {},
  area_breakdown: [],
  review_reason_counts: [],
  model_breakdown: [],
  class_breakdown: [],
  agent_performance: [],
})

// Read the same design tokens as the application shell.
const tokens = getComputedStyle(document.documentElement)
const palette = {
  blue: tokens.getPropertyValue('--blue').trim(),
  cyan: tokens.getPropertyValue('--cyan').trim(),
  green: tokens.getPropertyValue('--green').trim(),
  amber: tokens.getPropertyValue('--amber').trim(),
  red: tokens.getPropertyValue('--red').trim(),
  purple: tokens.getPropertyValue('--purple').trim(),
  text: tokens.getPropertyValue('--text-2').trim(),
  muted: tokens.getPropertyValue('--text-3').trim(),
  line: tokens.getPropertyValue('--line-soft').trim(),
}
const riskLabels: Record<string, string> = {
  high: '高风险',
  medium: '中风险',
  low: '低风险',
  review: '待复核',
  pending: '未研判',
}
const riskColors: Record<string, string> = {
  high: palette.red,
  medium: palette.amber,
  low: palette.green,
  review: palette.purple,
  pending: palette.muted,
}
const nodeLabels: Record<string, string> = {
  validate_input: '输入校验',
  check_image_quality: '图片质量',
  detect_traffic_signs: '双模型检测',
  check_detection_result: '可信度检查',
  retrieve_knowledge: '知识检索',
  evaluate_risk: '风险研判',
  generate_recommendations: '整改建议',
  generate_report: '报告生成',
  save_result: '结果保存',
  manual_review: '复核护栏',
  handle_error: '异常分支',
}

const hasTasks = computed(() => analytics.value.summary.total_tasks > 0)
const completionGap = computed(() => Math.max(0, analytics.value.summary.total_tasks - analytics.value.summary.completed_tasks))
const leadingArea = computed(() => analytics.value.area_breakdown[0])
const leadingReason = computed(() => analytics.value.review_reason_counts[0])
const leadingClass = computed(() => analytics.value.class_breakdown[0])
const slowestNode = computed(() => analytics.value.agent_performance[0])
const totalDetections = computed(() => analytics.value.model_breakdown.reduce((sum, item) => sum + item.detection_count, 0))
const activeDays = computed(() => analytics.value.daily_trend.filter(item => item.total > 0).length)

const baseTooltip = {
  trigger: 'axis',
  backgroundColor: '#101f2f',
  borderColor: palette.line,
  textStyle: { color: '#dce8f5', fontSize: 12 },
  axisPointer: { type: 'shadow' },
}
const axisLine = { lineStyle: { color: palette.line } }
const splitLine = { lineStyle: { color: '#172b3d' } }
const axisLabel = { color: palette.muted, fontSize: 12 }

const trendOption = computed<EChartsCoreOption>(() => ({
  animationDuration: 450,
  aria: { enabled: true, decal: { show: false } },
  color: [palette.blue, palette.purple, palette.red],
  tooltip: { ...baseTooltip, trigger: 'axis' },
  legend: { top: 0, right: 0, textStyle: { color: palette.text, fontSize: 12 }, itemWidth: 12, itemHeight: 6 },
  grid: { left: 38, right: 15, top: 42, bottom: 25 },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: analytics.value.daily_trend.map(item => formatDate(item.date)),
    axisLine,
    axisTick: { show: false },
    axisLabel,
  },
  yAxis: { type: 'value', minInterval: 1, axisLine: { show: false }, axisTick: { show: false }, axisLabel, splitLine },
  series: [
    { name: '巡检任务', type: 'line', smooth: .25, showSymbol: false, data: analytics.value.daily_trend.map(item => item.total), lineStyle: { width: 2 }, areaStyle: { opacity: .08 } },
    { name: '待复核', type: 'line', smooth: .25, showSymbol: false, data: analytics.value.daily_trend.map(item => item.review_required), lineStyle: { width: 1.5 } },
    { name: '高风险', type: 'line', smooth: .25, showSymbol: false, data: analytics.value.daily_trend.map(item => item.high_risk), lineStyle: { width: 1.5 } },
  ],
}))

const riskOption = computed<EChartsCoreOption>(() => {
  const data = Object.entries(analytics.value.risk_counts)
    .filter(([, value]) => value > 0)
    .map(([key, value]) => ({ name: riskLabels[key] || key, value, itemStyle: { color: riskColors[key] || palette.muted } }))
  return {
    animationDuration: 450,
    aria: { enabled: true, decal: { show: false } },
    tooltip: { trigger: 'item', backgroundColor: '#101f2f', borderColor: palette.line, textStyle: { color: '#dce8f5', fontSize: 12 } },
    legend: { bottom: 0, left: 'center', textStyle: { color: palette.text, fontSize: 12 }, itemWidth: 10, itemHeight: 7 },
    series: [{
      name: '风险构成',
      type: 'pie',
      radius: ['61%', '76%'],
      center: ['50%', '46%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 5, borderWidth: 4, borderColor: tokens.getPropertyValue('--panel').trim() },
      label: { color: palette.text, fontSize: 12, formatter: '{b}\n{c} 项' },
      labelLine: { lineStyle: { color: '#425b72' }, length: 8, length2: 6 },
      data,
    }],
  }
})

const areaOption = computed<EChartsCoreOption>(() => {
  const rows = analytics.value.area_breakdown.slice(0, 8).reverse()
  return {
    animationDuration: 450,
    aria: { enabled: true, decal: { show: false } },
    color: [palette.blue, palette.purple, palette.red],
    tooltip: baseTooltip,
    legend: { top: 0, right: 0, textStyle: { color: palette.text, fontSize: 12 }, itemWidth: 12, itemHeight: 6 },
    grid: { left: 86, right: 18, top: 38, bottom: 18 },
    xAxis: { type: 'value', minInterval: 1, axisLine: { show: false }, axisTick: { show: false }, axisLabel, splitLine },
    yAxis: { type: 'category', data: rows.map(item => item.area_type), axisLine, axisTick: { show: false }, axisLabel: { ...axisLabel, width: 76, overflow: 'truncate' } },
    series: [
      { name: '任务总量', type: 'bar', barMaxWidth: 12, data: rows.map(item => item.total), itemStyle: { borderRadius: [0, 2, 2, 0] } },
      { name: '待复核', type: 'bar', barMaxWidth: 12, data: rows.map(item => item.review_required), itemStyle: { borderRadius: [0, 2, 2, 0] } },
      { name: '高风险', type: 'bar', barMaxWidth: 12, data: rows.map(item => item.high_risk), itemStyle: { borderRadius: [0, 2, 2, 0] } },
    ],
  }
})

const reasonOption = computed<EChartsCoreOption>(() => {
  const rows = analytics.value.review_reason_counts.slice(0, 7).reverse()
  return {
    animationDuration: 450,
    aria: { enabled: true, decal: { show: false } },
    tooltip: baseTooltip,
    grid: { left: 78, right: 24, top: 12, bottom: 18 },
    xAxis: { type: 'value', minInterval: 1, axisLine: { show: false }, axisTick: { show: false }, axisLabel, splitLine },
    yAxis: { type: 'category', data: rows.map(item => item.category), axisLine, axisTick: { show: false }, axisLabel },
    series: [{
      name: '复核任务',
      type: 'bar',
      barMaxWidth: 14,
      data: rows.map((item, index) => ({ value: item.count, itemStyle: { color: index === rows.length - 1 ? palette.purple : '#566bb8', borderRadius: [0, 2, 2, 0] } })),
      label: { show: true, position: 'right', color: palette.text, fontSize: 12 },
    }],
  }
})

const modelOption = computed<EChartsCoreOption>(() => {
  const rows = analytics.value.model_breakdown
  return {
    animationDuration: 450,
    aria: { enabled: true, decal: { show: false } },
    color: [palette.cyan, palette.green],
    tooltip: baseTooltip,
    legend: { top: 0, right: 0, textStyle: { color: palette.text, fontSize: 12 }, itemWidth: 12, itemHeight: 6 },
    grid: { left: 38, right: 40, top: 38, bottom: 54 },
    xAxis: { type: 'category', data: rows.map(item => modelLabel(item.model_role, item.model_name)), axisLine, axisTick: { show: false }, axisLabel: { ...axisLabel, interval: 0, rotate: rows.length > 3 ? 20 : 0 } },
    yAxis: [
      { type: 'value', minInterval: 1, axisLine: { show: false }, axisTick: { show: false }, axisLabel, splitLine },
      { type: 'value', min: 0, max: 100, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { ...axisLabel, formatter: '{value}%' }, splitLine: { show: false } },
    ],
    series: [
      { name: '检出数', type: 'bar', barMaxWidth: 22, data: rows.map(item => item.detection_count), itemStyle: { borderRadius: [2, 2, 0, 0] } },
      { name: '平均置信度', type: 'line', yAxisIndex: 1, smooth: .2, symbolSize: 6, data: rows.map(item => Math.round(item.average_confidence * 100)) },
    ],
  }
})

const classOption = computed<EChartsCoreOption>(() => {
  const rows = analytics.value.class_breakdown.slice(0, 8).reverse()
  return {
    animationDuration: 450,
    aria: { enabled: true, decal: { show: false } },
    tooltip: baseTooltip,
    grid: { left: 76, right: 25, top: 12, bottom: 18 },
    xAxis: { type: 'value', minInterval: 1, axisLine: { show: false }, axisTick: { show: false }, axisLabel, splitLine },
    yAxis: { type: 'category', data: rows.map(item => item.class_name), axisLine, axisTick: { show: false }, axisLabel: { ...axisLabel, width: 70, overflow: 'truncate' } },
    series: [{ name: '检出数', type: 'bar', barMaxWidth: 13, data: rows.map(item => item.detection_count), itemStyle: { color: palette.cyan, borderRadius: [0, 2, 2, 0] }, label: { show: true, position: 'right', color: palette.text, fontSize: 12 } }],
  }
})

const agentOption = computed<EChartsCoreOption>(() => {
  const rows = analytics.value.agent_performance.slice(0, 8).reverse()
  return {
    animationDuration: 450,
    aria: { enabled: true, decal: { show: false } },
    tooltip: { ...baseTooltip, valueFormatter: (value: number) => `${value.toFixed(0)} ms` },
    grid: { left: 88, right: 38, top: 12, bottom: 18 },
    xAxis: { type: 'value', axisLine: { show: false }, axisTick: { show: false }, axisLabel: { ...axisLabel, formatter: '{value}ms' }, splitLine },
    yAxis: { type: 'category', data: rows.map(item => nodeLabels[item.node_name] || item.node_name), axisLine, axisTick: { show: false }, axisLabel: { ...axisLabel, width: 82, overflow: 'truncate' } },
    series: [{ name: '平均耗时', type: 'bar', barMaxWidth: 13, data: rows.map(item => item.average_duration_ms), itemStyle: { color: palette.blue, borderRadius: [0, 2, 2, 0] } }],
  }
})

function formatDate(value: string) {
  const [, month = '', day = ''] = value.split('-')
  return `${Number(month)}/${Number(day)}`
}

function formatDuration(value: number) {
  if (!value) return '—'
  return value >= 1000 ? `${(value / 1000).toFixed(1)}s` : `${Math.round(value)}ms`
}

function modelLabel(role: string, name: string) {
  const roleName = role === 'traffic_sign' ? '交通标志' : role === 'general_object' ? '人员车辆' : role
  return `${roleName}\n${name.replace('.pt', '')}`
}

async function load() {
  loading.value = true
  failure.value = ''
  try {
    analytics.value = await getAnalyticsOverview()
  } catch (error) {
    failure.value = errorMessage(error)
    ElMessage.error(`数据分析加载失败：${failure.value}`)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="standard-page analytics-page" v-loading="loading">
    <section class="page-toolbar">
      <div><p class="page-kicker">运营分析</p><h1>巡检数据分析</h1><p>用真实任务、检测结果与 Agent 轨迹定位风险热点、复核瓶颈和系统耗时。</p></div>
      <div class="analytics-actions"><el-button :icon="Refresh" @click="load">刷新数据</el-button><el-button type="primary" @click="router.push('/inspection/new')">新建巡检</el-button></div>
    </section>

    <section class="archive-summary analytics-summary" aria-label="分析核心指标">
      <article><el-icon class="summary-icon"><DataAnalysis /></el-icon><span>累计巡检</span><strong>{{ analytics.summary.total_tasks }}</strong><small>全部真实任务</small></article>
      <article><el-icon class="summary-icon"><PieChart /></el-icon><span>闭环完成率</span><strong class="success">{{ analytics.summary.completion_rate }}%</strong><small>{{ completionGap }} 项未完成</small></article>
      <article><el-icon class="summary-icon"><WarningFilled /></el-icon><span>人工复核率</span><strong class="warning">{{ analytics.summary.review_rate }}%</strong><small>{{ analytics.summary.review_required }} 项待确认</small></article>
      <article><el-icon class="summary-icon"><Stopwatch /></el-icon><span>平均链路耗时</span><strong>{{ formatDuration(analytics.summary.average_duration_ms) }}</strong><small>完整智能体流程</small></article>
    </section>

    <section class="analytics-scope-strip" aria-label="分析数据范围">
      <div><span>统计窗口</span><strong>{{ analytics.daily_trend.length }} 天</strong><small>{{ activeDays }} 个有任务日期</small></div>
      <div><span>区域覆盖</span><strong>{{ analytics.area_breakdown.length }} 类</strong><small>按任务区域字段聚合</small></div>
      <div><span>模型检出</span><strong>{{ totalDetections }} 个</strong><small>保留历史模型名称</small></div>
      <div><span>Agent 节点</span><strong>{{ analytics.agent_performance.length }} 个</strong><small>来自真实执行轨迹</small></div>
    </section>

    <div v-if="failure" class="analytics-error"><el-icon><WarningFilled /></el-icon><div><strong>分析接口暂不可用</strong><p>{{ failure }}。确认后端已更新并重新启动后再刷新。</p></div></div>

    <section v-if="hasTasks && !failure" class="analysis-brief" aria-label="复核工作提示">
      <span class="brief-icon"><el-icon><WarningFilled /></el-icon></span>
      <div><strong>{{ analytics.summary.review_required }} 项任务等待人工确认</strong><p>结合现场证据与风险评估结果，完成复核和处置闭环。</p></div>
      <el-button @click="router.push('/reviews')">进入复核队列</el-button>
    </section>

    <section class="analytics-grid">
      <article class="content-card chart-panel chart-span-8">
        <header class="chart-heading"><div><p class="eyebrow">30 DAY TREND</p><h3>巡检与风险趋势</h3></div><span><el-icon><TrendCharts /></el-icon>按校园本地日期统计</span></header>
        <DataChart :option="trendOption" :empty="!hasTasks" empty-text="完成首个巡检后生成 30 日趋势" ariaLabel="近三十日巡检、待复核和高风险趋势折线图" />
        <footer class="chart-insight"><strong>趋势口径</strong><span>仅使用已入库任务；没有任务的日期保留为 0，便于识别巡检中断。</span></footer>
      </article>

      <article class="content-card chart-panel chart-span-4">
        <header class="chart-heading"><div><p class="eyebrow">RISK MIX</p><h3>风险等级构成</h3></div><span><el-icon><PieChart /></el-icon>{{ analytics.summary.total_tasks }} 项</span></header>
        <DataChart :option="riskOption" :empty="!hasTasks" empty-text="尚无风险研判结果" ariaLabel="风险等级构成环形图" />
        <footer class="chart-insight"><strong>判定原则</strong><span>待复核单独计为紫色，不折算成中风险或低风险。</span></footer>
      </article>

      <article class="content-card chart-panel chart-span-7">
        <header class="chart-heading"><div><p class="eyebrow">AREA COVERAGE</p><h3>区域任务与风险分布</h3></div><span><el-icon><Location /></el-icon>Top 8 区域</span></header>
        <DataChart :option="areaOption" :empty="!analytics.area_breakdown.length" empty-text="巡检任务尚未形成区域覆盖" ariaLabel="各区域任务、待复核和高风险数量柱状图" />
        <footer class="chart-insight"><strong>{{ leadingArea?.area_type || '暂无重点区域' }}</strong><span v-if="leadingArea">任务最多，共 {{ leadingArea.total }} 项，其中 {{ leadingArea.review_required }} 项需复核。</span><span v-else>新建任务并选择区域后自动统计。</span></footer>
      </article>

      <article class="content-card chart-panel chart-span-5">
        <header class="chart-heading"><div><p class="eyebrow">REVIEW DRIVERS</p><h3>人工复核原因</h3></div><span><el-icon><WarningFilled /></el-icon>按任务去重</span></header>
        <DataChart :option="reasonOption" :empty="!analytics.review_reason_counts.length" empty-text="当前没有人工复核原因" ariaLabel="人工复核原因分类柱状图" />
        <footer class="chart-insight"><strong>{{ leadingReason?.category || '暂无复核瓶颈' }}</strong><span v-if="leadingReason">当前影响 {{ leadingReason.count }} 项任务，可据此安排优化优先级。</span><span v-else>清洁低风险任务可以直接闭环。</span></footer>
      </article>

      <article class="content-card chart-panel chart-span-4">
        <header class="chart-heading"><div><p class="eyebrow">MODEL OUTPUT</p><h3>双模型贡献</h3></div><span><el-icon><DataAnalysis /></el-icon>数量与置信度</span></header>
        <DataChart :option="modelOption" :empty="!analytics.model_breakdown.length" empty-text="执行巡检后展示各模型检出贡献" ariaLabel="双 YOLO 模型检出数和平均置信度组合图" />
        <footer class="chart-insight"><strong>当前配置（不代表已加载）</strong><span v-if="analytics.configured_models">交通标志：{{ analytics.configured_models.traffic_sign || '未配置' }}；人员车辆：{{ analytics.configured_models.general_object || '未启用' }}。图表保留检测发生时的历史模型名称。</span><span v-else>后端未提供当前模型配置；图表仅表示历史检测来源。</span></footer>
      </article>

      <article class="content-card chart-panel chart-span-4">
        <header class="chart-heading"><div><p class="eyebrow">TOP CLASSES</p><h3>高频识别目标</h3></div><span><el-icon><Histogram /></el-icon>Top 8 类别</span></header>
        <DataChart :option="classOption" :empty="!analytics.class_breakdown.length" empty-text="暂无可统计的检测类别" ariaLabel="高频检测类别横向柱状图" />
        <footer class="chart-insight"><strong>{{ leadingClass?.class_name || '暂无高频类别' }}</strong><span v-if="leadingClass">累计检出 {{ leadingClass.detection_count }} 次，是当前最常见目标。</span><span v-else>模型检出会按展示名称聚合。</span></footer>
      </article>

      <article class="content-card chart-panel chart-span-4">
        <header class="chart-heading"><div><p class="eyebrow">AGENT LATENCY</p><h3>智能体节点耗时</h3></div><span><el-icon><Stopwatch /></el-icon>平均执行时间</span></header>
        <DataChart :option="agentOption" :empty="!analytics.agent_performance.length" empty-text="暂无 Agent 执行轨迹" ariaLabel="智能体节点平均耗时柱状图" />
        <footer class="chart-insight"><strong>{{ slowestNode ? nodeLabels[slowestNode.node_name] || slowestNode.node_name : '暂无耗时数据' }}</strong><span v-if="slowestNode">平均 {{ formatDuration(slowestNode.average_duration_ms) }}，累计执行 {{ slowestNode.run_count }} 次。</span><span v-else>执行任务后自动分析节点性能。</span></footer>
      </article>
    </section>
  </div>
</template>
