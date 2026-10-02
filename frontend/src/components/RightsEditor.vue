<script setup lang="ts">
import { reactive, ref } from 'vue'
import Modal from './Modal.vue'
import { api, message, notify } from '../store'
import type { ProjectItem, Rights } from '../studio'

const props = defineProps<{ item: ProjectItem }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const form = reactive<Rights>({ ...props.item.rights })
const busy = ref(false), error = ref('')
async function save() {
  busy.value = true
  error.value = ''
  try {
    await api(`/studio/rights/${props.item.id}`, { method: 'PUT', body: JSON.stringify(form) })
    notify('授权记录已保存')
    emit('saved')
  } catch (e) { error.value = message(e) }
  finally { busy.value = false }
}
</script>
<template>
  <Modal title="素材授权记录" @close="emit('close')">
    <p class="asset-name">{{ item.title || item.url }}</p>
    <form @submit.prevent="save">
      <label>授权类型<select v-model="form.license"><option value="unknown">尚未确认</option><option value="owned">自有作品</option><option value="cc0">CC0 / 公共领域</option><option value="cc-by">CC BY（需要署名）</option><option value="permission">已获单独授权</option></select></label>
      <label>署名文字<textarea v-model="form.attribution" :required="form.license === 'cc-by'" maxlength="2000" rows="3" placeholder="作者、作品名称、来源、许可证链接与修改说明"></textarea></label>
      <label>授权证据链接<input v-model="form.evidence_url" type="url" :required="form.license === 'permission'" maxlength="2000" placeholder="https://…" /></label>
      <label class="confirmation"><input v-model="form.verified" type="checkbox" :disabled="form.license === 'unknown'" /><span>我已核验授权适用于本项目用途</span></label>
      <p class="muted hint">CC BY 需要署名；单独授权需要证据链接。授权记录由项目负责人核验，用于交付追溯。</p>
      <p v-if="error" class="error-text" role="alert">{{ error }}</p>
      <div class="modal-actions"><button type="button" class="button" :disabled="busy" @click="emit('close')">取消</button><button class="button primary" :disabled="busy">{{ busy ? '正在保存…' : '保存授权' }}</button></div>
    </form>
  </Modal>
</template>
<style scoped>
.asset-name { font-size: 13px; font-weight: 500; margin-bottom: 20px; overflow-wrap: anywhere; }
label + label { margin-top: 17px; }
.confirmation { display: flex; align-items: center; gap: 10px; }
.confirmation input { margin: 0; }
.hint { font-size: 11px; margin-top: 15px; }
</style>
