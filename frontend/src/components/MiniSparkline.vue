<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { LineChart } from 'echarts/charts'
import { GridComponent } from 'echarts/components'
import { init, use, type ECharts } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'

const props = withDefaults(defineProps<{ data: number[]; color?: string }>(), { color: '#4b8dff' })
const element = ref<HTMLElement>()
let chart: ECharts | undefined
let observer: ResizeObserver | undefined

use([LineChart, GridComponent, CanvasRenderer])

function render() {
  if (!element.value) return
  chart ||= init(element.value)
  chart.setOption({
    animationDuration: 600,
    grid: { left: 1, right: 1, top: 6, bottom: 2 },
    xAxis: { type: 'category', show: false, boundaryGap: false, data: props.data.map((_, index) => index) },
    yAxis: {
      type: 'value',
      show: false,
      min: (value: { min: number; max: number }) => value.min - Math.max(1, (value.max - value.min) * .28),
      max: (value: { min: number; max: number }) => value.max + Math.max(1, (value.max - value.min) * .18),
    },
    series: [{
      type: 'line',
      data: props.data,
      smooth: .28,
      showSymbol: false,
      lineStyle: { width: 1.5, color: props.color },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: `${props.color}50` }, { offset: 1, color: `${props.color}00` }] } },
      emphasis: { disabled: true },
    }],
  })
}

watch(() => [props.data, props.color], render, { deep: true })
onMounted(() => {
  render()
  if (element.value) {
    observer = new ResizeObserver(() => chart?.resize())
    observer.observe(element.value)
  }
})
onBeforeUnmount(() => { observer?.disconnect(); chart?.dispose() })
</script>

<template><div ref="element" class="mini-sparkline" aria-hidden="true"></div></template>
