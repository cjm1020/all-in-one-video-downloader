<script setup lang="ts">
import { ref } from 'vue'
import Icon from './Icon.vue'
import { api, duration, message } from '../store'
interface Match {
  task_id: string
  title: string
  text: string
  start: number | null
  end: number | null
}
const emit = defineEmits<{ select: [taskId: string, position: number | null] }>()
const query = ref(''),
  results = ref<Match[]>([]),
  total = ref(0),
  searched = ref(false),
  busy = ref(false),
  error = ref('')
let generation = 0
function hideResults() {
  searched.value = false
  results.value = []
}
async function search() {
  const id = ++generation
  busy.value = true
  error.value = ''
  try {
    const value = await api<{ results: Match[]; total: number }>(
      `/knowledge/search?q=${encodeURIComponent(query.value.trim())}&limit=20`,
    )
    if (generation === id) {
      results.value = value.results
      total.value = value.total
      searched.value = true
    }
  } catch (e) {
    if (generation === id) error.value = message(e)
  } finally {
    if (generation === id) busy.value = false
  }
}
</script>
<template>
  <section class="panel knowledge-search" aria-label="字幕资料库搜索">
    <div class="search-intro">
      <span class="feature-icon sky"><Icon name="search" :size="19" /></span>
      <div>
        <h2>从整个字幕库，找回那句话</h2>
        <p>搜索已导入的字幕，带时间戳的结果可以定位到原片段。</p>
      </div>
    </div>
    <form class="search-form" @submit.prevent="search">
      <label class="search-field">
        <span class="sr-only">搜索所有字幕</span>
        <Icon name="search" :size="15" />
        <input v-model="query" required minlength="1" maxlength="100" placeholder="搜索观点、术语或一句话…" />
      </label>
      <button class="button primary small" :disabled="busy || !query.trim()">
        {{ busy ? '正在查找…' : '搜索字幕' }}
      </button>
    </form>
    <p v-if="error" class="error-text" role="alert">{{ error }}</p>
    <div v-if="searched" class="search-results">
      <div class="results-heading">
        <span role="status">
          {{
            total
              ? `找到 ${total} 处相关片段${total > 20 ? '，显示前 20 处' : ''}`
              : '没有找到匹配字幕，试试其他词语。'
          }}
        </span>
        <button
          class="text-link"
          @click="hideResults"
        >
          收起结果
        </button>
      </div>
      <button
        v-for="(match, i) in results"
        :key="`${match.task_id}-${i}`"
        class="search-match"
        @click="emit('select', match.task_id, match.start)"
      >
        <div>
          <strong>{{ match.title }}</strong>
          <span v-if="match.start !== null" class="badge sky">
            {{ match.start ? duration(match.start) : '0:00' }}
            <template v-if="match.end !== null">– {{ duration(match.end) }}</template>
          </span>
          <span v-else class="badge">文本字幕</span>
        </div>
        <p>{{ match.text }}</p>
        <span class="text-link">
          打开学习资料
          <Icon name="right" :size="12" />
        </span>
      </button>
    </div>
  </section>
</template>
<style scoped>
.knowledge-search {
  padding: 22px;
  margin-bottom: 23px;
}
.search-intro {
  display: flex;
  gap: 13px;
  align-items: center;
}
.search-intro h2 {
  font-size: 14px;
}
.search-intro p {
  font-size: 10px;
  color: var(--muted);
  margin-top: 5px;
}
.search-form {
  display: flex;
  gap: 10px;
  margin-top: 19px;
}
.search-field {
  flex: 1;
}
.search-results {
  margin-top: 20px;
}
.results-heading {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  font-size: 10px;
  color: var(--muted);
  margin-bottom: 12px;
}
.search-match {
  display: block;
  width: 100%;
  padding: 17px;
  text-align: left;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: #fcfdf9;
  margin-top: 9px;
}
.search-match:hover {
  background: #f0f5e9;
}
.search-match > div {
  display: flex;
  gap: 10px;
  align-items: center;
}
.search-match strong {
  font-size: 12px;
  overflow-wrap: anywhere;
}
.search-match p {
  font-size: 11px;
  margin: 10px 0;
  color: var(--muted);
  overflow-wrap: anywhere;
}
.error-text {
  margin-top: 12px;
}
@media (max-width: 650px) {
  .knowledge-search {
    padding: 17px;
  }
  .search-form {
    flex-wrap: wrap;
  }
  .search-field {
    flex-basis: 100%;
  }
  .search-match > div {
    flex-wrap: wrap;
  }
  .search-intro h2 {
    font-size: 12px;
  }
}
</style>
