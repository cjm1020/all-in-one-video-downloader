<script setup lang="ts">
import { reactive } from 'vue'
import Modal from './Modal.vue'
import { api, message, notify } from '../store'
import type { Project, ProjectInput } from '../studio'
import { ref } from 'vue'

const props = defineProps<{ project?: Project }>()
const emit = defineEmits<{ close: []; saved: [project: Project] }>()
const form = reactive({
  name: props.project?.name || '', client: props.project?.client || '',
  budget: (props.project?.budget_cents || 0) / 100,
  due: props.project?.due_at?.slice(0, 10) || '', notes: props.project?.notes || '',
})
const busy = ref(false), error = ref('')
async function save() {
  busy.value = true
  error.value = ''
  const payload: ProjectInput = {
    name: form.name.trim(), client: form.client.trim(), budget_cents: Math.round(form.budget * 100),
    due_at: form.due ? new Date(`${form.due}T23:59:59`).toISOString() : null, notes: form.notes.trim(),
  }
  try {
    const project = await api<Project>(props.project ? `/studio/projects/${props.project.id}` : '/studio/projects', {
      method: props.project ? 'PATCH' : 'POST', body: JSON.stringify(payload),
    })
    notify(props.project ? '项目资料已更新' : '新项目已创建')
    emit('saved', project)
  } catch (e) { error.value = message(e) }
  finally { busy.value = false }
}
</script>
<template>
  <Modal :title="project ? '编辑项目资料' : '创建交付项目'" @close="emit('close')">
    <form @submit.prevent="save">
      <label>项目名称<input v-model="form.name" required maxlength="120" placeholder="例如：秋季品牌故事素材" /></label>
      <div class="form-row">
        <label>客户 / 团队<input v-model="form.client" maxlength="120" placeholder="例如：设计团队" /></label>
        <label>项目预算（元）<input v-model.number="form.budget" type="number" min="0" max="10000000" step="0.01" required /></label>
      </div>
      <div class="form-row">
        <label>截止日期<input v-model="form.due" type="date" /></label>
      </div>
      <label class="notes">交付说明<textarea v-model="form.notes" maxlength="5000" rows="4" placeholder="记录素材用途、交付范围与客户要求…"></textarea></label>
      <p v-if="error" class="error-text" role="alert">{{ error }}</p>
      <div class="modal-actions">
        <button type="button" class="button" :disabled="busy" @click="emit('close')">取消</button>
        <button class="button primary" :disabled="busy || !form.name.trim()">{{ busy ? '正在保存…' : '保存项目' }}</button>
      </div>
    </form>
  </Modal>
</template>
<style scoped>
.notes { margin-top: 20px; }
.error-text { margin-top: 12px; }
@media(max-width:650px) { .form-row { flex-direction: column; align-items: stretch; } }
</style>
