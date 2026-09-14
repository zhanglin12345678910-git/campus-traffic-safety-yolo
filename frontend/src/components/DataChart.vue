<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { AriaComponent, GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { init, use, type ECharts, type EChartsCoreOption } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'

const props = withDefaults(defineProps<{
  option: EChartsCoreOption
  empty?: boolean
  emptyText?: string
  ariaLabel: string
}>(), {
  empty: false,
  emptyText: '暂无可分析数据',
})

const element = ref<HTMLElement>()
let chart: ECharts | undefined
let observer: ResizeObserver | undefined

use([BarChart, LineChart, PieChart, AriaComponent, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

function render() {
  if (!element.value || props.empty) return
  chart ||= init(element.value)
  chart.setOption(props.option, { notMerge: true })
}

watch(() => [props.option, props.empty], () => {
  if (props.empty) chart?.clear()
  else render()
}, { deep: true })

onMounted(() => {
  render()
  if (element.value) {
    observer = new ResizeObserver(() => chart?.resize())
    observer.observe(element.value)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
  chart?.dispose()
})
</script>

<template>
  <div class="data-chart-shell" :aria-label="ariaLabel">
    <div v-show="!empty" ref="element" class="data-chart" role="img"></div>
    <div v-if="empty" class="chart-empty"><strong>暂无数据</strong><span>{{ emptyText }}</span></div>
  </div>
</template>
