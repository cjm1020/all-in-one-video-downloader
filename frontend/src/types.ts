export type Page = 'home' | 'queue' | 'library' | 'learning' | 'settings'
export type Preset = 'everyday' | 'archive' | 'commute' | 'audio'
export type TaskStatus =
  | 'queued'
  | 'downloading'
  | 'processing'
  | 'completed'
  | 'paused'
  | 'cancelled'
  | 'failed'
export interface Task {
  id: string
  url: string
  preset: Preset
  collection_id: string
  title: string
  platform: string
  duration: number
  thumbnail: string
  status: TaskStatus
  progress: number
  speed: number
  eta: number
  scheduled_at: string | null
  clip_start: number | null
  clip_end: number | null
  rate_limit: number
  file_size: number
  error: string
  favorite: boolean
  tags: string[]
  summary_mode: string
  created_at: string
  updated_at: string
  has_transcript?: boolean
  has_summary?: boolean
}
export interface TaskDetail extends Task {
  notes: string
  transcript: string
  summary: string
}
export interface Collection {
  id: string
  name: string
  color: string
  count: number
}
export interface Settings {
  default_preset: Preset
  rate_limit: number
  storage_limit_gb: number
}
export interface Status {
  worker_online: boolean
  engine_version: string
  ffmpeg_available: boolean
  ai_available: boolean
  cookies_configured: boolean
  storage_bytes: number
  disk_free_bytes: number
  total_tasks: number
  completed_tasks: number
  active_tasks: number
  favorite_tasks: number
}
export interface VideoInfo {
  title: string
  platform: string
  duration: number
  thumbnail: string
  uploader: string
  heights: number[]
  has_subtitles: boolean
  webpage_url: string
}
