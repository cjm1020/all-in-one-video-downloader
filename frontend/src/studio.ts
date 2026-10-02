import type { Preset, Task } from './types'

export interface Project {
  id: string
  name: string
  client: string
  budget_cents: number
  due_at: string | null
  notes: string
  status: 'draft' | 'active' | 'delivered'
  created_at: string
  updated_at: string
  item_count?: number
}
export interface ProjectInput {
  name: string
  client: string
  budget_cents: number
  due_at: string | null
  notes: string
}
export type License = 'unknown' | 'owned' | 'cc0' | 'cc-by' | 'permission'
export interface Rights {
  license: License
  attribution: string
  evidence_url: string
  verified: boolean
}
export interface ProjectItem extends Task { rights: Rights }
export interface Checklist {
  total: number
  completed: number
  licensed: number
  ready: boolean
  issues: { task_id: string; reason: string }[]
}
export interface ProjectDetail {
  project: Project
  items: ProjectItem[]
  checklist: Checklist
}
export interface Workflow {
  id: string
  name: string
  description: string
  preset: Preset
  collection_id: string
  tags: string[]
  rate_limit: number
  builtin?: boolean
}
export interface Analytics {
  projects: number
  active_projects: number
  delivered_projects: number
  budget_cents: number
  completed_media: number
  licensed_media: number
  storage_bytes: number
  download_minutes: number
  platforms: { name: string; count: number }[]
  activity: { id: string; action: string; entity_id: string; created_at: string }[]
}
export function currency(cents: number) {
  return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY', maximumFractionDigits: 2 }).format(cents / 100)
}
export function localDate(value: string | null) {
  if (!value) return '未设置截止日期'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('zh-CN')
}
export const projectStatus = { draft: '准备中', active: '进行中', delivered: '已交付' }
