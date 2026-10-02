import { reactive } from 'vue'
import type { Collection, Page, Settings, Status, Task } from './types'

const pages: Page[] = ['home', 'queue', 'library', 'learning', 'settings']
const initial = location.hash.slice(1) as Page
export const store = reactive({
  page: pages.includes(initial) ? initial : ('home' as Page),
  tasks: [] as Task[],
  collections: [] as Collection[],
  settings: { default_preset: 'everyday', rate_limit: 0, storage_limit_gb: 10 } as Settings,
  status: null as Status | null,
  ready: false,
  connected: false,
  authRequired: false,
  error: '',
  toast: '',
  toastError: false,
  selectedLearning: '',
  mobileMenu: false,
})
let source: EventSource | null = null
let toastTimer: ReturnType<typeof setTimeout>
let healthTimer: ReturnType<typeof setInterval> | undefined

export function notify(message: string, error = false) {
  clearTimeout(toastTimer)
  store.toast = message
  store.toastError = error
  toastTimer = setTimeout(() => {
    store.toast = ''
  }, 5000)
}

export function navigate(page: Page) {
  store.page = page
  store.mobileMenu = false
  location.hash = page
}
window.addEventListener('hashchange', () => {
  const page = location.hash.slice(1) as Page
  if (pages.includes(page)) store.page = page
})

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch('/api' + path, {
    signal: AbortSignal.timeout(120000),
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `请求失败 (${response.status})` }))
    if (response.status === 401) {
      store.authRequired = true
      source?.close()
    }
    const detail = Array.isArray(body.detail)
      ? body.detail.map((e: { msg: string }) => e.msg).join('；')
      : body.detail
    throw new Error(detail || '请求失败，请稍后重试')
  }
  return response.json()
}

export async function refresh() {
  const [tasks, collections, status, settings] = await Promise.all([
    api<Task[]>('/tasks'),
    api<Collection[]>('/collections'),
    api<Status>('/status'),
    api<Settings>('/settings'),
  ])
  Object.assign(store, { tasks, collections, status, settings, ready: true, error: '' })
}

export async function initialize() {
  clearInterval(healthTimer)
  source?.close()
  store.connected = false
  try {
    const session = await api<{ authenticated: boolean }>('/session')
    store.authRequired = !session.authenticated
    if (store.authRequired) return
    await refresh()
    source?.close()
    source = new EventSource('/api/events')
    source.onopen = () => {
      store.connected = true
    }
    source.onerror = () => {
      store.connected = false
    }
    source.addEventListener('tasks', (event) => {
      store.tasks = JSON.parse((event as MessageEvent).data)
      api<Status>('/status')
        .then((value) => {
          store.status = value
        })
        .catch(() => {})
      api<Collection[]>('/collections')
        .then((value) => {
          store.collections = value
        })
        .catch(() => {})
    })
    healthTimer = setInterval(() => {
      if (!document.hidden && !store.authRequired) {
        api<Status>('/status')
          .then((value) => {
            store.status = value
          })
          .catch(() => {})
      }
    }, 15000)
  } catch (error) {
    store.error = message(error)
  }
}

export function message(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请重试'
}
export function bytes(value: number): string {
  if (!value) return '0 B'
  const unit = Math.min(3, Math.floor(Math.log(value) / Math.log(1024)))
  return `${(value / 1024 ** unit).toFixed(unit ? 1 : 0)} ${['B', 'KB', 'MB', 'GB'][unit]}`
}
export function duration(value: number): string {
  if (!value) return '时长未知'
  const seconds = Math.floor(value)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}
export function hostname(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return '视频链接'
  }
}
export const presets = [
  {
    id: 'everyday',
    title: '日常收藏',
    detail: '优先 720p · 清晰刚刚好',
    icon: 'video',
    color: 'sage',
    label: '720p',
  },
  {
    id: 'archive',
    title: '高清存档',
    detail: '优先 1080p · 留住每个细节',
    icon: 'sparkles',
    color: 'lavender',
    label: '1080p',
  },
  {
    id: 'commute',
    title: '轻量通勤',
    detail: '优先 480p · 小一点也很精彩',
    icon: 'leaf',
    color: 'peach',
    label: '480p',
  },
  {
    id: 'audio',
    title: '音频口袋',
    detail: 'MP3 192k · 好内容随身听',
    icon: 'headphones',
    color: 'sky',
    label: 'MP3',
  },
] as const
export const statusLabels: Record<string, string> = {
  queued: '等待下载',
  downloading: '下载中',
  processing: '处理中',
  completed: '已完成',
  paused: '已暂停',
  cancelled: '已取消',
  failed: '需要重试',
}
