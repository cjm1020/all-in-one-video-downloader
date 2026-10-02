<script setup lang="ts">
import { computed, ref } from 'vue'
import Modal from './Modal.vue'
import Icon from './Icon.vue'
import { api, message, notify, statusLabels, store } from '../store'

const props = defineProps<{ projectId: string; taskIds: string[] }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const selected = ref([...props.taskIds]),
  query = ref(''),
  busy = ref(false),
  error = ref('')
const tasks = computed(() =>
  store.tasks.filter((task) => `${task.title} ${task.url}`.toLowerCase().includes(query.value.toLowerCase())),
)
async function save() {
  busy.value = true
  error.value = ''
  try {
    await api(`/studio/projects/${props.projectId}/items`, {
      method: 'PUT',
      body: JSON.stringify({ task_ids: selected.value }),
    })
    notify('项目素材清单已更新')
    emit('saved')
  } catch (e) {
    error.value = message(e)
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <Modal title="选择项目素材" @close="emit('close')">
    <p class="muted hint">下载队列中的素材也可以加入，完成后会自动更新交付检查。</p>
    <label class="search-field">
      <span class="sr-only">搜索项目素材</span>
      <Icon name="search" :size="16" />
      <input v-model="query" placeholder="搜索标题或来源链接…" />
    </label>
    <div class="selection-actions">
      <span class="section-caption">已选择 {{ selected.length }} 份素材</span>
      <button
        type="button"
        class="text-link"
        @click="selected = Array.from(new Set([...selected, ...tasks.map((t) => t.id)]))"
      >
        全选搜索结果
      </button>
      <button type="button" class="text-link" @click="selected = []">清空选择</button>
    </div>
    <div class="task-options">
      <label v-for="task in tasks" :key="task.id" class="task-option">
        <input v-model="selected" type="checkbox" :value="task.id" />
        <span>
          <strong>{{ task.title || task.url }}</strong>
          <small>{{ task.platform || '待解析' }} · {{ statusLabels[task.status] }}</small>
        </span>
      </label>
      <p v-if="!tasks.length" class="muted hint">暂无匹配素材，先从下载工作台添加一个链接。</p>
    </div>
    <p v-if="error" class="error-text" role="alert">{{ error }}</p>
    <div class="modal-actions">
      <button type="button" class="button" :disabled="busy" @click="emit('close')">取消</button>
      <button class="button primary" :disabled="busy" @click="save">
        {{ busy ? '正在保存…' : '保存素材清单' }}
      </button>
    </div>
  </Modal>
</template>
<style scoped>
.hint {
  font-size: 12px;
  margin-bottom: 15px;
}
.selection-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin: 17px 0;
}
.task-options {
  max-height: 340px;
  overflow: auto;
}
.task-option {
  display: flex;
  align-items: center;
  gap: 14px;
  border-top: 1px solid var(--line);
  padding: 14px 5px;
  cursor: pointer;
}
.task-option input {
  margin: 0;
  flex-shrink: 0;
}
.task-option span {
  min-width: 0;
}
.task-option strong {
  display: block;
  font-size: 12px;
  overflow-wrap: anywhere;
}
.task-option small {
  display: block;
  color: var(--muted);
  font-size: 10px;
  margin-top: 5px;
}
</style>
