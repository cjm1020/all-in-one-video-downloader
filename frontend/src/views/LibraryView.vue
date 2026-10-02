<script setup lang="ts">
import { computed, ref } from 'vue'
import Icon from '../components/Icon.vue'
import EmptyState from '../components/EmptyState.vue'
import Modal from '../components/Modal.vue'
import { api, bytes, duration, message, navigate, notify, presets, refresh, store } from '../store'
import type { Task, TaskDetail } from '../types'

const collectionFilter = ref('all'),
  query = ref(''),
  onlyFavorites = ref(false)
const showCollection = ref(false),
  collectionName = ref(''),
  collectionColor = ref('sage')
const current = ref<TaskDetail | null>(null),
  loadingId = ref(''),
  title = ref(''),
  notes = ref(''),
  tags = ref(''),
  collection = ref('inbox')
const saving = ref(false),
  deleting = ref(false),
  confirmDelete = ref(false),
  confirmCollectionDelete = ref(false)
const completed = computed(() => store.tasks.filter((t) => t.status === 'completed'))
function chooseCollection(id: string) {
  collectionFilter.value = id
  confirmCollectionDelete.value = false
}
const filtered = computed(() =>
  completed.value.filter(
    (t) =>
      (collectionFilter.value === 'all' || t.collection_id === collectionFilter.value) &&
      (!onlyFavorites.value || t.favorite) &&
      `${t.title} ${t.tags.join(' ')}`.toLowerCase().includes(query.value.toLowerCase()),
  ),
)
async function favorite(task: Task) {
  try {
    await api(`/tasks/${task.id}`, { method: 'PATCH', body: JSON.stringify({ favorite: !task.favorite }) })
    await refresh()
  } catch (e) {
    notify(message(e), true)
  }
}
async function open(task: Task) {
  loadingId.value = task.id
  try {
    const detail = await api<TaskDetail>(`/tasks/${task.id}`)
    if (loadingId.value !== task.id) return
    current.value = detail
    title.value = detail.title
    notes.value = detail.notes
    tags.value = detail.tags.join(', ')
    collection.value = detail.collection_id
    confirmDelete.value = false
  } catch (e) {
    notify(message(e), true)
  } finally {
    loadingId.value = ''
  }
}
async function save() {
  if (!current.value) return
  saving.value = true
  try {
    current.value = await api<TaskDetail>(`/tasks/${current.value.id}`, {
      method: 'PATCH',
      body: JSON.stringify({
        title: title.value,
        notes: notes.value,
        tags: tags.value.split(/[,，]/),
        collection_id: collection.value,
      }),
    })
    await refresh()
    notify('资料卡已保存，灵感也留下了')
  } catch (e) {
    notify(message(e), true)
  } finally {
    saving.value = false
  }
}
async function remove() {
  if (!current.value) return
  deleting.value = true
  try {
    await api(`/tasks/${current.value.id}`, { method: 'DELETE' })
    current.value = null
    await refresh()
    notify('已删除收藏与本地文件')
  } catch (e) {
    notify(message(e), true)
  } finally {
    deleting.value = false
  }
}
async function createCollection() {
  saving.value = true
  try {
    await api('/collections', {
      method: 'POST',
      body: JSON.stringify({ name: collectionName.value, color: collectionColor.value }),
    })
    showCollection.value = false
    collectionName.value = ''
    await refresh()
    notify('新的小抽屉准备好了')
  } catch (e) {
    notify(message(e), true)
  } finally {
    saving.value = false
  }
}
async function deleteCollection() {
  try {
    await api(`/collections/${collectionFilter.value}`, { method: 'DELETE' })
    collectionFilter.value = 'all'
    confirmCollectionDelete.value = false
    await refresh()
    notify('已删除合集，内容已移到“我的收藏”')
  } catch (e) {
    notify(message(e), true)
  }
}
function learn(task: Task) {
  store.selectedLearning = task.id
  navigate('learning')
}
</script>
<template>
  <div class="page-heading">
    <div>
      <div class="eyebrow">YOUR LITTLE COLLECTION</div>
      <h1>喜欢的，都在这里</h1>
      <p>给每个精彩一个小抽屉，随时回来重温。</p>
    </div>
    <button class="button" @click="showCollection = true">
      <Icon name="folder" :size="16" />
      新建合集
    </button>
  </div>
  <div class="collection-strip">
    <button
      class="collection-card"
      :class="{ selected: collectionFilter === 'all' }"
      @click="chooseCollection('all')"
    >
      <span class="feature-icon sage"><Icon name="library" /></span>
      <span>
        <strong>全部收藏</strong>
        <small>{{ completed.length }} 个片刻</small>
      </span>
    </button>
    <button
      v-for="item in store.collections"
      :key="item.id"
      class="collection-card"
      :class="{ selected: collectionFilter === item.id }"
      @click="chooseCollection(item.id)"
    >
      <span :class="['feature-icon', item.color]"><Icon name="folder" /></span>
      <span>
        <strong>{{ item.name }}</strong>
        <small>{{ completed.filter((t) => t.collection_id === item.id).length }} 个片刻</small>
      </span>
    </button>
  </div>
  <div class="filters">
    <button class="chip" :class="{ active: onlyFavorites }" @click="onlyFavorites = !onlyFavorites">
      <Icon name="heart" :size="14" />
      特别喜欢
    </button>
    <span class="section-caption">{{ filtered.length }} 份收藏</span>
    <template v-if="!['all', 'inbox'].includes(collectionFilter)">
      <button class="text-link" @click="confirmCollectionDelete = !confirmCollectionDelete">
        删除这个合集
      </button>
      <button v-if="confirmCollectionDelete" class="button small danger" @click="deleteCollection">
        确认删除，内容移入默认合集
      </button>
    </template>
    <label class="search-field">
      <span class="sr-only">搜索标题或标签</span>
      <Icon name="search" :size="16" />
      <input v-model="query" placeholder="搜索标题或标签…" />
    </label>
  </div>
  <section v-if="!filtered.length" class="panel">
    <EmptyState
      icon="library"
      :title="completed.length ? '这个小抽屉暂时没有内容' : '收藏室，等待你的第一份精彩'"
      description="下载完成的视频会出现在这里。可以直接播放，也可以写下你的灵感。"
    >
      <button class="button small" @click="navigate('home')">
        <Icon name="plus" :size="14" />
        去收藏一个片刻
      </button>
    </EmptyState>
  </section>
  <div v-else class="media-grid">
    <article v-for="task in filtered" :key="task.id" class="panel media-card">
      <button
        class="media-cover"
        :disabled="loadingId === task.id"
        :aria-label="`播放 ${task.title}`"
        @click="open(task)"
      >
        <img v-if="task.thumbnail" :src="task.thumbnail" alt="" referrerpolicy="no-referrer" />
        <div v-else :class="['cover-placeholder', task.preset === 'audio' ? 'audio-cover' : 'video-cover']">
          <Icon :name="task.preset === 'audio' ? 'headphones' : 'video'" :size="40" />
          <span>{{ task.preset === 'audio' ? '声音，也值得收藏' : '留住一份精彩' }}</span>
        </div>
        <span class="play-overlay">
          <Icon
            :name="loadingId === task.id ? 'loader' : 'play'"
            :size="20"
            :class="{ spinner: loadingId === task.id }"
          />
        </span>
        <span class="cover-badge">
          {{
            task.clip_end !== null
              ? `${task.clip_end - (task.clip_start || 0)} 秒片段`
              : duration(task.duration)
          }}
        </span>
      </button>
      <div class="media-card-body">
        <div class="media-title">
          <h3>{{ task.title || '未命名收藏' }}</h3>
          <button
            class="icon-button"
            :class="{ favorited: task.favorite }"
            :aria-label="task.favorite ? '取消特别喜欢' : '标记特别喜欢'"
            @click="favorite(task)"
          >
            <Icon name="heart" :size="17" />
          </button>
        </div>
        <p>
          {{ task.platform || '公开媒体' }} · {{ presets.find((p) => p.id === task.preset)?.label }} ·
          {{ bytes(task.file_size) }}
        </p>
        <div v-if="task.tags.length" class="tags">
          <span v-for="tag in task.tags" :key="tag" class="tag">{{ tag }}</span>
        </div>
        <div class="media-card-bottom">
          <button class="text-link" @click="learn(task)">
            <Icon name="book" :size="13" />
            学习资料卡
          </button>
          <a class="icon-button" :href="`/api/tasks/${task.id}/file?download=true`" aria-label="下载到设备">
            <Icon name="save" :size="16" />
          </a>
        </div>
      </div>
    </article>
  </div>
  <Modal v-if="showCollection" title="给精彩一个新抽屉" @close="showCollection = false">
    <form @submit.prevent="createCollection">
      <label>
        合集名称
        <input
          v-model="collectionName"
          required
          maxlength="40"
          placeholder="例如：周末灵感、编程小课、通勤歌单"
        />
      </label>
      <div class="color-picker">
        <button
          v-for="color in ['sage', 'peach', 'lavender', 'sky']"
          :key="color"
          type="button"
          :class="['color-choice', color, { chosen: collectionColor === color }]"
          :aria-label="{ sage: '鼠尾草绿', peach: '浅杏色', lavender: '淡紫色', sky: '浅蓝色' }[color]"
          :aria-pressed="collectionColor === color"
          @click="collectionColor = color"
        >
          <Icon v-if="collectionColor === color" name="check" :size="18" />
        </button>
      </div>
      <div class="modal-actions">
        <button class="button" type="button" @click="showCollection = false">稍后再建</button>
        <button class="button primary" :disabled="saving">创建小抽屉</button>
      </div>
    </form>
  </Modal>
  <Modal v-if="current" :title="current.title || '这一份收藏'" @close="current = null">
    <audio
      v-if="current.preset === 'audio'"
      :src="`/api/tasks/${current.id}/file`"
      controls
      preload="metadata"
    ></audio>
    <video v-else :src="`/api/tasks/${current.id}/file`" controls playsinline preload="metadata"></video>
    <div class="player-links">
      <a class="text-link" :href="current.url" target="_blank" rel="noopener noreferrer">
        <Icon name="external" :size="13" />
        查看来源
      </a>
      <a class="text-link" :href="`/api/tasks/${current.id}/export`">
        <Icon name="file" :size="13" />
        导出 Markdown
      </a>
      <a class="text-link" :href="`/api/tasks/${current.id}/export?format=json`">
        <Icon name="save" :size="13" />
        导出 JSON
      </a>
      <a class="text-link" :href="`/api/tasks/${current.id}/file?download=true`">
        <Icon name="download" :size="13" />
        保存文件
      </a>
    </div>
    <div class="form-row">
      <label>
        收藏标题
        <input v-model="title" required maxlength="200" />
      </label>
      <label>
        放进哪个小抽屉
        <select v-model="collection">
          <option v-for="item in store.collections" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
      </label>
    </div>
    <label class="detail-label">
      标签（逗号分隔，最多 12 个）
      <input v-model="tags" placeholder="灵感, 教程, 周末" />
    </label>
    <label class="detail-label">
      我的灵感笔记
      <textarea v-model="notes" rows="4" maxlength="20000" placeholder="这一段，让你想到了什么？"></textarea>
    </label>
    <div class="modal-actions">
      <button class="button danger small" @click="confirmDelete = !confirmDelete">
        <Icon name="trash" :size="14" />
        删除收藏
      </button>
      <button v-if="confirmDelete" class="button danger small" :disabled="deleting" @click="remove">
        确认删除本地文件
      </button>
      <button class="button primary" :disabled="saving" @click="save">
        <Icon name="check" :size="16" />
        {{ saving ? '正在保存…' : '保存资料卡' }}
      </button>
    </div>
  </Modal>
</template>
<style scoped>
.collection-strip {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  overflow-x: auto;
  padding-bottom: 7px;
}
.collection-card {
  display: flex;
  align-items: center;
  gap: 13px;
  border: 1px solid #e8ecdf;
  background: #fff;
  border-radius: 11px;
  min-width: 170px;
  max-width: 250px;
  padding: 17px 19px;
  text-align: left;
  flex-shrink: 0;
}
.collection-card.selected {
  background: #f2f7ed;
  border-color: #b8c9a9;
}
.collection-card strong {
  font-size: 12px;
  font-weight: 500;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 160px;
}
.collection-card small {
  font-size: 10px;
  color: #a2ad94;
  display: block;
  margin-top: 7px;
}
.media-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}
.media-card {
  overflow: hidden;
}
.media-cover {
  width: 100%;
  aspect-ratio: 16/10;
  background: #edf2e7;
  border: 0;
  padding: 0;
  position: relative;
  display: grid;
  place-items: center;
  overflow: hidden;
}
.media-cover > img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 17px;
  align-items: center;
  justify-content: center;
  color: #aac09a;
  background: linear-gradient(135deg, #eaf0e5, #f1f5e9);
}
.cover-placeholder span {
  font-size: 10px;
  letter-spacing: 1px;
}
.cover-placeholder.audio-cover {
  background: linear-gradient(135deg, #e9eef4, #e7eff0);
  color: #9fb5c4;
}
.play-overlay {
  position: absolute;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #fff9;
  color: #6d8b5d;
  opacity: 0;
  transition: opacity 0.2s;
}
.media-cover:hover .play-overlay,
.media-cover:focus-visible .play-overlay {
  opacity: 1;
}
.cover-badge {
  position: absolute;
  bottom: 9px;
  right: 9px;
  font-size: 9px;
  background: #34483d75;
  color: #fff;
  padding: 3px 6px;
  border-radius: 4px;
}
.media-card-body {
  padding: 17px 19px 10px;
}
.media-title {
  display: flex;
  align-items: center;
  gap: 6px;
}
.media-title h3 {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 500;
}
.media-title .icon-button {
  width: 25px;
  height: 25px;
}
.media-title .favorited {
  color: #c68e86;
}
.media-title .favorited :deep(svg) {
  fill: #e6bcb040;
}
.media-card-body > p {
  font-size: 9px;
  color: #9eaa90;
  margin-top: 5px;
}
.media-card-body > .tags {
  margin-top: 10px;
}
.media-card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 15px;
  border-top: 1px solid #eef1e6;
  padding-top: 6px;
}
.media-card-bottom .text-link {
  font-size: 9px;
}
.color-picker {
  display: flex;
  gap: 12px;
  margin-top: 22px;
}
.color-choice {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 2px solid transparent;
  display: grid;
  place-items: center;
}
.color-choice.chosen {
  border-color: #a6b99a;
}
.player-links {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  margin-top: 15px;
}
.detail-label {
  margin-top: 17px;
}
.modal-actions .primary {
  margin-left: auto;
}
@media (max-width: 1050px) {
  .media-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 650px) {
  .media-grid {
    gap: 12px;
  }
  .media-card-body {
    padding: 12px 12px 6px;
  }
  .media-title h3 {
    font-size: 10px;
  }
  .media-card-body > p {
    font-size: 8px;
  }
  .cover-placeholder span {
    font-size: 8px;
  }
  .media-cover .play-overlay {
    opacity: 0.8;
    width: 30px;
    height: 30px;
  }
  .media-cover .play-overlay svg {
    width: 15px;
  }
  .cover-placeholder > svg {
    width: 30px;
  }
  .collection-card {
    min-width: 150px;
    padding: 15px;
  }
  .player-links {
    gap: 12px;
  }
  .player-links a {
    font-size: 10px;
  }
  .modal-actions {
    flex-wrap: wrap;
  }
  .modal-actions .primary {
    margin-left: 0;
  }
}
</style>
