<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Clock, Location, WarningFilled } from '@element-plus/icons-vue'
import { errorMessage, getInspections } from '../api'
import RiskBadge from '../components/RiskBadge.vue'
import type { Inspection } from '../types'

const router = useRouter()
const items = ref<Inspection[]>([])
const loading = ref(false)
const loadFailure = ref('')
const highCount = computed(() => items.value.filter(item => item.risk_level === 'high').length)
const areaCount = computed(() => new Set(items.value.map(item => item.area_type).filter(Boolean)).size)
const reasonCount = computed(() => new Set(items.value.flatMap(item => item.review_reasons || [])).size)
const queueBreakdown = computed(() => [
  { label: '高风险任务', value: highCount.value, tone: 'danger' },
  { label: '其他风险任务', value: Math.max(items.value.length - highCount.value, 0), tone: 'warning' },
  { label: '重点区域', value: areaCount.value, tone: 'blue' },
])
const reviewSteps = ['核对现场原图与标注结果', '确认模型置信度和事件规则', '查看知识依据与风险建议', '人工确认或驳回后归档']

function displayTime(value: string) {
  // Backend timestamps without an offset retain their recorded wall-clock time.
  const match = /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/.exec(value)
  return match ? `${match[1]} ${match[2]}` : value || '—'
}

async function openTask(item: Inspection) { await router.push(`/inspection/${item.id}`) }
onMounted(async () => {
  loading.value = true
  try {
    const response = await getInspections({ review_required: true })
    items.value = response.items
  } catch (error) {
    items.value = []
    loadFailure.value = errorMessage(error)
  } finally { loading.value = false }
})
</script>

<template>
  <div class="standard-page">
    <section class="page-toolbar">
      <div><p class="page-kicker">人机协同</p><h1>人工复核队列</h1><p>统一承接低置信度、证据不足与高风险任务，人工结论覆盖自动研判。</p></div>
      <span class="queue-count"><strong>{{ items.length }}</strong> 条待处理</span>
    </section>
    <section class="review-overview">
      <div><el-icon><WarningFilled /></el-icon><span><strong>{{ highCount }}</strong> 高风险优先</span></div>
      <div><el-icon><Clock /></el-icon><span><strong>{{ reasonCount }}</strong> 类复核原因</span></div>
      <div><el-icon><Location /></el-icon><span><strong>{{ areaCount }}</strong> 个重点区域</span></div>
    </section>
    <div v-if="loadFailure" class="inline-error">复核队列加载失败：{{ loadFailure }}</div>
    <div class="review-workbench">
      <section class="content-card review-card">
        <div class="section-title compact"><div><h3>待确认任务</h3><p>优先核对现场图片、识别结果和风险依据</p></div></div>
        <div class="review-list" v-loading="loading">
          <article v-for="item in items" :key="item.id" @click="openTask(item)">
            <div class="review-primary"><img v-if="item.original_image_url" class="review-evidence-thumb" :src="item.original_image_url" :alt="`${item.location}现场证据缩略图`" loading="lazy" /><span class="review-risk" :class="`risk-${item.risk_level}`"><el-icon><WarningFilled /></el-icon></span><div class="review-task-copy"><strong>{{ item.location }}</strong><p class="review-task-number">{{ item.task_no }}</p><p class="review-task-meta"><span>{{ item.area_type || '区域未填写' }}</span><time :datetime="item.created_at">{{ displayTime(item.created_at) }}</time></p></div></div>
            <div class="review-evidence-summary"><RiskBadge :level="item.risk_level" /><div class="review-reasons"><span v-for="reason in item.review_reasons" :key="reason">{{ reason }}</span><span v-if="!item.review_reasons?.length" class="review-reason-empty">未记录具体原因，请核对任务证据</span></div></div>
            <el-button @click.stop="openTask(item)">进入复核<el-icon><ArrowRight /></el-icon></el-button>
          </article>
          <el-empty v-if="!items.length" description="当前没有待复核任务" :image-size="68" />
        </div>
        <div class="review-support-grid">
          <article><span>01</span><div><strong>证据优先</strong><p>先核对原图与标注框，避免仅凭风险分数作出结论。</p></div></article>
          <article><span>02</span><div><strong>依据可追溯</strong><p>模型置信度、事件规则和知识条款必须能够回看。</p></div></article>
          <article><span>03</span><div><strong>人工结论落档</strong><p>确认人、处理意见与最终状态写入同一巡检档案。</p></div></article>
        </div>
      </section>
      <aside class="review-rail">
        <section class="content-card rail-card">
          <div class="rail-heading"><div><strong>当前队列构成</strong><span>数据随待复核任务实时变化</span></div></div>
          <div class="queue-breakdown"><div v-for="item in queueBreakdown" :key="item.label"><i :class="item.tone"></i><span>{{ item.label }}</span><strong>{{ item.value }}</strong></div></div>
        </section>
        <section class="content-card rail-card">
          <div class="rail-heading"><div><strong>标准复核流程</strong><span>四步形成可追溯结论</span></div></div>
          <ol class="review-step-list"><li v-for="(step, index) in reviewSteps" :key="step"><span>{{ index + 1 }}</span><p>{{ step }}</p></li></ol>
        </section>
        <section class="content-card rail-card review-principle-card">
          <div class="rail-heading"><div><strong>人工判定原则</strong><span>系统建议不替代最终责任</span></div></div>
          <p>先看现场证据，再看模型与知识依据；证据不足时保持待复核，人工结论覆盖自动研判并写入档案。</p>
        </section>
      </aside>
    </div>
  </div>
</template>
