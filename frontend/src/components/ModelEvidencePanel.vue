<script setup lang="ts">
defineProps<{ services?: Record<string, any> }>()
</script>

<template>
  <section class="content-card model-evidence-panel" aria-label="视觉与风险模型职责">
    <div class="section-title"><div><p class="eyebrow">EVIDENCE & DECISION</p><h3>视觉证据与风险决策</h3></div><span>来自 /health · 配置不代表联网成功</span></div>
    <div class="model-role-grid">
      <article class="role-vision"><small>旁挂视觉研判</small><strong>{{ services?.vision_llm?.model || '—' }}</strong><em>{{ !services?.vision_llm ? '状态未知 · 后端未返回' : !services.vision_llm.enabled ? '已关闭' : services.vision_llm.configured ? '已启用 · 已配置' : '已启用 · 待配置' }}</em><p>补充现场可见证据，不直接决定风险等级或转人工策略。</p></article>
      <article class="role-risk"><small>最终风险研判</small><strong>{{ services?.llm?.model || '—' }}</strong><em>{{ !services ? '状态未知' : services.llm?.configured ? '已配置 · 任务中调用' : '未配置' }}</em><p>结合检测结果、检索条款与视觉证据生成风险结论。</p></article>
      <article class="role-policy"><small>服务端复核策略</small><strong>证据约束 · 人工兜底</strong><em>{{ services?.vision_llm?.person_gate === true ? '人物隐私闸门已启用' : services?.vision_llm?.person_gate === false ? '人物隐私闸门未启用' : '闸门状态未知' }}</em><p>检测到人物时跳过云端视觉调用；闸门不能保证覆盖漏检。视觉调用失败时降级并保留复核原因。</p></article>
    </div>
  </section>
</template>
