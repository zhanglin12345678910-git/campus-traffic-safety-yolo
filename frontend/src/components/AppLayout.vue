<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  Bell,
  Calendar,
  Checked,
  CircleCheck,
  Cloudy,
  Collection,
  DataAnalysis,
  Expand,
  Fold,
  FullScreen,
  Lightning,
  List,
  Monitor,
  PartlyCloudy,
  Pouring,
  Setting,
  Sunny,
  User,
  VideoCameraFilled,
} from '@element-plus/icons-vue'
import { api, getDashboard } from '../api'
import campusSkyline from '../assets/campus-sidebar-skyline.png'
import schoolLogo from '../assets/scmvc-official-logo.png'
import { campusProfile } from '../config/campus'
import type { CampusWeather } from '../types'

const route = useRoute()
const router = useRouter()
const collapsed = ref(false)
const serviceState = ref<'checking' | 'ready' | 'degraded'>('checking')
// Only the dashboard API may set this; no data means no badge.
const reviewCount = ref(0)
const weather = ref<CampusWeather>()
const now = ref(new Date())
let healthTimer: number | undefined
let clockTimer: number | undefined
let weatherTimer: number | undefined

const serviceText = computed(() => serviceState.value === 'ready' ? '系统正常' : serviceState.value === 'degraded' ? '受保护模式' : '服务检查中')
const weatherIcon = computed(() => {
  const text = weather.value?.weather || ''
  if (text.includes('雷')) return Lightning
  if (text.includes('雨') || text.includes('雪')) return Pouring
  if (text.includes('晴')) return Sunny
  if (text.includes('阴') || text.includes('雾') || text.includes('霾')) return Cloudy
  return PartlyCloudy
})
const dateText = computed(() => new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(now.value).replaceAll('/', '-'))
const weekText = computed(() => new Intl.DateTimeFormat('zh-CN', { weekday: 'short' }).format(now.value))
const timeText = computed(() => now.value.toLocaleTimeString('zh-CN', { hour12: false }))
const menu = [
  { path: '/dashboard', label: '态势总览', icon: Monitor },
  { path: '/inspection/new', label: '智能巡检', icon: VideoCameraFilled },
  { path: '/inspections', label: '巡检档案', icon: List },
  { path: '/reviews', label: '人工复核', icon: Checked, badge: true },
  { path: '/analytics', label: '数据分析', icon: DataAnalysis },
  { path: '/knowledge', label: '安全知识库', icon: Collection },
  { path: '/settings', label: '系统设置', icon: Setting },
]

async function checkHealth() {
  try {
    const [health, dashboard] = await Promise.all([
      api.get('/health'),
      getDashboard().catch(() => undefined),
    ])
    serviceState.value = health.data.services?.database === 'ok'
      && health.data.services?.qdrant?.status === 'ok'
      && health.data.services?.yolo?.configured
      ? 'ready' : 'degraded'
    reviewCount.value = dashboard?.review_required ?? 0
  } catch {
    serviceState.value = 'degraded'
  }
}

async function loadWeather() {
  try {
    weather.value = (await api.get<CampusWeather>('/maps/weather', { params: { adcode: campusProfile.adcode } })).data
  } catch {
    weather.value = undefined
  }
}

async function toggleFullscreen() {
  if (document.fullscreenElement) await document.exitFullscreen()
  else await document.documentElement.requestFullscreen()
}

onMounted(async () => {
  void loadWeather()
  weatherTimer = window.setInterval(loadWeather, 30 * 60_000)
  await checkHealth()
  healthTimer = window.setInterval(checkHealth, 30_000)
  clockTimer = window.setInterval(() => { now.value = new Date() }, 1_000)
})

onBeforeUnmount(() => {
  if (healthTimer) window.clearInterval(healthTimer)
  if (clockTimer) window.clearInterval(clockTimer)
  if (weatherTimer) window.clearInterval(weatherTimer)
})
</script>

<template>
  <div class="app-shell" :class="{ collapsed }">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark official-school-mark"><img :src="schoolLogo" alt="四川现代职业学院校徽" /></div>
        <div class="brand-copy">
          <strong>安巡智脑</strong>
          <span>{{ campusProfile.name }}</span>
        </div>
      </div>

      <nav class="primary-nav" aria-label="主导航">
        <router-link v-for="item in menu" :key="item.path" :to="item.path" :title="collapsed ? item.label : undefined">
          <el-icon><component :is="item.icon" /></el-icon>
          <span class="menu-label">{{ item.label }}</span>
          <span v-if="item.badge && reviewCount" class="menu-badge">{{ reviewCount > 99 ? '99+' : reviewCount }}</span>
        </router-link>
      </nav>

      <div class="sidebar-campus-signature" aria-label="四川现代职业学院校训">
        <img :src="campusSkyline" alt="校园建筑装饰线稿" />
        <p><span>厚德&nbsp; 精技</span><span>笃行&nbsp; 创新</span></p>
      </div>

      <div class="sidebar-system">
        <div class="sidebar-model"><el-icon><DataAnalysis /></el-icon><span>YOLO26</span><small>视觉引擎</small></div>
        <div class="sidebar-model"><el-icon><CircleCheck /></el-icon><span>Agent</span><small>研判链路</small></div>
      </div>

      <button class="sidebar-collapse" aria-label="切换侧栏" @click="collapsed = !collapsed">
        <el-icon><Expand v-if="collapsed" /><Fold v-else /></el-icon>
        <span>收起侧栏</span>
      </button>
    </aside>

    <main class="app-main">
      <header class="topbar">
        <div class="topbar-identity">
          <span class="school-seal official-school-mark"><img :src="schoolLogo" alt="四川现代职业学院校徽" /></span>
          <strong>{{ campusProfile.name }}</strong>
          <i></i>
          <small>AI 守护校园出行安全</small>
        </div>
        <div class="environment-strip">
          <!-- v-show keeps the element so the mobile nth-child rules stay aligned. -->
          <span v-show="weather?.available" class="weather-now" :title="weather?.report_time ? `高德实况天气 · 发布于 ${weather.report_time}` : undefined"><el-icon><component :is="weatherIcon" /></el-icon>{{ weather?.temperature }}°C&nbsp; {{ weather?.weather }}</span>
          <span><el-icon><Calendar /></el-icon>{{ dateText }}</span>
          <span>{{ weekText }}</span>
          <strong>{{ timeText }}</strong>
          <span class="system-state" :class="`is-${serviceState}`"><i></i>{{ serviceText }}</span>
        </div>
        <div class="top-actions">
          <button title="全屏" @click="toggleFullscreen"><el-icon><FullScreen /></el-icon><span>全屏</span></button>
          <button title="人工复核" @click="router.push('/reviews')">
            <el-icon><Bell /></el-icon><span>消息</span><em v-if="reviewCount">{{ reviewCount > 9 ? '9+' : reviewCount }}</em>
          </button>
          <button class="operator" title="当前值班员" @click="router.push('/settings')"><el-icon><User /></el-icon><span>安保值班员</span><el-icon class="operator-arrow"><ArrowDown /></el-icon></button>
        </div>
      </header>
      <section class="page-content" :class="{ 'dashboard-content': route.path === '/dashboard' }"><router-view /></section>
    </main>
  </div>
</template>
