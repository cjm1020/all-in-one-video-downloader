<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Icon from './Icon.vue'
import { api, message, notify } from '../store'
interface DueCard {
  id: string
  task_id: string
  title: string
  question: string
  answer: string
  due_at: string
  repetitions: number
  interval_days: number
}
const props = defineProps<{ refreshKey: number }>()
const emit = defineEmits<{ select: [taskId: string] }>()
const cards = ref<DueCard[]>([]),
  open = ref(false),
  revealed = ref(false),
  busy = ref(false),
  error = ref(''),
  reviewed = ref(0)
const current = computed(() => cards.value[0])
function toggleReview() {
  open.value = !open.value
  if (open.value) load()
}
async function load() {
  error.value = ''
  try {
    cards.value = await api<DueCard[]>('/knowledge/cards/due')
  } catch (e) {
    error.value = message(e)
  }
}
async function review(rating: 'again' | 'good' | 'easy') {
  if (!current.value) return
  busy.value = true
  error.value = ''
  try {
    await api(`/knowledge/cards/${current.value.id}/review`, {
      method: 'POST',
      body: JSON.stringify({ rating }),
    })
    cards.value.shift()
    revealed.value = false
    reviewed.value++
    if (!cards.value.length) notify('今天的到期复习已完成')
  } catch (e) {
    error.value = message(e)
    await load()
  } finally {
    busy.value = false
  }
}
watch(() => props.refreshKey, load)
watch(
  () => current.value?.id,
  () => {
    revealed.value = false
  },
)
onMounted(load)
</script>
<template>
  <section class="panel card-review" aria-label="到期复习">
    <div class="review-heading">
      <span class="feature-icon lavender"><Icon name="book" :size="19" /></span>
      <div>
        <h2>给知识，一次温柔的回访</h2>
        <p>
          {{ cards.length ? `${cards.length} 张复习卡已到期` : '当前没有到期复习卡' }}
          <span v-if="reviewed">· 本次已复习 {{ reviewed }} 张</span>
        </p>
      </div>
      <button
        class="button small"
        @click="toggleReview"
      >
        {{ open ? '收起复习' : cards.length ? '开始复习' : '检查复习' }}
      </button>
    </div>
    <template v-if="open">
      <article v-if="current" class="review-card">
        <div class="review-source">
          <span class="badge lavender">第 {{ current.repetitions + 1 }} 次复习</span>
          <button class="text-link" @click="emit('select', current.task_id)">
            {{ current.title || '查看来源' }}
            <Icon name="right" :size="12" />
          </button>
        </div>
        <h3>{{ current.question }}</h3>
        <p v-if="revealed" class="review-answer">{{ current.answer }}</p>
        <button v-else class="button" @click="revealed = true">想好以后，查看答案</button>
        <div v-if="revealed" class="rating-buttons">
          <button class="button small" :disabled="busy" @click="review('again')">还没记住</button>
          <button class="button small primary" :disabled="busy" @click="review('good')">基本记住</button>
          <button class="button small" :disabled="busy" @click="review('easy')">轻松记住</button>
        </div>
        <p class="review-hint">根据回忆情况安排下次复习。先尝试作答，再对照参考答案。</p>
      </article>
      <p v-else class="empty-review">复习已完成。新建复习卡后，可以回到这里开始。</p>
    </template>
    <p v-if="error" class="error-text" role="alert">{{ error }}</p>
  </section>
</template>
<style scoped>
.card-review {
  margin-bottom: 23px;
  padding: 22px;
}
.review-heading {
  display: flex;
  gap: 13px;
  align-items: center;
}
.review-heading > div {
  flex: 1;
}
.review-heading h2 {
  font-size: 14px;
}
.review-heading p {
  font-size: 10px;
  color: var(--muted);
  margin-top: 5px;
}
.review-heading .button {
  white-space: nowrap;
}
.review-card {
  padding: 23px;
  background: #f7f4fb;
  border: 1px solid #e8e1f0;
  border-radius: 11px;
  margin-top: 21px;
}
.review-source {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.review-source .text-link {
  overflow-wrap: anywhere;
}
.review-card h3 {
  font-size: 16px;
  line-height: 1.8;
  margin: 20px 0;
  overflow-wrap: anywhere;
}
.review-answer {
  font-size: 12px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  padding: 17px;
  background: #fff;
  border-radius: 9px;
  margin-bottom: 18px;
}
.rating-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.review-hint,
.empty-review {
  font-size: 10px;
  color: var(--muted);
  margin-top: 20px;
}
.error-text {
  margin-top: 12px;
}
@media (max-width: 650px) {
  .card-review {
    padding: 17px;
  }
  .review-heading h2 {
    font-size: 12px;
  }
  .review-heading {
    flex-wrap: wrap;
  }
  .review-card {
    padding: 17px;
  }
  .review-card h3 {
    font-size: 14px;
  }
}
</style>
