<script setup lang="ts">
/**
 * 独立应用中心 /apps。
 * URL 查询参数（q / category / view）与筛选状态双向同步，便于分享和刷新。
 * 数据来自后端：关键词搜索走 /search 接口（名称/副标题/简介/编码），
 * 分类筛选走仓库过滤，二者可组合。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { SearchIcon } from 'tdesign-icons-vue-next'
import PortalHeader from '@/components/PortalHeader.vue'
import AppCard from '@/components/AppCard.vue'
import CopyRight from '@/components/CopyRight.vue'
import { usePortalStore } from '@/services/portal/store.ts'
import { addFavorite, removeFavorite, searchApps, type PortalApp } from '@/services/portal/api.ts'
import { useAppLaunch } from '@/services/portal/useAppLaunch.ts'
import { isAuthenticated } from '@/services/auth/logto.ts'
import { MessagePlugin } from 'tdesign-vue-next'

const route = useRoute()
const router = useRouter()
const { state, loadCatalog, loadUserData, favoriteIds, upsertFavorite } = usePortalStore()
const { launch } = useAppLaunch()

const keyword = ref(String(route.query.q ?? ''))
const category = ref(String(route.query.category ?? 'all'))
const view = ref<'all' | 'favorites' | 'recent'>(
  ['all', 'favorites', 'recent'].includes(String(route.query.view)) ? String(route.query.view) as 'all' | 'favorites' | 'recent' : 'all',
)
const authenticated = ref(false)
const remoteResults = ref<PortalApp[] | null>(null)
const page = ref(1)
const pageSize = 12

// URL ←→ 状态：改动筛选条件时同步到地址栏，支持分享与刷新
watch([keyword, category, view], () => {
  const query: Record<string, string> = {}
  if (keyword.value.trim()) query.q = keyword.value.trim()
  if (category.value !== 'all') query.category = category.value
  if (view.value !== 'all') query.view = view.value
  void router.replace({ name: 'apps', query })
})

const source = computed(() => {
  if (remoteResults.value !== null) return remoteResults.value
  if (view.value === 'favorites') return state.favorites
  if (view.value === 'recent') return state.recent
  return state.apps
})

const filtered = computed(() => {
  let rows = source.value
  if (view.value === 'all' && category.value !== 'all') {
    rows = rows.filter((a) => a.categories.includes(category.value))
  }
  if (keyword.value && remoteResults.value === null) {
    const q = keyword.value.trim().toLowerCase()
    rows = rows.filter((a) => `${a.name} ${a.code} ${a.subtitle} ${a.description}`.toLowerCase().includes(q))
  }
  return rows
})

const paged = computed(() => filtered.value.slice(0, page.value * pageSize))
const hasMore = computed(() => paged.value.length < filtered.value.length)

onMounted(async () => {
  await loadCatalog()
  authenticated.value = await isAuthenticated().catch(() => false)
  if (authenticated.value) await loadUserData(true)
})

// 关键词搜索走后端接口（覆盖 code 等前端缓存可能不含的字段）
let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(keyword, (value) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!value.trim()) { remoteResults.value = null; return }
  searchTimer = setTimeout(async () => {
    try {
      const res = await searchApps(value.trim(), category.value === 'all' ? '' : category.value)
      remoteResults.value = res.items
    } catch {
      remoteResults.value = null  // 搜索失败回退本地过滤
    }
  }, 250)
})
watch(category, () => {
  if (remoteResults.value !== null && keyword.value.trim()) {
    void searchApps(keyword.value.trim(), category.value === 'all' ? '' : category.value)
      .then((res) => { remoteResults.value = res.items })
      .catch(() => { remoteResults.value = null })
  }
})

async function toggleFavorite(app: PortalApp): Promise<void> {
  if (!authenticated.value) { await MessagePlugin.warning('登录后即可收藏应用'); return }
  const has = favoriteIds.value.has(app.id)
  try {
    if (has) await removeFavorite(app.id)
    else await addFavorite(app.id)
    upsertFavorite(app, !has)
  } catch { await MessagePlugin.error('收藏操作失败，请重试') }
}

function open(app: PortalApp): void { void launch(app) }
function loadMore(): void { page.value += 1 }
function clearFilters(): void {
  keyword.value = ''
  category.value = 'all'
  view.value = 'all'
  remoteResults.value = null
}
</script>

<template>
  <PortalHeader />

  <main class="mx-auto max-w-6xl px-4 pb-16">
    <div class="flex items-center justify-between flex-wrap gap-3 mb-5">
      <div>
        <h1 class="text-[24px] font-bold">应用中心</h1>
        <p class="text-[13px] text-ink-3 mt-1">发现 Also 生态的全部应用与工具</p>
      </div>
      <t-input v-model="keyword" class="w-[260px]" placeholder="搜索名称、编码或功能" clearable>
        <template #prefix-icon><SearchIcon /></template>
      </t-input>
    </div>

    <t-tabs v-model="view" class="mb-4">
      <t-tab-panel value="all" label="全部应用" />
      <t-tab-panel value="favorites" label="我的收藏" />
      <t-tab-panel value="recent" label="最近使用" />
    </t-tabs>

    <div class="category-bar">
      <button
        v-for="cat in state.categories"
        :key="cat.code"
        type="button"
        class="category-chip"
        :class="{ 'category-chip--active': category === cat.code }"
        @click="category = cat.code"
      >
        {{ cat.name }}
      </button>
    </div>

    <div class="mt-4 text-[12px] text-ink-3">共 {{ filtered.length }} 个应用</div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-3">
      <AppCard
        v-for="app in paged"
        :key="app.id"
        :app="app"
        :favorited="favoriteIds.has(app.id)"
        @toggle-favorite="toggleFavorite"
        @launch="open"
      />
    </div>

    <div v-if="!filtered.length && !state.loading" class="text-center py-16 text-ink-3">
      没有找到匹配的应用。<t-link theme="primary" @click="clearFilters">清除筛选</t-link>
    </div>

    <div v-if="hasMore" class="flex justify-center mt-6">
      <t-button variant="outline" @click="loadMore">加载更多</t-button>
    </div>
  </main>

  <CopyRight />
</template>

<style scoped>
.category-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.category-chip {
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid var(--color-line);
  background: var(--color-surface);
  color: var(--color-ink-2);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.category-chip:hover { border-color: var(--color-brand); color: var(--color-brand); }
.category-chip--active {
  background: var(--color-brand);
  border-color: var(--color-brand);
  color: #fff;
}
</style>
