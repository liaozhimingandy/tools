<script setup lang="ts">
/**
 * Also Apps 首页。
 * 所有应用数据来自后端 API（经 portal store 缓存），管理员新增应用后前端自动展示。
 * 登录用户优先看收藏/最近，未登录看推荐。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { SearchIcon, StarIcon, HistoryIcon, ArrowRightIcon } from 'tdesign-icons-vue-next'
import PortalHeader from '@/components/PortalHeader.vue'
import AppCard from '@/components/AppCard.vue'
import CopyRight from '@/components/CopyRight.vue'
import { usePortalStore } from '@/services/portal/store.ts'
import { addFavorite, removeFavorite } from '@/services/portal/api.ts'
import { useAppLaunch } from '@/services/portal/useAppLaunch.ts'
import { isAuthenticated } from '@/services/auth/logto.ts'
import { MessagePlugin } from 'tdesign-vue-next'
import type { PortalApp } from '@/services/portal/api.ts'

const router = useRouter()
const { state, loadCatalog, loadUserData, favoriteIds, upsertFavorite } = usePortalStore()
const { launch } = useAppLaunch()
const keyword = ref('')
const authenticated = ref(false)

const favorites = computed(() => state.favorites)
const recent = computed(() => state.recent)
const featured = computed(() => state.apps.filter((a) => a.is_featured))
const categorized = computed(() => state.categories
  .filter((c) => c.code !== 'all')
  .map((c) => ({ category: c, apps: state.apps.filter((a) => a.categories.includes(c.code)) }))
  .filter((g) => g.apps.length > 0))

onMounted(async () => {
  await loadCatalog()
  authenticated.value = await isAuthenticated().catch(() => false)
  if (authenticated.value) await loadUserData(true)
})

function search(): void {
  const q = keyword.value.trim()
  void router.push({ name: 'apps', query: q ? { q } : {} })
}

async function toggleFavorite(app: PortalApp): Promise<void> {
  if (!authenticated.value) {
    await MessagePlugin.warning('登录后即可收藏应用')
    return
  }
  const has = favoriteIds.value.has(app.id)
  try {
    if (has) await removeFavorite(app.id)
    else await addFavorite(app.id)
    upsertFavorite(app, !has)
  } catch {
    await MessagePlugin.error('收藏操作失败，请重试')
  }
}

function open(app: PortalApp): void { void launch(app) }
function goto(code: string): void { void router.push({ name: 'apps', query: { category: code } }) }
</script>

<template>
  <PortalHeader />

  <main class="mx-auto max-w-6xl px-4 pb-16">
    <!-- 欢迎区 -->
    <section class="hero">
      <div class="relative z-10">
        <h1 class="text-[28px] sm:text-[34px] font-bold tracking-tight">你好，欢迎来到 Also Apps</h1>
        <p class="mt-2 text-[14px] text-ink-2 max-w-xl">
          一个入口，找到 Also 生态的所有应用、工具与服务。收藏常用的，随时从这里出发。
        </p>
        <div class="mt-5 flex flex-col sm:flex-row gap-3 max-w-xl">
          <t-input v-model="keyword" placeholder="搜索应用名称、编码或功能..." clearable size="large" @enter="search">
            <template #prefix-icon><SearchIcon /></template>
          </t-input>
          <t-button theme="primary" size="large" @click="search">搜索应用</t-button>
        </div>
      </div>
    </section>

    <!-- API 失败提示 -->
    <t-alert v-if="state.error" theme="warning" class="mb-6">
      <template #message>{{ state.error }}。请确认后端服务可用后刷新页面。</template>
    </t-alert>

    <t-loading :loading="state.loading && !state.loaded" size="small" class="min-h-[200px]">
      <!-- 常用 / 最近（仅登录用户） -->
      <template v-if="authenticated && (favorites.length || recent.length)">
        <section v-if="favorites.length" class="mt-8">
          <div class="flex items-center justify-between mb-3">
            <h2 class="section-title"><StarIcon size="18px" class="text-amber" /> 常用应用</h2>
            <t-link theme="primary" @click="goto('all')">管理收藏 <ArrowRightIcon size="14px" /></t-link>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <AppCard v-for="app in favorites" :key="app.id" :app="app" :favorited="true" @toggle-favorite="toggleFavorite" @launch="open" />
          </div>
        </section>

        <section v-if="recent.length" class="mt-8">
          <h2 class="section-title mb-3"><HistoryIcon size="18px" class="text-ink-3" /> 最近使用</h2>
          <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            <AppCard v-for="app in recent" :key="app.id" :app="app" compact :show-favorite="false" @launch="open" />
          </div>
        </section>
      </template>

      <!-- 推荐应用（未登录或未收藏时展示） -->
      <section v-if="featured.length" class="mt-8">
        <h2 class="section-title mb-3">推荐应用</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <AppCard v-for="app in featured" :key="app.id" :app="app" :favorited="favoriteIds.has(app.id)" @toggle-favorite="toggleFavorite" @launch="open" />
        </div>
      </section>

      <!-- 按分类展示 -->
      <section v-for="group in categorized" :key="group.category.code" class="mt-8">
        <div class="flex items-center justify-between mb-3">
          <h2 class="section-title">{{ group.category.name }}</h2>
          <t-link theme="primary" size="small" @click="goto(group.category.code)">查看全部 <ArrowRightIcon size="14px" /></t-link>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <AppCard v-for="app in group.apps" :key="app.id" :app="app" :favorited="favoriteIds.has(app.id)" @toggle-favorite="toggleFavorite" @launch="open" />
        </div>
      </section>

      <div v-if="!state.apps.length && !state.loading" class="text-center py-16 text-ink-3">
        暂无已发布的应用，请在后台发布后刷新。
      </div>
    </t-loading>
  </main>

  <CopyRight />
</template>

<style scoped>
.hero {
  margin-top: 20px;
  padding: 36px 32px;
  border-radius: 18px;
  background: linear-gradient(120deg, var(--color-brand-softer), var(--color-brand-soft));
  border: 1px solid var(--color-line);
}
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 17px;
  font-weight: 600;
  color: var(--color-ink);
}
</style>
