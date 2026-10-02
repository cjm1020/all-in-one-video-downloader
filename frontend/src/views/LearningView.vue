<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import Icon from '../components/Icon.vue'
import KnowledgeSearch from '../components/KnowledgeSearch.vue'
import TaskMarkers from '../components/TaskMarkers.vue'
import StudyCards from '../components/StudyCards.vue'
import CardReview from '../components/CardReview.vue'
import { api, duration, message, navigate, notify, refresh, store } from '../store'
import type { TaskDetail } from '../types'

const selected = ref(store.selectedLearning),
  detail = ref<TaskDetail | null>(null)
const transcript = ref(''),
  importing = ref(false),
  busy = ref(''),
  loading = ref(false)
const available = computed(() => store.tasks.filter((t) => t.status === 'completed'))
const filter = ref(''),
  showTranscript = ref(false)
const filtered = computed(() =>
  available.value.filter((t) => t.title.toLowerCase().includes(filter.value.toLowerCase())),
)
const selectedPosition = ref<number | null>(null)
const reviewKey = ref(0)
async function selectResult(id: string, position: number | null) {
  selectedPosition.value = position
  await select(id)
}
async function select(id: string) {
  selected.value = id
  store.selectedLearning = id
  loading.value = true
  try {
    const value = await api<TaskDetail>(`/tasks/${id}`)
    if (selected.value === id) {
      detail.value = value
      transcript.value = ''
      importing.value = false
    }
  } catch (e) {
    notify(message(e), true)
  } finally {
    loading.value = false
  }
}
async function readFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (file.size > 750000) {
    notify('字幕文件较大，请选取小于 750 KB 的文件', true)
    return
  }
  transcript.value = await file.text()
}
async function importTranscript() {
  if (!detail.value) return
  const id = detail.value.id
  busy.value = 'import'
  try {
    const value = await api<TaskDetail>(`/tasks/${id}/transcript`, {
      method: 'POST',
      body: JSON.stringify({ text: transcript.value }),
    })
    if (selected.value === id) {
      detail.value = value
      importing.value = false
    }
    await refresh()
    notify('字幕已种进学习花园')
  } catch (e) {
    notify(message(e), true)
  } finally {
    busy.value = ''
  }
}
async function summarize(mode: string) {
  if (!detail.value) return
  const id = detail.value.id
  busy.value = mode
  try {
    const value = await api<TaskDetail>(`/tasks/${id}/summary`, {
      method: 'POST',
      body: JSON.stringify({ mode }),
    })
    if (selected.value === id) detail.value = value
    await refresh()
    notify('这份学习要点已经整理好')
  } catch (e) {
    notify(message(e), true)
  } finally {
    busy.value = ''
  }
}
onMounted(() => {
  if (selected.value) select(selected.value)
})
</script>
<template>
  <div class="page-heading">
    <div>
      <div class="eyebrow">LET YOUR IDEAS GROW</div>
      <h1>让好内容，长出小收获</h1>
      <p>从字幕里提取要点，让每次观看都留下一点知识。</p>
    </div>
    <span class="badge lavender">
      <Icon name="leaf" :size="12" />
      学习花园
    </span>
  </div>
  <KnowledgeSearch @select="selectResult" />
  <CardReview :refresh-key="reviewKey" @select="selectResult($event, null)" />
  <div class="learning-banner">
    <span class="feature-icon lavender"><Icon name="sparkles" :size="23" /></span>
    <div>
      <strong>一份字幕，一颗灵感种子</strong>
      <p>本地要点直接提取字幕原句，无需密钥。AI 摘要需配置 DeepSeek，会将选中视频的字幕发送给服务商。</p>
    </div>
    <span class="badge" :class="store.status?.ai_available ? 'sage' : 'peach'">
      {{ store.status?.ai_available ? 'AI 已配置' : '本地模式可用' }}
    </span>
  </div>
  <div v-if="available.length" class="learning-layout">
    <aside class="panel learning-list">
      <div class="panel-heading">
        <h2>
          <Icon name="bookmark" :size="17" />
          选择一份收藏
        </h2>
        <span class="section-caption">{{ available.length }}</span>
      </div>
      <label class="search-field">
        <span class="sr-only">搜索学习内容</span>
        <Icon name="search" :size="15" />
        <input v-model="filter" placeholder="找一份学习素材…" />
      </label>
      <button
        v-for="task in filtered"
        :key="task.id"
        class="learning-item"
        :class="{ active: selected === task.id }"
        @click="select(task.id)"
      >
        <span :class="['feature-icon', task.has_summary ? 'sage' : 'lavender']">
          <Icon :name="task.has_summary ? 'checks' : 'video'" :size="17" />
        </span>
        <span>
          <strong>{{ task.title || '未命名收藏' }}</strong>
          <small>
            {{ task.has_summary ? '已整理要点' : task.has_transcript ? '字幕已准备好' : '等待字幕种子' }} ·
            {{ duration(task.duration) }}
          </small>
        </span>
      </button>
      <p v-if="!filtered.length" class="muted no-results">没有找到这份收藏</p>
    </aside>
    <section class="panel learning-content">
      <EmptyState
        v-if="!detail"
        icon="leaf"
        title="选一份内容，种下小收获"
        description="从左侧选择一个视频，导入字幕，整理属于你的学习资料卡。"
      />
      <template v-else>
        <div class="learning-content-heading">
          <div>
            <span class="eyebrow">{{ detail.platform || 'YOUR COLLECTION' }}</span>
            <h2>{{ detail.title }}</h2>
          </div>
          <a :href="`/api/tasks/${detail.id}/export`" class="button small">
            <Icon name="file" :size="14" />
            导出资料卡
          </a>
        </div>
        <div class="learning-actions">
          <button class="button small" :disabled="!!busy || loading" @click="importing = !importing">
            <Icon name="upload" :size="14" />
            {{ detail.transcript ? '替换字幕' : '导入字幕' }}
          </button>
          <button
            class="button small primary"
            :disabled="!detail.transcript || !!busy || loading"
            @click="summarize('local')"
          >
            <Icon
              :name="busy === 'local' ? 'loader' : 'leaf'"
              :size="14"
              :class="{ spinner: busy === 'local' }"
            />
            提取本地要点
          </button>
          <button
            class="button small"
            :disabled="!detail.transcript || !!busy || loading || !store.status?.ai_available"
            @click="summarize('ai')"
          >
            <Icon
              :name="busy === 'ai' ? 'loader' : 'sparkles'"
              :size="14"
              :class="{ spinner: busy === 'ai' }"
            />
            {{ busy === 'ai' ? 'AI 正在整理…' : 'AI 学习摘要' }}
          </button>
        </div>
        <form v-if="importing" class="transcript-import" @submit.prevent="importTranscript">
          <label>
            上传 SRT、VTT 或 TXT
            <input type="file" accept=".srt,.vtt,.txt" @change="readFile" />
          </label>
          <label>
            或粘贴字幕文本
            <textarea
              v-model="transcript"
              rows="7"
              maxlength="250000"
              placeholder="把字幕带过来，让灵感开始发芽…"
              required
            ></textarea>
          </label>
          <p class="muted">替换字幕后，旧摘要会清除。最多 250,000 字符。</p>
          <div class="modal-actions">
            <button type="button" class="button small" @click="importing = false">取消</button>
            <button class="button primary small" :disabled="!!busy || !transcript.trim()">
              {{ busy === 'import' ? '正在导入…' : '种下字幕' }}
            </button>
          </div>
        </form>
        <div v-if="detail.summary" class="summary-card">
          <div class="summary-heading">
            <span class="feature-icon sage"><Icon name="leaf" :size="18" /></span>
            <h3>{{ detail.summary_mode === 'ai' ? 'AI 整理的学习摘要' : '从字幕里长出的要点' }}</h3>
            <span class="badge">{{ detail.summary_mode === 'ai' ? 'DEEPSEEK' : 'LOCAL' }}</span>
          </div>
          <div class="summary-text">{{ detail.summary }}</div>
          <p class="summary-hint">
            {{
              detail.summary_mode === 'ai'
                ? 'AI 可能遗漏或误解内容，请对照原视频与字幕。'
                : '依据字幕原句进行频率排序提取，可作为复习线索。'
            }}
          </p>
        </div>
        <EmptyState
          v-else-if="!importing"
          icon="sparkles"
          :title="detail.transcript ? '字幕已就位，开始收获吧' : '这里还缺一颗字幕种子'"
          :description="
            detail.transcript
              ? '点击提取本地要点，或使用 AI 整理学习摘要。'
              : '这个视频没有自动获取到字幕，可以导入 SRT、VTT 或 TXT；没有字幕时不会生成摘要。'
          "
        />
        <TaskMarkers :task="detail" :position="selectedPosition" />
        <StudyCards :task="detail" @changed="reviewKey++" />
        <div v-if="detail.notes" class="learning-notes">
          <h3>
            <Icon name="file" :size="15" />
            我的灵感笔记
          </h3>
          <p>{{ detail.notes }}</p>
        </div>
        <div v-if="detail.transcript" class="transcript-section">
          <button class="text-link" :aria-expanded="showTranscript" @click="showTranscript = !showTranscript">
            <Icon name="file" :size="15" />
            {{ showTranscript ? '收起完整字幕' : '查看完整字幕' }} ·
            {{ detail.transcript.length.toLocaleString() }} 字符
            <Icon name="down" :size="13" />
          </button>
          <a class="text-link" :href="`/api/tasks/${detail.id}/export?format=transcript`">
            导出 TXT
            <Icon name="save" :size="12" />
          </a>
          <pre v-if="showTranscript">{{ detail.transcript }}</pre>
        </div>
      </template>
    </section>
  </div>
  <section v-else class="panel">
    <EmptyState
      icon="leaf"
      title="花园里的第一颗种子，在等你"
      description="先下载一个喜欢的视频，再带上字幕，让知识在这里慢慢生长。"
    >
      <button class="button small" @click="navigate('home')">
        <Icon name="plus" :size="14" />
        去收藏学习素材
      </button>
    </EmptyState>
  </section>
</template>
<style scoped>
.page-heading > .badge {
  display: flex;
  gap: 5px;
  align-items: center;
}
.learning-banner {
  display: flex;
  align-items: center;
  gap: 15px;
  background: #f0edf5;
  border: 1px solid #e7e0ef;
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 25px;
}
.learning-banner > div {
  flex: 1;
}
.learning-banner strong {
  font-size: 12px;
  font-weight: 500;
  color: #8e81a3;
}
.learning-banner p {
  font-size: 10px;
  color: #a097ac;
  margin-top: 6px;
}
.learning-layout {
  display: grid;
  grid-template-columns: 265px 1fr;
  gap: 20px;
  align-items: start;
}
.learning-list {
  padding: 20px 15px;
}
.learning-list h2 {
  font-size: 12px;
}
.learning-list .search-field {
  display: block;
  margin: 19px 0 13px;
}
.learning-list .search-field input {
  font-size: 10px;
}
.learning-item {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 0;
  background: none;
  padding: 14px 10px;
  width: 100%;
  text-align: left;
  border-radius: 8px;
  margin-top: 3px;
}
.learning-item.active {
  background: #f1f6eb;
}
.learning-item:hover {
  background: #f5f7f0;
}
.learning-item > .feature-icon {
  width: 30px;
  height: 33px;
  border-radius: 8px;
}
.learning-item > span:nth-child(2) {
  min-width: 0;
}
.learning-item strong {
  font-size: 10px;
  display: block;
  font-weight: 500;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.learning-item small {
  font-size: 8px;
  color: #a4af98;
  display: block;
  margin-top: 6px;
}
.learning-content {
  padding: 26px;
  min-height: 390px;
}
.learning-content-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 15px;
}
.learning-content-heading .eyebrow {
  font-size: 9px;
  letter-spacing: 1px;
}
.learning-content-heading h2 {
  font-size: 16px;
  margin-top: 8px;
  line-height: 1.6;
}
.learning-content-heading a {
  white-space: nowrap;
}
.learning-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 24px;
}
.transcript-import {
  padding: 20px;
  background: #f7f9f3;
  border-radius: 10px;
  margin-top: 20px;
}
.transcript-import label + label {
  margin-top: 17px;
}
.transcript-import p {
  font-size: 9px;
  margin-top: 10px;
}
.summary-card {
  background: #f6f9f0;
  border: 1px solid #e6edda;
  border-radius: 11px;
  margin-top: 25px;
  padding: 20px;
}
.summary-heading {
  display: flex;
  align-items: center;
  gap: 11px;
}
.summary-heading h3 {
  font-size: 12px;
  font-weight: 500;
  flex: 1;
}
.summary-heading .feature-icon {
  width: 31px;
  height: 31px;
  border-radius: 9px;
}
.summary-text {
  font-size: 12px;
  color: #738768;
  line-height: 2.1;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  margin-top: 18px;
}
.summary-hint {
  font-size: 9px;
  color: #acb69c;
  margin-top: 20px;
  border-top: 1px solid #e7eddd;
  padding-top: 12px;
}
.learning-notes {
  margin-top: 25px;
  padding: 20px;
  background: #fbf7f0;
  border-radius: 10px;
}
.learning-notes h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #b4a085;
}
.learning-notes p {
  white-space: pre-wrap;
  font-size: 11px;
  color: #a59a86;
  margin-top: 12px;
  overflow-wrap: anywhere;
}
.transcript-section {
  border-top: 1px solid #e9eddf;
  margin-top: 25px;
  padding-top: 20px;
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 15px;
}
.transcript-section pre {
  white-space: pre-wrap;
  width: 100%;
  max-height: 350px;
  overflow: auto;
  color: #97a18e;
  font: 10px/2 inherit;
  background: #f7f9f3;
  padding: 15px;
  border-radius: 8px;
  overflow-wrap: anywhere;
}
.no-results {
  font-size: 11px;
  padding: 20px 10px;
}
@media (max-width: 1050px) {
  .learning-layout {
    grid-template-columns: 210px 1fr;
  }
}
@media (max-width: 650px) {
  .learning-layout {
    grid-template-columns: 1fr;
  }
  .learning-list {
    max-height: 270px;
    overflow: auto;
  }
  .learning-content {
    padding: 20px;
  }
  .learning-banner {
    padding: 17px;
    align-items: flex-start;
  }
  .learning-banner > .badge {
    display: none;
  }
  .learning-content-heading {
    align-items: flex-start;
  }
  .learning-content-heading h2 {
    font-size: 14px;
  }
  .learning-content-heading .button {
    font-size: 9px;
    padding: 6px;
  }
  .summary-card {
    padding: 16px;
  }
  .summary-heading h3 {
    font-size: 11px;
  }
  .summary-text {
    font-size: 11px;
  }
}
</style>
