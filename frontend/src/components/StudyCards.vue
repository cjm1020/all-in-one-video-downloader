<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import Icon from './Icon.vue'
import { api, message, notify } from '../store'
import type { TaskDetail } from '../types'
interface Card { id: string; task_id: string; question: string; answer: string; due_at: string; interval_days: number; repetitions: number }
const props = defineProps<{ task: TaskDetail }>()
const emit = defineEmits<{ changed: [] }>()
const cards = ref<Card[]>([]), busy = ref(''), error = ref(''), shown = ref<string[]>([]), expanded = ref(false)
const form = reactive({ question: '', answer: '' })
async function load() {
  const id = props.task.id
  try { const value = await api<Card[]>(`/knowledge/tasks/${id}/cards`); if (props.task.id === id) cards.value = value }
  catch (e) { error.value = message(e) }
}
async function create() {
  busy.value = 'create'; error.value = ''
  try {
    await api(`/knowledge/tasks/${props.task.id}/cards`, { method: 'POST', body: JSON.stringify(form) })
    form.question = ''; form.answer = ''; await load(); emit('changed'); notify('复习卡已保存')
  } catch (e) { error.value = message(e) }
  finally { busy.value = '' }
}
async function generate() {
  busy.value = 'generate'; error.value = ''
  try {
    const result = await api<{ added: Card[] }>(`/knowledge/tasks/${props.task.id}/cards/generate`, { method: 'POST' })
    await load(); expanded.value = true; emit('changed'); notify(`已从字幕原句提取 ${result.added.length} 张填空卡`)
  } catch (e) { error.value = message(e) }
  finally { busy.value = '' }
}
async function remove(card: Card) {
  busy.value = card.id
  try { await api(`/knowledge/cards/${card.id}`, { method: 'DELETE' }); await load(); emit('changed'); notify('复习卡已移除') }
  catch (e) { error.value = message(e) }
  finally { busy.value = '' }
}
function toggle(id: string) { shown.value = shown.value.includes(id) ? shown.value.filter(value => value !== id) : [...shown.value, id] }
watch(() => props.task.id, () => { cards.value = []; shown.value = []; form.question = ''; form.answer = ''; error.value = ''; load() })
onMounted(load)
</script>
<template>
  <section class="study-cards" aria-label="素材复习卡">
    <div class="panel-heading"><h3><Icon name="book" :size="16" />把观点，变成复习卡 <span class="section-caption">{{ cards.length }}</span></h3><button class="button small" :disabled="!!busy || !task.transcript" @click="generate"><Icon :name="busy === 'generate' ? 'loader' : 'leaf'" :size="13" :class="{ spinner: busy === 'generate' }" />本地提取填空卡</button></div><p class="hint">从字幕原句提取填空题，无需模型服务；也可以写下自己的问题与答案。</p>
    <form class="card-form" @submit.prevent="create"><label>复习问题<input v-model="form.question" required maxlength="1000" placeholder="这个片段解决了什么问题？" /></label><label>参考答案<textarea v-model="form.answer" required maxlength="5000" rows="3" placeholder="用自己的语言，写下关键结论…"></textarea></label><div class="card-form-action"><button class="button small" :disabled="!!busy || !form.question.trim() || !form.answer.trim()">{{ busy === 'create' ? '正在保存…' : '添加复习卡' }}</button></div></form>
    <button v-if="cards.length" class="text-link card-toggle" :aria-expanded="expanded" @click="expanded = !expanded">{{ expanded ? '收起' : '查看' }} {{ cards.length }} 张复习卡<Icon name="down" :size="12" /></button>
    <div v-if="expanded" class="card-list"><article v-for="card in cards" :key="card.id" class="study-card"><div class="card-header"><strong>{{ card.question }}</strong><button class="icon-button danger" :disabled="!!busy" :aria-label="`删除复习卡 ${card.question}`" @click="remove(card)"><Icon name="trash" :size="14" /></button></div><p v-if="shown.includes(card.id)" class="answer">{{ card.answer }}</p><div class="card-footer"><button class="text-link" @click="toggle(card.id)">{{ shown.includes(card.id) ? '隐藏答案' : '显示答案' }}</button><small>{{ card.repetitions }} 次复习 · 下次 {{ new Date(card.due_at).toLocaleDateString('zh-CN') }}</small></div></article></div>
    <div v-if="task.transcript" class="brief-export"><h4><Icon name="file" :size="15" />内容研究简报</h4><p>按本地字幕提取研究要点、原句与时间线索，便于项目评审。</p><a :href="`/api/knowledge/tasks/${task.id}/brief?format=markdown`" class="button small">导出研究简报</a><a :href="`/api/knowledge/tasks/${task.id}/brief?format=json`" class="text-link">JSON 数据</a></div>
    <p v-if="error" class="error-text" role="alert">{{ error }}</p>
  </section>
</template>
<style scoped>
.study-cards { margin-top: 25px; border-top: 1px solid var(--line); padding-top: 22px; }h3 { font-size: 13px; display: flex; align-items: center; gap: 8px; }.hint { font-size: 10px; color: var(--muted); margin: 12px 0 17px; }.card-form { padding: 17px; background: #f5f3f8; border-radius: 10px; }.card-form label { font-size: 10px; }.card-form label + label { margin-top: 14px; }.card-form-action { margin-top: 14px; display: flex; justify-content: end; }.card-toggle { margin-top: 18px; }.study-card { margin-top: 12px; padding: 17px; border: 1px solid #e8e1ef; background: #fcfbfe; border-radius: 10px; }.card-header { display: flex; gap: 10px; justify-content: space-between; }.card-header strong { font-size: 12px; font-weight: 500; overflow-wrap: anywhere; padding-top: 5px; }.answer { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 11px; color: var(--muted); margin-top: 13px; padding: 12px; background: #f1edf7; border-radius: 8px; }.card-footer { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 10px; align-items: center; margin-top: 12px; }.card-footer small { font-size: 9px; color: var(--muted); }.brief-export { margin-top: 22px; padding: 17px; background: #f8faf4; border-radius: 10px; }.brief-export h4 { display: flex; align-items: center; gap: 7px; font-size: 12px; }.brief-export p { font-size: 10px; color: var(--muted); margin: 8px 0 14px; }.brief-export > a { margin-right: 12px; }.error-text { margin-top: 12px; }
@media(max-width:650px) { .panel-heading { flex-wrap: wrap; }.card-form,.study-card { padding: 14px; } }
</style>
