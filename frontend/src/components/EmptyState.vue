<script setup lang="ts">
import Icon from './Icon.vue'
defineProps<{ icon?: string; title: string; description: string }>()
</script>
<template><div class="empty-state"><div class="empty-icon"><Icon :name="icon || 'leaf'" :size="30" /></div><h3>{{ title }}</h3><p>{{ description }}</p><slot /></div></template>
