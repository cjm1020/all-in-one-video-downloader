<script setup lang="ts">
import { nextTick, onMounted, reactive, ref, watch } from 'vue'
import Icon from './Icon.vue'
import { api, message, notify } from '../store'
import type { TaskDetail } from '../types'
interface Marker {
  id: string
  task_id: string
  position: number
  label: string
  notes: string
  color: string
}
const props = defineProps<{ task: TaskDetail; position: number | null }>()
const markers = ref<Marker[]>([]),
  player = ref<HTMLMediaElement | null>(null),
  open = ref(false),
  busy = ref(false),
  error = ref('')
const form = reactive({ position: 0, label: '', notes: '', color: 'sage' })
function time(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`
}
async function load() {
  const id = props.task.id
  try {
    const value = await api<Marker[]>(`/knowledge/tasks/${id}/markers`)
    if (props.task.id === id) markers.value = value
  } catch (e) {
    error.value = message(e)
  }
}
function seek(position: number) {
  if (player.value) player.value.currentTime = position
  form.position = position
}
async function openMarker(position: number) {
  open.value = true
  await nextTick()
  seek(position)
}
function fromPlayer() {
  form.position = Math.round(player.value?.currentTime || 0)
}
async function save() {
  busy.value = true
  error.value = ''
  try {
    await api(`/knowledge/tasks/${props.task.id}/markers`, { method: 'POST', body: JSON.stringify(form) })
    form.label = ''
    form.notes = ''
    await load()
    notify('片段书签已保存')
  } catch (e) {
    error.value = message(e)
  } finally {
    busy.value = false
  }
}
async function remove(marker: Marker) {
  busy.value = true
  try {
    await api(`/knowledge/markers/${marker.id}`, { method: 'DELETE' })
    await load()
    notify('片段书签已移除')
  } catch (e) {
    error.value = message(e)
  } finally {
    busy.value = false
  }
}
function metadata() {
  if (props.position !== null) seek(props.position)
}
watch(
  () => props.task.id,
  async () => {
    markers.value = []
    form.label = ''
    form.notes = ''
    error.value = ''
    await load()
    await nextTick()
    if (props.position !== null) {
      open.value = true
      seek(props.position)
    }
  },
)
watch(
  () => props.position,
  async (value) => {
    if (value !== null) {
      open.value = true
      await nextTick()
      seek(value)
    }
  },
)
onMounted(() => {
  load()
  if (props.position !== null) {
    open.value = true
    form.position = props.position
  }
})
</script>
<template>
  <section class="task-markers" aria-label="片段书签">
    <div class="panel-heading">
      <h3>
        <Icon name="bookmark" :size="16" />
        片段书签
        <span class="section-caption">{{ markers.length }}</span>
      </h3>
      <button class="text-link" :aria-expanded="open" @click="open = !open">
        {{ open ? '收起播放器' : '打开播放器' }}
        <Icon name="down" :size="13" />
      </button>
    </div>
    <template v-if="open">
      <audio
        v-if="task.preset === 'audio'"
        :key="task.id"
        ref="player"
        :src="`/api/tasks/${task.id}/file`"
        controls
        preload="metadata"
        @loadedmetadata="metadata"
      ></audio>
      <video
        v-else
        :key="task.id"
        ref="player"
        :src="`/api/tasks/${task.id}/file`"
        controls
        playsinline
        preload="metadata"
        @loadedmetadata="metadata"
      ></video>
    </template>
    <p class="hint">为值得回看的片段标记时间，记录想法，再从书签回到原视频。</p>
    <div class="marker-list">
      <article v-for="marker in markers" :key="marker.id" :class="['marker', marker.color]">
        <button
          class="marker-seek"
          @click="openMarker(marker.position)"
        >
          <strong>{{ time(marker.position) }} · {{ marker.label }}</strong>
          <span v-if="marker.notes">{{ marker.notes }}</span>
        </button>
        <button
          class="icon-button"
          :aria-label="`删除书签 ${marker.label}`"
          :disabled="busy"
          @click="remove(marker)"
        >
          <Icon name="x" :size="14" />
        </button>
      </article>
    </div>
    <form class="marker-form" @submit.prevent="save">
      <div class="form-row">
        <label>
          位置（秒）
          <input
            v-model.number="form.position"
            type="number"
            min="0"
            :max="task.duration || 86400"
            step="0.1"
            required
          />
        </label>
        <label>
          片段标题
          <input v-model="form.label" required maxlength="120" placeholder="这个观点值得再看" />
        </label>
      </div>
      <button v-if="open" class="text-link use-position" type="button" @click="fromPlayer">
        <Icon name="clock" :size="12" />
        使用播放器当前位置
      </button>
      <label class="field">
        片段笔记
        <input v-model="form.notes" maxlength="5000" placeholder="记录你的观察或待办…" />
      </label>
      <div class="marker-actions">
        <label>
          书签颜色
          <select v-model="form.color">
            <option value="sage">鼠尾草绿</option>
            <option value="peach">暖桃色</option>
            <option value="lavender">薰衣草紫</option>
            <option value="sky">晴空蓝</option>
          </select>
        </label>
        <button class="button small" :disabled="busy || !form.label.trim()">
          {{ busy ? '正在保存…' : '添加片段书签' }}
        </button>
      </div>
    </form>
    <p v-if="error" class="error-text" role="alert">{{ error }}</p>
  </section>
</template>
<style scoped>
.task-markers {
  margin-top: 25px;
  border-top: 1px solid var(--line);
  padding-top: 22px;
}
h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.hint {
  font-size: 10px;
  color: var(--muted);
  margin: 12px 0 16px;
}
video,
audio {
  width: 100%;
  margin-top: 17px;
  border-radius: 10px;
}
video {
  max-height: 300px;
  background: #24362b;
}
.marker {
  display: flex;
  align-items: start;
  padding: 12px;
  border-radius: 9px;
  margin: 8px 0;
}
.marker-seek {
  flex: 1;
  min-width: 0;
  background: none;
  border: 0;
  text-align: left;
  padding: 4px 0;
}
.marker strong {
  display: block;
  font-size: 11px;
  overflow-wrap: anywhere;
}
.marker span {
  display: block;
  font-size: 10px;
  margin-top: 5px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}
.marker-form {
  padding: 17px;
  border-radius: 10px;
  background: #f8faf4;
  margin-top: 17px;
}
.marker-form .form-row {
  margin: 0;
}
.marker-form label {
  font-size: 10px;
}
.marker-form .form-row label:first-child {
  max-width: 120px;
}
.field {
  margin-top: 13px;
}
.use-position {
  margin-top: 12px;
}
.marker-actions {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 15px;
  margin-top: 16px;
}
.marker-actions label {
  max-width: 160px;
}
.error-text {
  margin-top: 12px;
}
@media (max-width: 650px) {
  .marker-form {
    padding: 14px;
  }
  .marker-actions {
    flex-wrap: wrap;
  }
  .marker-actions label {
    max-width: 140px;
  }
}
</style>
