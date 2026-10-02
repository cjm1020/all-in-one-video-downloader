<script setup lang="ts">
import Icon from './Icon.vue'
defineProps<{ title: string }>()
const emit = defineEmits<{ close: [] }>()
</script>
<template><Teleport to="body"><div class="modal-overlay" @click.self="emit('close')" @keydown.esc="emit('close')"><section class="modal" role="dialog" aria-modal="true" :aria-label="title"><header class="modal-header"><h2>{{ title }}</h2><button class="icon-button" aria-label="关闭弹窗" @click="emit('close')"><Icon name="x" /></button></header><slot /></section></div></Teleport></template>
