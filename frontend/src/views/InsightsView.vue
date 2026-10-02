<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import Icon from '../components/Icon.vue'
import EmptyState from '../components/EmptyState.vue'
import { api, bytes, message } from '../store'
import { currency } from '../studio'
import type { Analytics } from '../studio'
const data = ref<Analytics | null>(null), loading = ref(false), error = ref('')
const estimate = reactive({ hourlyRate: 120, minutesPerItem: 8, storageCost: 0.3 })
const hours = computed(() => (data.value?.completed_media || 0) * Math.max(0, estimate.minutesPerItem || 0) / 60)
const labor = computed(() => hours.value * Math.max(0, estimate.hourlyRate || 0))
const storage = computed(() => (data.value?.storage_bytes || 0) / 1024 ** 3 * Math.max(0, estimate.storageCost || 0))
const maxPlatform = computed(() => Math.max(1, ...(data.value?.platforms.map(p => p.count) || [])))
const actions: Record<string, string> = {
  project_created: '创建项目', project_updated: '更新项目', project_deleted: '移除项目',
  project_delivered: '完成交付', project_reopened: '重新打开项目', project_items_updated: '更新素材清单',
  rights_updated: '更新授权记录', workflow_created: '创建工作流', workflow_deleted: '移除工作流', workflow_run: '运行工作流',
  'project.create': '创建项目', 'project.update': '更新项目', 'project.delete': '移除项目',
  'project.items': '更新素材清单', 'rights.update': '更新授权记录',
  'workflow.create': '创建工作流', 'workflow.delete': '移除工作流', 'workflow.run': '运行工作流',
}
async function load() {
  loading.value = true; error.value = ''
  try { data.value = await api<Analytics>('/studio/analytics') }
  catch (e) { error.value = message(e) }
  finally { loading.value = false }
}
onMounted(load)
</script>
<template>
  <div class="page-heading"><div><div class="eyebrow">MAKE YOUR WORK VISIBLE</div><h1>看见每一份积累的价值</h1><p>以真实项目、媒体与操作记录，衡量你的内容工作流。</p></div><button class="button" :disabled="loading" @click="load"><Icon name="retry" :size="15" :class="{ spinner: loading }" />刷新数据</button></div>
  <div v-if="error" class="error-banner" role="alert"><span>{{ error }}</span><button class="button small" @click="load">重试</button></div>
  <p v-if="!data && loading" class="muted initial-loading" role="status">正在读取工作空间数据…</p>
  <template v-if="data">
    <div class="stats-grid"><article class="panel stat-card"><span class="feature-icon sage"><Icon name="folder" /></span><div><strong>{{ data.projects }}</strong><p>项目总数 · {{ data.active_projects }} 个进行中</p></div></article><article class="panel stat-card"><span class="feature-icon lavender"><Icon name="checks" /></span><div><strong>{{ data.delivered_projects }}</strong><p>已交付项目</p></div></article><article class="panel stat-card"><span class="feature-icon peach"><Icon name="shield" /></span><div><strong>{{ data.licensed_media }}<span class="stat-unit">/ {{ data.completed_media }}</span></strong><p>已核验授权 / 已完成媒体</p></div></article><article class="panel stat-card"><span class="feature-icon sky"><Icon name="storage" /></span><div><strong class="storage-value">{{ bytes(data.storage_bytes) }}</strong><p>实际媒体存储</p></div></article></div>
    <div class="insights-columns"><section class="panel estimate-panel"><div class="panel-heading"><h2><Icon name="clock" :size="18" />时间价值估算</h2><span class="badge peach">基于你的输入</span></div><p class="intro">用已完成的 {{ data.completed_media }} 份媒体，估算批量下载节省的手动处理时间。结果为假设估算，项目预算不代表收入。</p><div class="estimate-fields"><label>人工时薪（元 / 小时）<input v-model.number="estimate.hourlyRate" type="number" min="0" max="100000" step="1" /></label><label>每份手动处理时间（分钟）<input v-model.number="estimate.minutesPerItem" type="number" min="0" max="10000" step="1" /></label><label>每 GB 月存储成本（元）<input v-model.number="estimate.storageCost" type="number" min="0" max="100000" step="0.01" /></label></div><div class="estimate-results"><div><span>预计节省时间</span><strong>{{ hours.toFixed(1) }}<small> 小时</small></strong></div><div><span>对应人工价值</span><strong>{{ currency(Math.round(labor * 100)) }}</strong></div><div><span>预计月存储成本</span><strong>{{ currency(Math.round(storage * 100)) }}</strong></div></div><p class="formula">节省时间 = 已完成媒体 × 每份手动处理分钟 ÷ 60。人工价值 = 时间 × 时薪。存储估算按 1 GB = 1024³ 字节计算。</p></section><section class="panel workspace-facts"><div class="panel-heading"><h2><Icon name="leaf" :size="18" />工作空间概况</h2></div><div class="budget-fact"><span>全部项目预算</span><strong>{{ currency(data.budget_cents) }}</strong><p>来自项目资料中手动填写的预算总和</p></div><div class="budget-fact"><span>完成媒体总时长</span><strong>{{ Math.round(data.download_minutes).toLocaleString() }} <small>分钟</small></strong><p>按媒体实际时长汇总</p></div><div class="platforms"><h3>素材来源分布</h3><div v-for="platform in data.platforms" :key="platform.name" class="platform-row"><div><span>{{ platform.name || '其他来源' }}</span><strong>{{ platform.count }}</strong></div><div class="progress-track"><span :style="{ width: `${platform.count / maxPlatform * 100}%` }"></span></div></div><p v-if="!data.platforms.length" class="muted intro">添加素材后，来源分布会显示在这里。</p></div></section></div>
    <section class="panel activity-panel"><div class="panel-heading"><h2><Icon name="file" :size="18" />最近操作记录</h2><span class="section-caption">{{ data.activity.length }} 条</span></div><p class="intro">记录项目、授权与工作流的真实操作，方便回溯交付过程。</p><EmptyState v-if="!data.activity.length" icon="file" title="新的工作，会在这里留下脚印" description="创建项目或更新授权后，这里会自动记录操作时间与对象。" /><ol v-else class="activity-list"><li v-for="event in data.activity" :key="event.id"><span class="activity-dot"></span><div><strong>{{ actions[event.action] || event.action }}</strong><span>{{ event.entity_id }}</span></div><time :datetime="event.created_at">{{ new Date(event.created_at).toLocaleString('zh-CN') }}</time></li></ol></section>
  </template>
</template>
<style scoped>
.initial-loading { font-size: 12px; padding: 40px; }.stat-card { padding: 18px; }.stat-card strong.storage-value { font-size: 19px; }.insights-columns { display: grid; grid-template-columns: 1.4fr 1fr; gap: 20px; }.estimate-panel,.workspace-facts,.activity-panel { padding: 23px; min-width: 0; }.intro { font-size: 11px; color: var(--muted); margin: 12px 0 20px; }.estimate-fields { display: grid; gap: 17px; }.estimate-fields label { font-size: 11px; }.estimate-results { margin-top: 25px; display: grid; grid-template-columns: 1fr 1fr; gap: 18px; background: #f3f7ec; border-radius: 10px; padding: 20px; }.estimate-results span { font-size: 10px; color: var(--muted); display: block; }.estimate-results strong { display: block; font-size: 22px; font-weight: 550; margin-top: 9px; }.estimate-results small { font-size: 12px; }.formula { font-size: 9px; color: #99a48d; margin-top: 17px; }.budget-fact { border-bottom: 1px solid var(--line); padding: 20px 0; }.budget-fact span { display: block; font-size: 11px; color: var(--muted); }.budget-fact strong { display: block; font-size: 24px; margin-top: 10px; font-weight: 550; }.budget-fact small { font-size: 12px; }.budget-fact p { font-size: 9px; color: var(--muted); margin-top: 5px; }.platforms { margin-top: 23px; }.platforms h3 { font-size: 13px; }.platform-row { margin-top: 17px; }.platform-row > div:first-child { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 8px; }.activity-panel { margin-top: 23px; }.activity-list { padding: 0; margin: 0; list-style: none; }.activity-list li { display: flex; align-items: center; gap: 12px; padding: 16px 0; border-top: 1px solid var(--line); }.activity-dot { width: 7px; height: 7px; background: #a3b894; border-radius: 50%; flex-shrink: 0; }.activity-list li > div { flex: 1; min-width: 0; }.activity-list strong { display: block; font-size: 12px; font-weight: 500; }.activity-list div span { display: block; font-size: 9px; margin-top: 6px; color: var(--muted); overflow-wrap: anywhere; }.activity-list time { font-size: 10px; color: var(--muted); flex-shrink: 0; }
@media(max-width:1100px) { .stats-grid { grid-template-columns: 1fr 1fr; }.insights-columns { grid-template-columns: 1fr; }.workspace-facts .platforms { margin-top: 20px; } }@media(max-width:650px) { .estimate-panel,.workspace-facts,.activity-panel { padding: 18px; }.stat-card { padding: 15px 12px; gap: 10px; }.stat-card strong.storage-value { font-size: 15px; }.stat-card strong { font-size: 21px; }.activity-list li { flex-wrap: wrap; }.activity-list time { margin-left: 19px; }.estimate-results { padding: 16px; gap: 15px; }.estimate-results strong { font-size: 18px; }.estimate-panel .panel-heading h2 { font-size: 13px; } }
</style>
