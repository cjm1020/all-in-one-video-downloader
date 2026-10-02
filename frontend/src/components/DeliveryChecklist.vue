<script setup lang="ts">
import Icon from './Icon.vue'
import type { Checklist, ProjectItem } from '../studio'
defineProps<{ checklist: Checklist; items: ProjectItem[] }>()
const reasons: Record<string, string> = {
  not_completed: '素材下载尚未完成',
  missing_file: '媒体文件不可用',
  unknown_license: '尚未确认授权类型',
  license_unknown: '尚未确认授权类型',
  unverified: '授权尚未核验',
  rights_unverified: '授权尚未核验',
  missing_attribution: 'CC BY 需要署名',
  missing_evidence: '单独授权需要证据链接',
}
</script>
<template>
  <section class="delivery-checklist" :class="{ ready: checklist.ready }" aria-label="交付检查清单">
    <div class="checklist-title">
      <Icon :name="checklist.ready ? 'circlecheck' : 'shield'" :size="21" />
      <div>
        <h3>{{ checklist.ready ? '交付材料已准备好' : '交付前，再检查一下' }}</h3>
        <p>下载完成、媒体文件可用、授权核验通过后，可以打包并标记交付。</p>
      </div>
    </div>
    <div class="check-metrics">
      <div>
        <span>素材清单</span>
        <strong>{{ checklist.total }} 份</strong>
      </div>
      <div>
        <span>已完成下载</span>
        <strong>{{ checklist.completed }} / {{ checklist.total }}</strong>
      </div>
      <div>
        <span>授权已通过</span>
        <strong>{{ checklist.licensed }} / {{ checklist.total }}</strong>
      </div>
    </div>
    <div
      class="progress-track"
      role="progressbar"
      aria-label="素材准备进度"
      :aria-valuenow="
        checklist.total
          ? Math.round(((checklist.completed + checklist.licensed) / (checklist.total * 2)) * 100)
          : 0
      "
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <span
        :style="{
          width: `${checklist.total ? ((checklist.completed + checklist.licensed) / (checklist.total * 2)) * 100 : 0}%`,
        }"
      ></span>
    </div>
    <ul v-if="checklist.issues.length" class="checklist-issues">
      <li v-for="(issue, i) in checklist.issues" :key="`${issue.task_id}-${i}`">
        <Icon name="alert" :size="13" />
        <span>
          {{ items.find((t) => t.id === issue.task_id)?.title || (issue.task_id ? '项目素材' : '项目') }}：{{
            reasons[issue.reason] || issue.reason
          }}
        </span>
      </li>
    </ul>
    <p v-else-if="!checklist.total" class="muted empty">先将素材加入项目，再核验每一份授权。</p>
  </section>
</template>
<style scoped>
.delivery-checklist {
  background: #fbf8f1;
  border: 1px solid #eee5d3;
  border-radius: 12px;
  padding: 21px;
  margin-top: 22px;
}
.delivery-checklist.ready {
  background: #f3f7ee;
  border-color: #e1e9d7;
}
.checklist-title {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  color: #9a916e;
}
.ready .checklist-title {
  color: #6b865f;
}
.checklist-title h3 {
  font-size: 13px;
}
.checklist-title p {
  font-size: 10px;
  color: var(--muted);
  margin-top: 5px;
}
.check-metrics {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin: 20px 0 14px;
}
.check-metrics span {
  display: block;
  font-size: 10px;
  color: var(--muted);
}
.check-metrics strong {
  display: block;
  font-size: 15px;
  margin-top: 7px;
  font-weight: 550;
}
.checklist-issues {
  margin: 15px 0 0;
  padding: 0;
  list-style: none;
  max-height: 150px;
  overflow: auto;
}
.checklist-issues li {
  display: flex;
  gap: 8px;
  font-size: 11px;
  line-height: 1.8;
  color: #a28b6e;
  margin-top: 6px;
  overflow-wrap: anywhere;
}
.empty {
  font-size: 11px;
  margin-top: 15px;
}
</style>
