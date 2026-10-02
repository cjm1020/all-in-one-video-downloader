<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Artwork from '../components/Artwork.vue'
import EmptyState from '../components/EmptyState.vue'
import Icon from '../components/Icon.vue'
import {
  api,
  bytes,
  duration,
  hostname,
  message,
  navigate,
  notify,
  presets,
  refresh,
  statusLabels,
  store,
} from '../store'
import type { Preset, VideoInfo } from '../types'

const url = ref(''),
  mode = ref('single'),
  preset = ref<Preset>(store.settings.default_preset)
const collection = ref('inbox'),
  advanced = ref(false),
  schedule = ref('')
const clipStart = ref(''),
  clipEnd = ref(''),
  rate = ref(store.settings.rate_limit)
const inspecting = ref(false),
  submitting = ref(false),
  info = ref<VideoInfo | null>(null),
  error = ref('')
const links = computed(() =>
  url.value
    .split(/\n+/)
    .map((s) => s.trim())
    .filter(Boolean),
)
watch(
  () => store.settings,
  (v) => {
    preset.value = v.default_preset
    rate.value = v.rate_limit
  },
)
watch(url, () => {
  info.value = null
  error.value = ''
})
async function inspect() {
  if (links.value.length !== 1) {
    error.value = '请先输入一个完整的视频链接'
    return
  }
  inspecting.value = true
  error.value = ''
  try {
    info.value = await api<VideoInfo>('/inspect', {
      method: 'POST',
      body: JSON.stringify({ url: links.value[0] }),
    })
  } catch (e) {
    error.value = message(e)
  } finally {
    inspecting.value = false
  }
}
async function submit() {
  if (!links.value.length) {
    error.value = '粘贴一个链接，就可以开始收藏啦'
    return
  }
  if (links.value.length > 30) {
    error.value = '一次最多添加 30 个视频，请分批收藏'
    return
  }
  if ((clipStart.value === '') !== (clipEnd.value === '')) {
    error.value = '请同时填写片段的开始和结束时间'
    return
  }
  if (clipEnd.value !== '' && Number(clipEnd.value) <= Number(clipStart.value)) {
    error.value = '片段结束时间需要晚于开始时间'
    return
  }
  if (schedule.value && new Date(schedule.value).getTime() <= Date.now()) {
    error.value = '预约时间需要晚于现在'
    return
  }
  submitting.value = true
  error.value = ''
  try {
    const result = await api<{ added: unknown[]; skipped: string[] }>('/tasks', {
      method: 'POST',
      body: JSON.stringify({
        urls: links.value,
        preset: preset.value,
        collection_id: collection.value,
        scheduled_at: schedule.value ? new Date(schedule.value).toISOString() : null,
        clip_start: clipStart.value === '' ? null : Number(clipStart.value),
        clip_end: clipEnd.value === '' ? null : Number(clipEnd.value),
        rate_limit: Number(rate.value),
      }),
    })
    notify(
      `已添加 ${result.added.length} 个片刻${result.skipped.length ? `，跳过 ${result.skipped.length} 个重复链接` : '，正在等待下载'}`,
    )
    await refresh()
    if (result.added.length) {
      url.value = ''
      navigate('queue')
    }
  } catch (e) {
    error.value = message(e)
  } finally {
    submitting.value = false
  }
}
function demo() {
  url.value = 'https://download.blender.org/peach/trailer/trailer_480p.mp4'
  mode.value = 'single'
  notify('已填入 Blender 公开授权演示片，点击开始收藏即可下载')
}
const recent = computed(() => store.tasks.slice(0, 3))
</script>
<template>
  <section class="hero-panel">
    <div class="hero-copy">
      <div class="eyebrow">
        <span class="hero-dot"></span>
        A LITTLE HOME FOR YOUR FAVORITES
      </div>
      <h1>
        把喜欢的片刻，
        <br />
        留在身边
        <span class="heading-period">。</span>
      </h1>
      <p>
        视频、音乐、灵感，都值得好好收藏。
        <br />
        一个链接，开启你的私人媒体小天地。
      </p>
      <div class="hero-tags">
        <span>
          <Icon name="shield" :size="13" />
          本地保存
        </span>
        <span>
          <Icon name="leaf" :size="13" />
          轻盈无广告
        </span>
        <span>
          <Icon name="heart" :size="13" />
          为喜欢而下载
        </span>
      </div>
    </div>
    <Artwork />
  </section>
  <div class="stats-grid">
    <div class="panel stat-card">
      <span class="feature-icon sage"><Icon name="library" /></span>
      <div>
        <strong>
          {{ store.status?.completed_tasks ?? 0 }}
          <span class="stat-unit">个</span>
        </strong>
        <p>已收藏的片刻</p>
      </div>
    </div>
    <div class="panel stat-card">
      <span class="feature-icon peach"><Icon name="download" /></span>
      <div>
        <strong>
          {{ store.status?.active_tasks ?? 0 }}
          <span class="stat-unit">个</span>
        </strong>
        <p>正在路上的精彩</p>
      </div>
    </div>
    <div class="panel stat-card">
      <span class="feature-icon lavender"><Icon name="heart" /></span>
      <div>
        <strong>
          {{ store.status?.favorite_tasks ?? 0 }}
          <span class="stat-unit">个</span>
        </strong>
        <p>特别喜欢的内容</p>
      </div>
    </div>
    <div class="panel stat-card">
      <span class="feature-icon sky"><Icon name="storage" /></span>
      <div>
        <strong class="storage-stat">{{ bytes(store.status?.storage_bytes ?? 0) }}</strong>
        <p>收藏空间已使用</p>
      </div>
    </div>
  </div>
  <form class="panel download-panel" @submit.prevent="submit">
    <div class="panel-heading">
      <h2>
        <Icon name="link" :size="19" />
        从一个链接开始
        <span class="badge">NEW MOMENT</span>
      </h2>
      <div class="segmented" aria-label="链接输入模式">
        <button type="button" :class="{ active: mode === 'single' }" @click="mode = 'single'">
          单个链接
        </button>
        <button type="button" :class="{ active: mode === 'batch' }" @click="mode = 'batch'">批量收藏</button>
      </div>
    </div>
    <p class="download-caption">粘贴视频链接，剩下的交给我们。支持 yt-dlp 兼容的平台与直接媒体链接。</p>
    <div class="url-field">
      <Icon name="link" :size="20" />
      <textarea
        v-if="mode === 'batch'"
        v-model="url"
        rows="4"
        aria-label="批量视频链接"
        placeholder="每行一个视频链接，一次最多 30 个"
      ></textarea>
      <input
        v-else
        v-model="url"
        type="url"
        aria-label="视频链接"
        placeholder="粘贴 YouTube、Bilibili、抖音或其他视频链接…"
      />
      <button
        type="button"
        class="button inspect-button"
        :disabled="inspecting || !url.trim() || links.length !== 1"
        @click="inspect"
      >
        <Icon :name="inspecting ? 'loader' : 'search'" :size="16" :class="{ spinner: inspecting }" />
        {{ inspecting ? '解析中' : '预览信息' }}
      </button>
    </div>
    <div class="platform-line">
      <span>常用平台</span>
      <span class="platform youtube">
        <span class="platform-letter">▶</span>
        YouTube
      </span>
      <span class="platform bili">
        <span class="platform-letter">b</span>
        Bilibili
      </span>
      <span class="platform douyin">
        <span class="platform-letter">♪</span>
        抖音
      </span>
      <span class="platform vimeo">
        <span class="platform-letter">v</span>
        Vimeo
      </span>
      <span class="platform more">更多平台</span>
      <button type="button" class="text-link sample-link" @click="demo">
        试试公开演示素材
        <Icon name="arrow" :size="13" />
      </button>
    </div>
    <div v-if="info" class="inspection-card">
      <img v-if="info.thumbnail" :src="info.thumbnail" alt="视频封面" referrerpolicy="no-referrer" />
      <div v-else class="feature-icon sage"><Icon name="video" /></div>
      <div>
        <h3>{{ info.title }}</h3>
        <p>{{ info.platform }} · {{ duration(info.duration) }} · {{ info.uploader || '公开媒体来源' }}</p>
        <div class="tags">
          <span v-for="height in info.heights" :key="height" class="tag">{{ height }}p</span>
          <span class="tag">{{ info.has_subtitles ? '有字幕，可用于学习' : '暂无字幕，可手动导入' }}</span>
        </div>
      </div>
      <Icon name="circlecheck" :size="20" />
    </div>
    <div class="preset-label">
      选择一种收藏方式
      <span>让每个片刻，以最合适的方式留下</span>
    </div>
    <div class="preset-grid">
      <button
        v-for="item in presets"
        :key="item.id"
        type="button"
        :class="['preset-card', { selected: preset === item.id }]"
        :aria-pressed="preset === item.id"
        @click="preset = item.id"
      >
        <span :class="['feature-icon', item.color]"><Icon :name="item.icon" :size="20" /></span>
        <span>
          <strong>{{ item.title }}</strong>
          <small>{{ item.detail }}</small>
        </span>
        <span class="preset-radio"><Icon v-if="preset === item.id" name="check" :size="10" /></span>
      </button>
    </div>
    <div class="download-options">
      <label class="collection-inline">
        <Icon name="folder" :size="16" />
        <span>收藏到</span>
        <select v-model="collection" aria-label="目标合集">
          <option v-for="item in store.collections" :key="item.id" :value="item.id">{{ item.name }}</option>
          <option v-if="!store.collections.length" value="inbox">我的收藏</option>
        </select>
      </label>
      <button
        class="text-link advanced-toggle"
        type="button"
        :aria-expanded="advanced"
        @click="advanced = !advanced"
      >
        <Icon name="sliders" :size="15" />
        更多小偏好
        <Icon name="down" :size="13" />
      </button>
    </div>
    <div v-if="advanced" class="advanced-options">
      <div class="form-row">
        <label>
          稍后再下
          <input v-model="schedule" type="datetime-local" aria-label="预约下载时间" />
        </label>
        <label>
          速度上限（KB/s，0 为不限）
          <input v-model="rate" type="number" min="0" max="100000" />
        </label>
      </div>
      <div class="form-row">
        <label>
          灵感剪辑 · 开始秒数
          <input v-model="clipStart" type="number" min="0" max="86400" placeholder="留空则收藏完整视频" />
        </label>
        <label>
          结束秒数
          <input v-model="clipEnd" type="number" min="1" max="86400" placeholder="例如 30" />
        </label>
      </div>
      <p class="muted">片段会在完整视频下载后精确剪辑；时间基于原始视频。预约时间使用你的本地时区。</p>
    </div>
    <p v-if="error" class="error-text form-error" role="alert">{{ error }}</p>
    <div class="download-bottom">
      <span>
        <Icon name="shield" :size="14" />
        请收藏自己拥有版权或获授权的内容
      </span>
      <button class="button primary download-submit" :disabled="submitting || !store.ready">
        <Icon :name="submitting ? 'loader' : 'download'" :size="17" :class="{ spinner: submitting }" />
        {{
          submitting
            ? '正在加入收藏…'
            : mode === 'batch'
              ? `收藏这 ${links.length || '些'} 个片刻`
              : '开始收藏'
        }}
        <Icon name="right" :size="16" />
      </button>
    </div>
  </form>
  <div class="home-lower">
    <section class="panel recent-panel">
      <div class="panel-heading">
        <h2>最近的片刻</h2>
        <button class="text-link" @click="navigate('queue')">
          查看全部
          <Icon name="right" :size="13" />
        </button>
      </div>
      <EmptyState
        v-if="!recent.length"
        icon="bookmark"
        title="第一份收藏，正在等你"
        description="添加一个视频链接，让这里慢慢装满你喜欢的内容。"
      />
      <div v-for="task in recent" :key="task.id" class="recent-row">
        <span :class="['feature-icon', presets.find((p) => p.id === task.preset)?.color]">
          <Icon :name="task.preset === 'audio' ? 'headphones' : 'video'" :size="19" />
        </span>
        <div>
          <strong>{{ task.title || hostname(task.url) }}</strong>
          <p>
            {{ presets.find((p) => p.id === task.preset)?.title }} ·
            {{ new Date(task.created_at).toLocaleDateString('zh-CN') }}
          </p>
        </div>
        <span :class="['status-pill', task.status]">{{ statusLabels[task.status] }}</span>
      </div>
    </section>
    <section class="inspiration-panel">
      <div class="eyebrow">MORE THAN A DOWNLOAD</div>
      <h2>收藏之后，还有小惊喜</h2>
      <p>好内容，不止看过就忘。</p>
      <button @click="navigate('learning')">
        <span class="feature-icon lavender"><Icon name="sparkles" :size="18" /></span>
        <span>
          <strong>让字幕长出知识</strong>
          <small>提取要点，整理你的学习灵感</small>
        </span>
        <Icon name="right" :size="15" />
      </button>
      <button @click="navigate('library')">
        <span class="feature-icon peach"><Icon name="folder" :size="18" /></span>
        <span>
          <strong>给精彩一个小抽屉</strong>
          <small>合集、标签、笔记，井井有条</small>
        </span>
        <Icon name="right" :size="15" />
      </button>
    </section>
  </div>
</template>
<style scoped>
.hero-panel {
  min-height: 264px;
  background: linear-gradient(105deg, #eef3e8, #f4f5ec 65%, #f0f3e9);
  border: 1px solid #e5ebdc;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 30px 38px;
  overflow: hidden;
  position: relative;
}
.hero-copy {
  position: relative;
  z-index: 1;
}
.hero-copy .eyebrow {
  font-size: 9px;
  letter-spacing: 1.9px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.hero-dot {
  width: 5px;
  height: 5px;
  background: #9fb391;
  border-radius: 50%;
}
.hero-copy h1 {
  font-size: 32px;
  margin: 14px 0 10px;
  line-height: 1.45;
  letter-spacing: 0.6px;
  color: #4e6648;
  font-weight: 600;
}
.heading-period {
  color: #a9b99c;
}
.hero-copy p {
  font-size: 12px;
  color: #89987c;
  line-height: 1.95;
}
.hero-tags {
  display: flex;
  gap: 20px;
  margin-top: 20px;
  font-size: 9px;
  color: #96a489;
}
.hero-tags span {
  display: flex;
  align-items: center;
  gap: 5px;
}
.hero-art {
  width: 310px;
  height: 232px;
  margin-right: 12px;
}
.storage-stat {
  font-size: 20px !important;
}
.download-panel {
  padding: 27px 28px 0;
}
.download-caption {
  font-size: 11px;
  color: #9ca591;
  margin: 11px 0 19px;
}
.url-field {
  display: flex;
  align-items: center;
  border: 1px solid #dce5d4;
  background: #fbfdf8;
  border-radius: 9px;
  padding: 6px 7px 6px 17px;
  gap: 13px;
  box-shadow: 0 0 0 3px #e7eedc20;
}
.url-field > svg {
  color: #a6b59a;
}
.url-field input,
.url-field textarea {
  border: 0;
  box-shadow: none;
  background: none;
  padding: 10px 0;
  font-size: 12px;
  min-width: 0;
}
.inspect-button {
  font-size: 10px;
  padding: 9px 14px;
  white-space: nowrap;
  background: #f1f5eb;
  color: #80966f;
  border-color: #e5ebdd;
  box-shadow: none;
}
.platform-line {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 14px 0 27px;
  font-size: 9px;
  flex-wrap: wrap;
  color: #a6ae9e;
}
.platform {
  display: flex;
  gap: 4px;
  align-items: center;
  color: #939f8b;
  font-size: 9px;
}
.platform-letter {
  font-weight: 700;
  color: #ae9e90;
  font-size: 11px;
}
.bili .platform-letter {
  color: #a9bac4;
}
.douyin .platform-letter {
  color: #adb0bb;
}
.vimeo .platform-letter {
  color: #98b7bc;
}
.platform.more {
  color: #b4baad;
}
.sample-link {
  margin-left: auto;
  font-size: 9px;
}
.preset-label {
  font-size: 12px;
  font-weight: 500;
  display: flex;
  gap: 15px;
  align-items: center;
  margin-bottom: 13px;
}
.preset-label span {
  font-size: 9px;
  color: #acb3a3;
  font-weight: 400;
}
.preset-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.preset-card {
  background: #fff;
  border: 1px solid #e9ece3;
  border-radius: 10px;
  padding: 15px 11px;
  display: flex;
  align-items: center;
  gap: 10px;
  text-align: left;
  position: relative;
  transition:
    background 0.2s,
    border 0.2s;
}
.preset-card:hover {
  border-color: #c6d6bb;
}
.preset-card.selected {
  background: #f5f8f0;
  border-color: #aabe99;
  box-shadow: 0 0 0 1px #aabe9912;
}
.preset-card .feature-icon {
  width: 33px;
  height: 35px;
  border-radius: 8px;
}
.preset-card strong {
  font-size: 11px;
  font-weight: 500;
  display: block;
  white-space: nowrap;
}
.preset-card small {
  font-size: 8px;
  color: #a2ac97;
  display: block;
  margin-top: 6px;
  white-space: nowrap;
}
.preset-radio {
  width: 12px;
  height: 12px;
  border: 1px solid #dce4d3;
  position: absolute;
  right: 7px;
  top: 7px;
  border-radius: 50%;
  display: grid;
  place-items: center;
}
.selected .preset-radio {
  background: #8ca577;
  border-color: #8ca577;
  color: white;
}
.download-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 22px 0;
  gap: 20px;
}
.collection-inline {
  display: flex;
  align-items: center;
  gap: 9px;
  white-space: nowrap;
  font-size: 10px;
  color: #9aa78d;
}
.collection-inline select {
  width: auto;
  min-width: 112px;
  font-size: 10px;
  background: #f6f8f1;
  border-color: #e8ecdf;
  padding: 6px 24px 6px 10px;
  margin: 0;
}
.advanced-toggle {
  font-size: 10px;
}
.download-bottom {
  margin: 0 -28px;
  padding: 18px 28px;
  border-top: 1px solid #edf0e7;
  background: #fcfdf9;
  border-radius: 0 0 14px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
}
.download-bottom > span {
  display: flex;
  gap: 7px;
  align-items: center;
  font-size: 9px;
  color: #b0b9a4;
}
.download-submit {
  min-width: 143px;
  padding: 11px 18px;
  font-size: 11px;
}
.advanced-options {
  padding: 18px;
  background: #f7f9f3;
  border: 1px solid #edf0e7;
  border-radius: 10px;
  margin: 0 0 20px;
}
.advanced-options .form-row + .form-row {
  margin-top: 15px;
}
.advanced-options p {
  font-size: 9px;
  margin-top: 13px;
}
.form-error {
  margin: 0 0 17px;
}
.inspection-card {
  display: flex;
  gap: 14px;
  align-items: center;
  background: #f4f7ef;
  border-radius: 9px;
  padding: 13px;
  margin: -10px 0 23px;
}
.inspection-card > img {
  width: 85px;
  height: 55px;
  object-fit: cover;
  border-radius: 6px;
}
.inspection-card > div:nth-child(2) {
  flex: 1;
  min-width: 0;
}
.inspection-card h3 {
  font-size: 12px;
}
.inspection-card p {
  font-size: 10px;
  color: #95a18a;
  margin: 4px 0 6px;
}
.inspection-card > svg {
  color: #93ac85;
}
.home-lower {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 20px;
  margin-top: 24px;
}
.recent-panel {
  padding: 23px 26px;
}
.recent-panel :deep(.empty-state) {
  padding: 26px 10px 9px;
}
.recent-panel :deep(.empty-icon) {
  height: 44px;
  width: 44px;
  border-radius: 14px;
  margin-bottom: 12px;
}
.recent-panel :deep(.empty-state p) {
  margin-bottom: 6px;
  font-size: 10px;
}
.recent-panel :deep(.empty-state h3) {
  font-size: 11px;
}
.recent-panel :deep(.empty-icon svg) {
  width: 24px;
}
.recent-row {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 15px 0;
  border-bottom: 1px solid #f0f2eb;
}
.recent-row:last-child {
  border: 0;
  padding-bottom: 0;
}
.recent-row > div {
  flex: 1;
  min-width: 0;
}
.recent-row strong {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 11px;
  font-weight: 500;
}
.recent-row p {
  font-size: 9px;
  color: #a5b098;
  margin-top: 5px;
}
.inspiration-panel {
  background: #f2f0e9;
  border: 1px solid #ebe7dd;
  border-radius: 14px;
  padding: 23px 24px;
}
.inspiration-panel > .eyebrow {
  font-size: 8px;
  color: #a6a391;
  letter-spacing: 1.3px;
  margin-bottom: 8px;
}
.inspiration-panel h2 {
  font-size: 14px;
  color: #858575;
}
.inspiration-panel > p {
  font-size: 10px;
  color: #aaa895;
  margin-top: 6px;
  margin-bottom: 15px;
}
.inspiration-panel button {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 0;
  background: none;
  width: 100%;
  text-align: left;
  padding: 9px 0;
}
.inspiration-panel button > span:nth-child(2) {
  flex: 1;
}
.inspiration-panel strong {
  font-size: 11px;
  font-weight: 500;
  color: #888a78;
}
.inspiration-panel small {
  display: block;
  font-size: 9px;
  color: #afaf9c;
  margin-top: 5px;
}
.inspiration-panel button > svg {
  color: #b2b7a3;
}
.inspiration-panel .feature-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
}
@media (max-width: 1150px) {
  .preset-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .hero-art {
    width: 250px;
    margin-right: -18px;
  }
  .hero-copy h1 {
    font-size: 28px;
  }
  .stats-grid {
    gap: 10px;
  }
  .stat-card {
    padding: 16px 13px;
    gap: 10px;
  }
  .stat-card .feature-icon {
    width: 32px;
    height: 34px;
  }
  .stat-card strong {
    font-size: 20px;
  }
  .stat-card p {
    font-size: 9px;
  }
}
@media (max-width: 650px) {
  .hero-panel {
    padding: 25px 23px;
    min-height: 242px;
  }
  .hero-art {
    position: absolute;
    width: 175px;
    right: -18px;
    top: 40px;
    opacity: 0.6;
  }
  .hero-copy .eyebrow {
    font-size: 7px;
    letter-spacing: 1px;
  }
  .hero-copy h1 {
    font-size: 25px;
  }
  .hero-copy p {
    font-size: 10px;
  }
  .hero-tags {
    gap: 10px;
    font-size: 8px;
    flex-wrap: wrap;
  }
  .download-panel {
    padding: 21px 18px 0;
  }
  .download-panel .panel-heading {
    flex-wrap: wrap;
  }
  .download-caption {
    font-size: 10px;
  }
  .download-bottom {
    margin: 0 -18px;
    padding: 15px 18px;
  }
  .download-bottom > span {
    font-size: 8px;
    max-width: 150px;
    line-height: 1.7;
  }
  .download-submit {
    min-width: 110px;
    padding: 10px;
    font-size: 10px;
  }
  .url-field {
    gap: 8px;
    padding-left: 10px;
  }
  .url-field input {
    font-size: 10px;
  }
  .url-field > .button {
    font-size: 9px;
    padding: 8px;
  }
  .url-field > .button svg {
    display: none;
  }
  .platform-line {
    gap: 10px;
    font-size: 8px;
  }
  .sample-link {
    margin-left: 0;
  }
  .platform.more {
    display: none;
  }
  .preset-card {
    padding: 15px 10px;
  }
  .preset-card small {
    font-size: 7.5px;
  }
  .preset-label {
    display: block;
  }
  .preset-label span {
    display: block;
    margin-top: 7px;
  }
  .home-lower {
    grid-template-columns: 1fr;
  }
  .form-row {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  .advanced-toggle {
    font-size: 9px;
  }
  .download-options {
    gap: 10px;
  }
  .collection-inline {
    gap: 6px;
  }
  .hero-art {
    pointer-events: none;
  }
}
</style>
