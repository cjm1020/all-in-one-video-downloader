<script setup lang="ts">
import { ref } from 'vue'
import Icon from './Icon.vue'
import { message, notify } from '../store'
import type { ProjectDetail } from '../studio'
const props = defineProps<{ detail: ProjectDetail }>()
const downloading = ref('')
async function download(format: 'markdown' | 'json' | 'csv' | 'zip') {
  downloading.value = format
  const path = format === 'zip' ? 'package' : `export?format=${format}`
  try {
    const response = await fetch(`/api/studio/projects/${props.detail.project.id}/${path}`, { signal: AbortSignal.timeout(120000) })
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '导出失败，请重试' }))
      throw new Error(error.detail)
    }
    const blob = await response.blob()
    const url = URL.createObjectURL(blob), anchor = document.createElement('a')
    const extension = format === 'markdown' ? 'md' : format
    anchor.href = url; anchor.download = `${props.detail.project.name.replace(/[\\/:*?"<>|]/g, '_')}-交付.${extension}`
    anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
    notify(format === 'zip' ? '交付包已下载，包含媒体与授权清单' : '交付文档已导出')
  } catch (e) { notify(message(e), true) }
  finally { downloading.value = '' }
}
</script>
<template>
  <section class="delivery-exports" aria-label="交付导出">
    <div><h3><Icon name="file" :size="16" />交付资料</h3><p>文档记录来源与授权信息。ZIP 包会再次检查下载和授权状态。</p></div>
    <div class="export-buttons"><button v-for="format in (['markdown', 'csv', 'json'] as const)" :key="format" class="button small" :disabled="!!downloading" @click="download(format)">{{ format === 'markdown' ? '交付文档' : format.toUpperCase() }}</button><button class="button small primary" :disabled="!detail.checklist.ready || !!downloading" @click="download('zip')"><Icon :name="downloading === 'zip' ? 'loader' : 'download'" :class="{ spinner: downloading === 'zip' }" :size="14" />{{ downloading === 'zip' ? '正在打包…' : '下载交付 ZIP' }}</button></div>
    <p v-if="!detail.checklist.ready" class="export-hint">完成上方交付检查，即可下载包含媒体文件的 ZIP 包。</p>
  </section>
</template>
<style scoped>
.delivery-exports { padding: 20px; border: 1px solid var(--line); background: #fafbf7; border-radius: 10px; margin-top: 23px; }
h3 { display: flex; gap: 8px; align-items: center; font-size: 13px; }p { font-size: 10px; color: var(--muted); margin-top: 7px; }.export-buttons { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 17px; }.export-hint { margin-top: 14px; }
</style>
