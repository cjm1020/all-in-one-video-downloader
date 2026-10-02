<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import Icon from './Icon.vue'
import Modal from './Modal.vue'
import { api, message, notify, presets, refresh, store } from '../store'
import type { Preset, Task } from '../types'
import type { Project, Workflow } from '../studio'
const props = defineProps<{ projects: Project[] }>()
const emit = defineEmits<{ changed: [] }>()
const workflows = ref<Workflow[]>([]),
  chosen = ref<Workflow | null>(null),
  creating = ref(false)
const busy = ref(false),
  error = ref(''),
  urls = ref(''),
  projectId = ref(''),
  deleting = ref('')
const result = ref<{ added: Task[]; skipped: string[] } | null>(null)
const form = reactive({
  name: '',
  description: '',
  preset: 'everyday' as Preset,
  collection_id: 'inbox',
  tags: '',
  rate_limit: 0,
})
const availableProjects = computed(() => props.projects.filter((p) => p.status !== 'delivered'))
function newRecipe() {
  creating.value = true
  error.value = ''
}
async function load() {
  try {
    workflows.value = await api<Workflow[]>('/studio/workflows')
  } catch (e) {
    error.value = message(e)
  }
}
function choose(workflow: Workflow) {
  chosen.value = workflow
  error.value = ''
  result.value = null
  urls.value = ''
  projectId.value = ''
}
async function create() {
  busy.value = true
  error.value = ''
  try {
    const tags = form.tags
      .split(/[,，]/)
      .map((t) => t.trim())
      .filter(Boolean)
    if (tags.length > 12) throw new Error('最多保存 12 个标签，请精简后再试')
    await api('/studio/workflows', {
      method: 'POST',
      body: JSON.stringify({
        ...form,
        tags,
      }),
    })
    creating.value = false
    await load()
    notify('工作流配方已保存')
  } catch (e) {
    error.value = message(e)
  } finally {
    busy.value = false
  }
}
async function run() {
  if (!chosen.value) return
  busy.value = true
  error.value = ''
  result.value = null
  try {
    const links = urls.value.split(/\r?\n/).map((t) => t.trim()).filter(Boolean)
    if (links.length > 100) throw new Error('每次最多运行 100 个链接，请分批处理')
    const outcome = await api<{ added: Task[]; skipped: string[] }>(
      `/studio/workflows/${chosen.value.id}/run`,
      {
        method: 'POST',
        body: JSON.stringify({
          urls: links,
          project_id: projectId.value || null,
        }),
      },
    )
    result.value = outcome
    await refresh()
    emit('changed')
    notify(`已加入 ${outcome.added.length} 个任务，跳过 ${outcome.skipped.length} 个重复链接`)
  } catch (e) {
    error.value = message(e)
  } finally {
    busy.value = false
  }
}
async function remove(id: string) {
  busy.value = true
  try {
    await api(`/studio/workflows/${id}`, { method: 'DELETE' })
    deleting.value = ''
    await load()
    notify('自定义配方已移除')
  } catch (e) {
    error.value = message(e)
  } finally {
    busy.value = false
  }
}
onMounted(load)
</script>
<template>
  <section class="recipes panel">
    <div class="panel-heading">
      <h2>
        <Icon name="zap" :size="18" />
        让常用流程，一键出发
      </h2>
      <button
        class="button small"
        @click="newRecipe"
      >
        <Icon name="plus" :size="13" />
        自定义配方
      </button>
    </div>
    <p class="recipe-intro">将清晰度、收藏夹、标签与限速保存成配方，批量链接可以直接归入项目。</p>
    <p v-if="error && !chosen && !creating" class="error-text" role="alert">{{ error }}</p>
    <div class="recipe-grid">
      <article v-for="workflow in workflows" :key="workflow.id" class="recipe-card">
        <span class="feature-icon" :class="workflow.builtin ? 'lavender' : 'sage'">
          <Icon name="zap" :size="18" />
        </span>
        <div>
          <h3>{{ workflow.name }}</h3>
          <p>{{ workflow.description }}</p>
          <div class="tags">
            <span class="tag">{{ presets.find((p) => p.id === workflow.preset)?.title }}</span>
            <span v-for="tag in workflow.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
          <div class="recipe-actions">
            <button class="button small" @click="choose(workflow)">
              使用配方
              <Icon name="right" :size="13" />
            </button>
            <button
              v-if="!workflow.builtin"
              class="icon-button danger"
              :aria-label="`删除配方 ${workflow.name}`"
              @click="deleting = workflow.id"
            >
              <Icon name="trash" :size="14" />
            </button>
          </div>
          <div v-if="deleting === workflow.id" class="delete-recipe">
            <span>移除此配方？</span>
            <button class="text-link" :disabled="busy" @click="remove(workflow.id)">确认</button>
            <button class="text-link" @click="deleting = ''">取消</button>
          </div>
        </div>
      </article>
    </div>
  </section>
  <Modal v-if="creating" title="保存你的工作流配方" @close="creating = false">
    <form @submit.prevent="create">
      <label>
        配方名称
        <input v-model="form.name" maxlength="120" required placeholder="例如：客户音频简报" />
      </label>
      <label class="field">
        用途说明
        <textarea
          v-model="form.description"
          maxlength="2000"
          rows="2"
          placeholder="什么时候使用这份配方？"
        ></textarea>
      </label>
      <div class="form-row">
        <label>
          下载预设
          <select v-model="form.preset">
            <option v-for="preset in presets" :key="preset.id" :value="preset.id">
              {{ preset.title }} · {{ preset.label }}
            </option>
          </select>
        </label>
        <label>
          归入收藏夹
          <select v-model="form.collection_id">
            <option value="inbox">默认收藏</option>
            <option v-for="collection in store.collections" :key="collection.id" :value="collection.id">
              {{ collection.name }}
            </option>
          </select>
        </label>
      </div>
      <div class="form-row">
        <label>
          标签（用逗号分隔）
          <input v-model="form.tags" maxlength="500" placeholder="品牌素材, 客户交付" />
        </label>
        <label>
          下载限速（KB/s，0 为不限）
          <input v-model.number="form.rate_limit" type="number" min="0" max="100000" required />
        </label>
      </div>
      <p v-if="error" class="error-text" role="alert">{{ error }}</p>
      <div class="modal-actions">
        <button type="button" class="button" @click="creating = false">取消</button>
        <button class="button primary" :disabled="busy || !form.name.trim()">
          {{ busy ? '正在保存…' : '保存配方' }}
        </button>
      </div>
    </form>
  </Modal>
  <Modal v-if="chosen" :title="`使用配方：${chosen.name}`" @close="chosen = null">
    <form @submit.prevent="run">
      <p class="recipe-intro">
        {{ chosen.description }} · {{ presets.find((p) => p.id === chosen!.preset)?.title }}
      </p>
      <label>
        视频链接（每行一个）
        <textarea v-model="urls" rows="6" required maxlength="100000" placeholder="https://…"></textarea>
      </label>
      <p class="recipe-intro">每次最多 100 个链接；重复链接会跳过。</p>
      <label class="field">
        关联交付项目
        <select v-model="projectId">
          <option value="">只加入下载队列</option>
          <option v-for="project in availableProjects" :key="project.id" :value="project.id">
            {{ project.name }}
          </option>
        </select>
      </label>
      <p v-if="result" class="run-result" role="status">
        已加入 {{ result.added.length }} 个下载任务，跳过 {{ result.skipped.length }} 个重复链接。
        <span v-if="result.skipped.length">{{ result.skipped.join('\n') }}</span>
      </p>
      <p v-if="error" class="error-text" role="alert">{{ error }}</p>
      <div class="modal-actions">
        <button type="button" class="button" @click="chosen = null">关闭</button>
        <button class="button primary" :disabled="busy || !urls.trim()">
          {{ busy ? '正在加入队列…' : '运行配方' }}
        </button>
      </div>
    </form>
  </Modal>
</template>
<style scoped>
.recipes {
  margin-top: 25px;
  padding: 23px;
}
.recipe-intro {
  font-size: 11px;
  color: var(--muted);
  margin: 10px 0 20px;
}
.recipe-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.recipe-card {
  display: flex;
  gap: 12px;
  border: 1px solid var(--line);
  border-radius: 11px;
  padding: 17px;
}
.recipe-card > div {
  min-width: 0;
}
.recipe-card h3 {
  font-size: 12px;
}
.recipe-card p {
  font-size: 10px;
  color: var(--muted);
  margin: 7px 0 12px;
}
.recipe-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
}
.field {
  margin-top: 18px;
}
.delete-recipe {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 10px;
  margin-top: 10px;
}
.run-result {
  font-size: 12px;
  padding: 15px;
  background: var(--sage);
  border-radius: 8px;
  margin-top: 15px;
}
.run-result span {
  display: block;
  font-size: 10px;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  margin-top: 7px;
}
@media (max-width: 1100px) {
  .recipe-grid {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 650px) {
  .recipe-grid {
    grid-template-columns: 1fr;
  }
  .recipes {
    padding: 18px;
  }
  .recipes .panel-heading {
    align-items: start;
  }
  .recipes .panel-heading h2 {
    font-size: 12px;
  }
  .recipes .button {
    white-space: nowrap;
  }
  .form-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
