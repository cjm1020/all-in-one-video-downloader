<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import Icon from '../components/Icon.vue'
import EmptyState from '../components/EmptyState.vue'
import ProjectForm from '../components/ProjectForm.vue'
import ProjectItems from '../components/ProjectItems.vue'
import RightsEditor from '../components/RightsEditor.vue'
import DeliveryChecklist from '../components/DeliveryChecklist.vue'
import DeliveryExports from '../components/DeliveryExports.vue'
import WorkflowRecipes from '../components/WorkflowRecipes.vue'
import { api, bytes, message, notify, statusLabels, store } from '../store'
import { currency, localDate, projectStatus } from '../studio'
import type { Project, ProjectDetail, ProjectItem } from '../studio'

const projects = ref<Project[]>([]),
  selected = ref(''),
  detail = ref<ProjectDetail | null>(null)
const loading = ref(true),
  loadingDetail = ref(false),
  error = ref(''),
  busy = ref(false)
const formOpen = ref(false),
  editing = ref<Project | undefined>(),
  itemsOpen = ref(false),
  rights = ref<ProjectItem | null>(null),
  confirmingDelete = ref(false)
const search = ref('')
const filtered = computed(() =>
  projects.value.filter((p) => `${p.name} ${p.client}`.toLowerCase().includes(search.value.toLowerCase())),
)
async function loadProjects() {
  projects.value = await api<Project[]>('/studio/projects')
  if (selected.value && !projects.value.some((p) => p.id === selected.value)) selected.value = ''
  if (!selected.value && projects.value.length) selected.value = projects.value[0]!.id
}
async function loadDetail() {
  const id = selected.value
  if (!id) {
    detail.value = null
    return
  }
  loadingDetail.value = true
  try {
    const result = await api<ProjectDetail>(`/studio/projects/${id}`)
    if (selected.value === id) detail.value = result
  } catch (e) {
    notify(message(e), true)
  } finally {
    if (selected.value === id) loadingDetail.value = false
  }
}
async function reload() {
  error.value = ''
  try {
    await loadProjects()
    await loadDetail()
  } catch (e) {
    error.value = message(e)
  } finally {
    loading.value = false
  }
}
function select(id: string) {
  selected.value = id
  detail.value = null
  confirmingDelete.value = false
  loadDetail()
}
function create() {
  editing.value = undefined
  formOpen.value = true
}
async function saved(project: Project) {
  formOpen.value = false
  selected.value = project.id
  await reload()
}
async function changed() {
  itemsOpen.value = false
  rights.value = null
  await reload()
}
async function setStatus(status: Project['status']) {
  if (!detail.value) return
  busy.value = true
  try {
    await api(`/studio/projects/${detail.value.project.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    })
    await reload()
    notify(status === 'delivered' ? '项目已标记交付' : '项目状态已更新')
  } catch (e) {
    notify(message(e), true)
  } finally {
    busy.value = false
  }
}
async function remove() {
  if (!detail.value) return
  busy.value = true
  try {
    await api(`/studio/projects/${detail.value.project.id}`, { method: 'DELETE' })
    selected.value = ''
    detail.value = null
    confirmingDelete.value = false
    await reload()
    notify('项目已移除，媒体素材仍保留在收藏中')
  } catch (e) {
    notify(message(e), true)
  } finally {
    busy.value = false
  }
}
let refreshTimer: ReturnType<typeof setTimeout> | undefined
watch(
  () => store.tasks,
  () => {
    clearTimeout(refreshTimer)
    refreshTimer = setTimeout(() => {
      if (selected.value) loadDetail()
    }, 500)
  },
)
onMounted(reload)
onUnmounted(() => clearTimeout(refreshTimer))
</script>
<template>
  <div class="page-heading">
    <div>
      <div class="eyebrow">FROM COLLECTION TO DELIVERY</div>
      <h1>把灵感，交付成作品</h1>
      <p>管理客户项目、核验素材授权，让每一次交付有据可循。</p>
    </div>
    <button class="button primary" @click="create">
      <Icon name="plus" :size="16" />
      创建项目
    </button>
  </div>
  <div v-if="error" class="error-banner" role="alert">
    <span>{{ error }}</span>
    <button class="button small" @click="reload">重新加载</button>
  </div>
  <p v-if="loading" class="muted loading" role="status">正在整理项目…</p>
  <div v-else-if="projects.length" class="studio-layout">
    <aside class="panel project-list">
      <div class="panel-heading">
        <h2>
          <Icon name="folder" :size="17" />
          交付项目
        </h2>
        <span class="section-caption">{{ projects.length }}</span>
      </div>
      <label class="search-field">
        <span class="sr-only">搜索交付项目</span>
        <Icon name="search" :size="15" />
        <input v-model="search" placeholder="项目或客户名称…" />
      </label>
      <button
        v-for="project in filtered"
        :key="project.id"
        :class="['project-option', { active: selected === project.id }]"
        @click="select(project.id)"
      >
        <strong>{{ project.name }}</strong>
        <span>{{ project.client || '个人项目' }} · {{ project.item_count || 0 }} 份素材</span>
        <small>
          <span class="badge" :class="project.status === 'delivered' ? 'sage' : 'peach'">
            {{ projectStatus[project.status] }}
          </span>
          {{ currency(project.budget_cents) }}
        </small>
      </button>
      <p v-if="!filtered.length" class="muted loading">没有匹配的项目</p>
    </aside>
    <section class="panel project-content" :aria-busy="loadingDetail">
      <p v-if="!detail" class="muted loading" role="status">正在加载项目资料…</p>
      <template v-else>
        <div class="project-heading">
          <div>
            <span class="eyebrow">{{ detail.project.client || 'YOUR PROJECT' }}</span>
            <h2>{{ detail.project.name }}</h2>
            <p>{{ currency(detail.project.budget_cents) }} 预算 · {{ localDate(detail.project.due_at) }}</p>
          </div>
          <button
            class="button small"
            @click="
              editing = detail.project
              formOpen = true
            "
          >
            <Icon name="sliders" :size="14" />
            编辑资料
          </button>
        </div>
        <p v-if="detail.project.notes" class="project-notes">{{ detail.project.notes }}</p>
        <div class="project-toolbar">
          <span class="badge" :class="detail.project.status === 'delivered' ? 'sage' : 'lavender'">
            {{ projectStatus[detail.project.status] }}
          </span>
          <button
            v-if="detail.project.status === 'draft'"
            class="button small"
            :disabled="busy || loadingDetail"
            @click="setStatus('active')"
          >
            开始项目
          </button>
          <button
            v-if="detail.project.status === 'delivered'"
            class="button small"
            :disabled="busy || loadingDetail"
            @click="setStatus('active')"
          >
            重新打开项目
          </button>
          <button
            v-else
            class="button small primary"
            :disabled="!detail.checklist.ready || busy || loadingDetail"
            @click="setStatus('delivered')"
          >
            <Icon name="checks" :size="14" />
            标记已交付
          </button>
        </div>
        <DeliveryChecklist :checklist="detail.checklist" :items="detail.items" />
        <div class="panel-heading media-heading">
          <h2>
            项目素材
            <span class="section-caption">{{ detail.items.length }}</span>
          </h2>
          <button
            class="button small"
            :disabled="detail.project.status === 'delivered'"
            @click="itemsOpen = true"
          >
            <Icon name="plus" :size="14" />
            管理素材
          </button>
        </div>
        <EmptyState
          v-if="!detail.items.length"
          icon="library"
          title="把第一份素材放进项目"
          description="已完成和排队中的素材都可以加入。下载与授权检查会随项目更新。"
        />
        <article v-for="item in detail.items" :key="item.id" class="project-media">
          <span
            class="feature-icon"
            :class="item.rights.verified && item.rights.license !== 'unknown' ? 'sage' : 'peach'"
          >
            <Icon
              :name="item.rights.verified && item.rights.license !== 'unknown' ? 'shield' : 'video'"
              :size="18"
            />
          </span>
          <div>
            <strong>{{ item.title || item.url }}</strong>
            <small>
              {{ item.platform || '待解析' }} · {{ bytes(item.file_size) }} · {{ statusLabels[item.status] }}
            </small>
            <span class="rights-hint">
              {{
                item.rights.license === 'unknown'
                  ? '授权待确认'
                  : item.rights.verified
                    ? '授权已核验'
                    : '授权待核验'
              }}
            </span>
          </div>
          <button class="button small" @click="rights = item">授权记录</button>
        </article>
        <DeliveryExports :detail="detail" />
        <div class="project-remove">
          <button class="text-link" @click="confirmingDelete = !confirmingDelete">
            <Icon name="trash" :size="13" />
            移除项目
          </button>
          <div v-if="confirmingDelete" class="remove-confirm">
            <p>移除「{{ detail.project.name }}」的项目记录与关联？媒体文件仍保留。</p>
            <button class="button small" :disabled="busy" @click="confirmingDelete = false">取消</button>
            <button class="button small danger" :disabled="busy" @click="remove">确认移除</button>
          </div>
        </div>
      </template>
    </section>
  </div>
  <section v-else class="panel">
    <EmptyState
      icon="folder"
      title="你的第一份交付，从这里开始"
      description="为客户或团队创建一个项目，挑选素材、补齐授权记录，再导出交付资料。"
    >
      <button class="button small primary" @click="create">
        <Icon name="plus" :size="14" />
        创建第一个项目
      </button>
    </EmptyState>
  </section>
  <WorkflowRecipes :projects="projects" @changed="reload" />
  <ProjectForm v-if="formOpen" :project="editing" @close="formOpen = false" @saved="saved" />
  <ProjectItems
    v-if="itemsOpen && detail"
    :project-id="detail.project.id"
    :task-ids="detail.items.map((t) => t.id)"
    @close="itemsOpen = false"
    @saved="changed"
  />
  <RightsEditor v-if="rights" :item="rights" @close="rights = null" @saved="changed" />
</template>
<style scoped>
.studio-layout {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}
.project-list {
  padding: 20px 15px;
}
.project-list .search-field {
  margin: 18px 0 12px;
  display: block;
}
.project-option {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: 9px;
  padding: 15px 12px;
  margin: 4px 0;
}
.project-option.active {
  background: #eff5e9;
}
.project-option:hover {
  background: #f5f7f1;
}
.project-option strong {
  font-size: 12px;
  display: block;
  overflow-wrap: anywhere;
}
.project-option > span {
  display: block;
  font-size: 10px;
  color: var(--muted);
  margin-top: 7px;
}
.project-option small {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 10px;
  margin-top: 12px;
}
.project-content {
  padding: 25px;
  min-width: 0;
}
.project-heading {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 15px;
}
.project-heading h2 {
  font-size: 20px;
  margin-top: 8px;
  overflow-wrap: anywhere;
}
.project-heading p {
  font-size: 11px;
  margin-top: 9px;
  color: var(--muted);
}
.project-heading .button {
  white-space: nowrap;
}
.project-notes {
  padding: 15px;
  background: #f8f9f4;
  border-radius: 8px;
  white-space: pre-wrap;
  font-size: 11px;
  margin-top: 20px;
  overflow-wrap: anywhere;
}
.project-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-top: 20px;
}
.media-heading {
  margin-top: 25px;
}
.project-media {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px 0;
  border-bottom: 1px solid var(--line);
}
.project-media > div {
  flex: 1;
  min-width: 0;
}
.project-media strong {
  display: block;
  font-size: 12px;
  overflow-wrap: anywhere;
}
.project-media small {
  display: block;
  font-size: 10px;
  color: var(--muted);
  margin-top: 5px;
}
.rights-hint {
  font-size: 9px;
  color: #95a789;
  display: block;
  margin-top: 7px;
}
.project-media > .button {
  flex-shrink: 0;
}
.loading {
  font-size: 12px;
  padding: 25px 10px;
}
.project-remove {
  margin-top: 25px;
  border-top: 1px solid var(--line);
  padding-top: 20px;
}
.remove-confirm {
  margin-top: 15px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.remove-confirm p {
  flex: 1 1 100%;
  font-size: 11px;
}
@media (max-width: 1000px) {
  .studio-layout {
    grid-template-columns: 200px minmax(0, 1fr);
    gap: 15px;
  }
  .project-content {
    padding: 20px;
  }
}
@media (max-width: 760px) {
  .studio-layout {
    grid-template-columns: 1fr;
  }
  .project-list {
    max-height: 280px;
    overflow: auto;
  }
  .project-content {
    padding: 18px;
  }
  .project-heading h2 {
    font-size: 17px;
  }
  .project-media {
    flex-wrap: wrap;
  }
  .project-media .button {
    margin-left: 51px;
  }
}
</style>
