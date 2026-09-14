<script setup lang="ts">
defineProps<{ level?: string }>()
const labels: Record<string, string> = { low: '低风险', medium: '中风险', high: '高风险', review: '待复核' }
</script>

<template>
  <span class="risk-badge" :class="`risk-${level || 'pending'}`">{{ labels[level || ''] || '未研判' }}</span>
</template>

