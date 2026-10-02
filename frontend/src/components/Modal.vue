<script setup lang="ts">
import Icon from './Icon.vue'
import { onMounted, onUnmounted, ref } from 'vue'
defineProps<{ title: string }>()
const emit = defineEmits<{ close: [] }>()
const panel = ref<HTMLElement | null>(null)
const previousFocus = document.activeElement as HTMLElement | null
const previousOverflow = document.body.style.overflow
function focusable() {
  return Array.from(
    panel.value?.querySelectorAll<HTMLElement>(
      'button:not(:disabled), a[href], input:not(:disabled), textarea:not(:disabled), select:not(:disabled), [tabindex="0"]',
    ) || [],
  )
}
function keys(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
  }
  if (event.key === 'Tab') {
    const elements = focusable(),
      first = elements[0],
      last = elements[elements.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last?.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first?.focus()
    }
  }
}
onMounted(() => {
  document.body.style.overflow = 'hidden'
  focusable()[0]?.focus()
})
onUnmounted(() => {
  document.body.style.overflow = previousOverflow
  previousFocus?.focus()
})
</script>
<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="emit('close')" @keydown="keys">
      <section ref="panel" class="modal" role="dialog" aria-modal="true" :aria-label="title">
        <header class="modal-header">
          <h2>{{ title }}</h2>
          <button class="icon-button" aria-label="关闭弹窗" @click="emit('close')"><Icon name="x" /></button>
        </header>
        <slot />
      </section>
    </div>
  </Teleport>
</template>
