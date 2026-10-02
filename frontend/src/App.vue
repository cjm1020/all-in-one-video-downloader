<script setup lang="ts">
import { defineAsyncComponent, onMounted, ref } from 'vue'
import Icon from './components/Icon.vue'
import { api, bytes, initialize, message, navigate, store } from './store'
import type { Page } from './types'

const views = {
  home: defineAsyncComponent(() => import('./views/HomeView.vue')),
  queue: defineAsyncComponent(() => import('./views/QueueView.vue')),
  library: defineAsyncComponent(() => import('./views/LibraryView.vue')),
  learning: defineAsyncComponent(() => import('./views/LearningView.vue')),
  studio: defineAsyncComponent(() => import('./views/StudioView.vue')),
  insights: defineAsyncComponent(() => import('./views/InsightsView.vue')),
  settings: defineAsyncComponent(() => import('./views/SettingsView.vue')),
}
const navigation: { id: Page; icon: string; title: string; caption: string }[] = [
  { id: 'home', icon: 'download', title: '下载工作台', caption: '从一个链接开始' },
  { id: 'queue', icon: 'queue', title: '下载队列', caption: '让精彩慢慢抵达' },
  { id: 'library', icon: 'library', title: '媒体收藏', caption: '喜欢的，都在这里' },
  { id: 'learning', icon: 'book', title: '学习花园', caption: '把内容变成收获' },
  { id: 'studio', icon: 'folder', title: '创作交付', caption: '把灵感变成作品' },
  { id: 'insights', icon: 'sparkles', title: '经营洞察', caption: '看见积累的价值' },
  { id: 'settings', icon: 'sliders', title: '偏好设置', caption: '按你的节奏来' },
]
const token = ref(''),
  loginError = ref(''),
  loggingIn = ref(false)
async function login() {
  loggingIn.value = true
  loginError.value = ''
  try {
    await api('/session', { method: 'POST', body: JSON.stringify({ token: token.value }) })
    token.value = ''
    await initialize()
  } catch (e) {
    loginError.value = message(e)
  } finally {
    loggingIn.value = false
  }
}
onMounted(initialize)
</script>
<template>
  <div class="app-shell">
    <button
      v-if="store.mobileMenu"
      class="sidebar-scrim"
      aria-label="关闭导航"
      @click="store.mobileMenu = false"
    ></button>
    <aside class="sidebar" :class="{ open: store.mobileMenu }">
      <a href="#home" class="brand" @click.prevent="navigate('home')">
        <span class="brand-mark"><Icon name="download" :size="23" /></span>
        <span>
          All-in-One
          <span class="brand-sub">VIDEO DOWNLOADER</span>
        </span>
      </a>
      <div class="sidebar-label">你的小小收藏室</div>
      <nav aria-label="主导航">
        <button
          v-for="item in navigation"
          :key="item.id"
          :class="['nav-item', { active: store.page === item.id }]"
          :aria-current="store.page === item.id ? 'page' : undefined"
          @click="navigate(item.id)"
        >
          <Icon :name="item.icon" :size="21" />
          <span>{{ item.title }}</span>
          <span v-if="item.id === 'queue' && store.status?.active_tasks" class="nav-count">
            {{ store.status.active_tasks }}
          </span>
        </button>
      </nav>
      <div class="sidebar-note">
        <div class="note-leaf"><Icon name="leaf" :size="24" /></div>
        <h4>留住喜欢，轻装前行</h4>
        <p>
          一段视频，一点灵感。
          <br />
          让值得收藏的内容陪伴你。
        </p>
        <span class="tiny-pill">MADE FOR YOUR LITTLE MOMENTS</span>
      </div>
      <div class="sidebar-bottom">
        <span class="avatar"><Icon name="sun" :size="18" /></span>
        <div>
          <strong>个人工作空间</strong>
          <small>SELF-HOSTED · v1.1</small>
        </div>
        <span class="online-dot" :class="{ offline: !store.status?.worker_online }"></span>
      </div>
    </aside>
    <main class="main-shell">
      <header class="topbar">
        <div class="breadcrumb">
          <button
            class="icon-button mobile-toggle"
            aria-label="打开导航"
            @click="store.mobileMenu = !store.mobileMenu"
          >
            <Icon name="menu" />
          </button>
          <span>我的空间</span>
          <Icon name="right" :size="14" />
          <strong>{{ navigation.find((n) => n.id === store.page)?.title }}</strong>
        </div>
        <div class="topbar-right">
          <span class="local-badge">
            <span class="online-dot" :class="{ offline: !store.status?.worker_online }"></span>
            {{ store.status?.worker_online ? '本地服务运行中' : '等待服务连接' }}
          </span>
          <a
            class="icon-button"
            href="https://github.com/cjm1020/all-in-one-video-downloader"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub 项目仓库"
          >
            <Icon name="github" :size="19" />
          </a>
        </div>
      </header>
      <div v-if="store.authRequired" class="auth-wrap">
        <form class="panel auth-card" @submit.prevent="login">
          <span class="feature-icon sage"><Icon name="shield" :size="28" /></span>
          <h1>欢迎回到收藏室</h1>
          <p class="muted">输入部署时设置的访问口令，继续你的收藏。</p>
          <label>
            访问口令
            <input
              v-model="token"
              type="password"
              autocomplete="current-password"
              required
              placeholder="你的 ACCESS_TOKEN"
            />
          </label>
          <p v-if="loginError" class="error-text" role="alert">{{ loginError }}</p>
          <button class="button primary" :disabled="loggingIn">
            {{ loggingIn ? '正在进入…' : '进入工作空间' }}
            <Icon name="right" :size="18" />
          </button>
        </form>
      </div>
      <div v-else class="workspace">
        <div v-if="store.error" class="error-banner" role="alert">
          <Icon name="alert" />
          <span>{{ store.error }}</span>
          <button class="button small" @click="initialize">重新连接</button>
        </div>
        <component :is="views[store.page]" />
        <footer class="page-footer">
          <span>
            <Icon name="leaf" :size="13" />
            把喜欢的片刻，留在身边。
          </span>
          <span v-if="store.status">
            已收藏 {{ store.status.completed_tasks }} 个片刻 · {{ bytes(store.status.storage_bytes) }}
          </span>
        </footer>
      </div>
    </main>
    <Transition name="toast">
      <div v-if="store.toast" class="toast-message" :class="{ error: store.toastError }" role="status">
        <Icon :name="store.toastError ? 'alert' : 'circlecheck'" :size="19" />
        {{ store.toast }}
        <button class="icon-button" aria-label="关闭提示" @click="store.toast = ''">
          <Icon name="x" :size="16" />
        </button>
      </div>
    </Transition>
  </div>
</template>
