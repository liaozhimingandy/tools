/**
 * 门户轻量状态（模块级 reactive 单例，工程无 Pinia 依赖，不擅自新增）。
 *
 * 职责：缓存分类/应用列表/收藏/最近访问，供首页、应用中心、启动器共享，
 * 避免每个组件重复请求。身份态仍以 services/auth/logto.ts 为唯一来源。
 */

import { computed, reactive } from 'vue'
import {
  listApps,
  listCategories,
  listFavorites,
  listRecent,
  type PortalApp,
  type PortalCategory,
  PortalApiError,
} from './api.ts'

interface PortalState {
  categories: PortalCategory[]
  apps: PortalApp[]
  favorites: PortalApp[]
  recent: PortalApp[]
  loading: boolean
  error: string
  loaded: boolean
}

const state = reactive<PortalState>({
  categories: [],
  apps: [],
  favorites: [],
  recent: [],
  loading: false,
  error: '',
  loaded: false,
})

export function usePortalStore() {
  const appsByCategory = computed(() => (code: string): PortalApp[] => {
    if (code === 'all') return state.apps
    return state.apps.filter((a) => a.categories.includes(code))
  })

  const favoriteIds = computed(() => new Set(state.favorites.map((a) => a.id)))

  /** 加载公开目录（分类 + 已发布应用）；失败时降级为空列表并保留错误文案。 */
  async function loadCatalog(): Promise<void> {
    if (state.loading) return
    state.loading = true
    state.error = ''
    const results = await Promise.allSettled([
      listCategories(),
      listApps({ page: 1, pageSize: 100 }),
    ])
    if (results[0].status === 'fulfilled') {
      state.categories = results[0].value.items
    }
    if (results[1].status === 'fulfilled') {
      state.apps = results[1].value.items
      state.loaded = true
    }
    const failed = results.find((r) => r.status === 'rejected')
    if (failed?.status === 'rejected') {
      const reason = failed.reason
      state.error = reason instanceof PortalApiError ? reason.message : '加载应用目录失败'
    }
    state.loading = false
  }

  /** 登录后加载用户态数据；未登录时静默跳过，不产生错误提示。 */
  async function loadUserData(authenticated: boolean): Promise<void> {
    if (!authenticated) {
      state.favorites = []
      state.recent = []
      return
    }
    const [favs, recents] = await Promise.allSettled([listFavorites(), listRecent(10)])
    if (favs.status === 'fulfilled') state.favorites = favs.value.items
    if (recents.status === 'fulfilled') state.recent = recents.value.items
  }

  function upsertFavorite(app: PortalApp, added: boolean): void {
    if (added) {
      if (!state.favorites.some((f) => f.id === app.id)) state.favorites.push(app)
    } else {
      state.favorites = state.favorites.filter((f) => f.id !== app.id)
    }
  }

  function touchRecent(app: PortalApp): void {
    state.recent = [
      { ...app, last_visited_at: new Date().toISOString(), visit_count: (app.visit_count ?? 0) + 1 },
      ...state.recent.filter((r) => r.id !== app.id),
    ].slice(0, 10)
  }

  return {
    state,
    appsByCategory,
    favoriteIds,
    loadCatalog,
    loadUserData,
    upsertFavorite,
    touchRecent,
  }
}

/** 供非 Vue 上下文（测试/工具函数）读取当前快照。 */
export function portalSnapshot(): Readonly<PortalState> {
  return state
}
