<script setup lang="ts">
/** 应用详情页 /apps/:code：图标/封面/介绍/分类/状态/登录要求 + 立即使用 + 收藏。 */
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { StarIcon, StarFilledIcon, LockOnIcon, ChevronLeftIcon, JumpIcon } from 'tdesign-icons-vue-next'
import PortalHeader from '@/components/PortalHeader.vue'
import CopyRight from '@/components/CopyRight.vue'
import { usePortalStore } from '@/services/portal/store.ts'
import {
  getApp, addFavorite, removeFavorite, PortalApiError,
  type PortalApp,
} from '@/services/portal/api.ts'
import { useAppLaunch } from '@/services/portal/useAppLaunch.ts'
import { isAuthenticated } from '@/services/auth/logto.ts'
import { MessagePlugin } from 'tdesign-vue-next'

const route = useRoute()
const code = String(route.params.code ?? '').toUpperCase()
const { state, loadCatalog, loadUserData, favoriteIds, upsertFavorite } = usePortalStore()
const { launch } = useAppLaunch()

const app = ref<PortalApp | null>(null)
const favorited = ref(false)
const loading = ref(true)
const error = ref('')
const authenticated = ref(false)

const typeLabel = computed(() => ({
  application: '应用', tool: '工具', game: '游戏', service: '服务',
}[app.value?.app_type ?? 'application']))

const categoryNames = computed(() => {
  if (!app.value) return []
  return app.value.categories
    .map((c) => state.categories.find((cat) => cat.code === c)?.name ?? c)
})

onMounted(async () => {
  authenticated.value = await isAuthenticated().catch(() => false)
  if (authenticated.value) await loadUserData(true)
  await loadCatalog()
  try {
    const detail = await getApp(code)
    app.value = detail
    favorited.value = detail.favorited || favoriteIds.value.has(detail.id)
  } catch (e) {
    error.value = e instanceof PortalApiError && e.status === 404
      ? '应用不存在、尚未发布或你没有访问权限'
      : '加载详情失败，请稍后重试'
  } finally {
    loading.value = false
  }
})

async function toggleFavorite(): Promise<void> {
  if (!app.value) return
  if (!authenticated.value) { await MessagePlugin.warning('登录后即可收藏应用'); return }
  try {
    if (favorited.value) await removeFavorite(app.value.id)
    else await addFavorite(app.value.id)
    favorited.value = !favorited.value
    upsertFavorite(app.value, favorited.value)
  } catch { await MessagePlugin.error('收藏操作失败，请重试') }
}

function open(): void { if (app.value) void launch(app.value) }
function back(): void { window.history.back() }
function formatTime(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString()  // 前端按浏览器本地时区展示
}
</script>

<template>
  <PortalHeader />

  <main class="mx-auto max-w-5xl px-4 pb-16">
    <t-button variant="text" size="small" class="mb-4" @click="back">
      <ChevronLeftIcon /> 返回
    </t-button>

    <t-loading :loading="loading" class="min-h-[300px]">
      <t-alert v-if="error" theme="warning"><template #message>{{ error }}</template></t-alert>

      <template v-if="app">
        <t-card class="detail-head">
          <div class="flex flex-col sm:flex-row gap-5">
            <div class="detail-icon">
              <img v-if="app.icon_url" :src="app.icon_url" :alt="app.name" />
              <span v-else>{{ app.name.charAt(0).toUpperCase() }}</span>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <h1 class="text-[26px] font-bold">{{ app.name }}</h1>
                <t-tag v-if="app.is_new" theme="success" variant="light" size="small">新</t-tag>
                <t-tag v-if="app.is_featured" theme="primary" variant="light" size="small">推荐</t-tag>
              </div>
              <p class="text-ink-2 mt-1">{{ app.subtitle }}</p>
              <div class="flex flex-wrap gap-2 mt-3">
                <t-tag variant="outline">{{ typeLabel }}</t-tag>
                <t-tag v-for="name in categoryNames" :key="name" variant="light">{{ name }}</t-tag>
                <t-tag v-if="app.auth_required" variant="light" theme="warning">
                  <LockOnIcon size="13px" /> 需要登录
                </t-tag>
              </div>
              <div class="flex gap-2 mt-5">
                <t-button theme="primary" size="large" :disabled="!app.launch_url" @click="open">
                  <JumpIcon /> 立即使用
                </t-button>
                <t-button variant="outline" size="large" @click="toggleFavorite">
                  <StarFilledIcon v-if="favorited" size="18px" />
                  <StarIcon v-else size="18px" />
                  {{ favorited ? '已收藏' : '收藏' }}
                </t-button>
              </div>
              <p v-if="!app.launch_url" class="text-[12px] text-ink-3 mt-2">该应用尚未开放访问地址</p>
            </div>
          </div>
        </t-card>

        <t-card v-if="app.cover_url" class="mt-4">
          <img :src="app.cover_url" :alt="`${app.name} 封面`" class="w-full rounded-lg object-cover max-h-[320px]" />
        </t-card>

        <t-card class="mt-4">
          <h2 class="text-[16px] font-semibold mb-3">应用介绍</h2>
          <p class="text-[14px] text-ink-2 leading-7 whitespace-pre-wrap">{{ app.detail || app.description }}</p>
        </t-card>

        <t-card class="mt-4">
          <h2 class="text-[16px] font-semibold mb-3">访问信息</h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-y-2 text-[13px]">
            <div><span class="text-ink-3">应用编码：</span><code>{{ app.code }}</code></div>
            <div><span class="text-ink-3">打开方式：</span>{{ app.open_mode === 'new_tab' ? '新标签页' : '当前页面' }}</div>
            <div><span class="text-ink-3">访问地址：</span><span class="break-all">{{ app.launch_url || '未配置' }}</span></div>
            <div><span class="text-ink-3">更新时间：</span>{{ formatTime(app.updated_at) }}</div>
          </div>
        </t-card>
      </template>
    </t-loading>
  </main>

  <CopyRight />
</template>

<style scoped>
.detail-head { border-radius: 16px; }
.detail-head :deep(.t-card__body) { padding: 28px; }
.detail-icon {
  width: 88px;
  height: 88px;
  border-radius: 20px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-brand-soft);
  color: var(--color-brand);
  font-size: 36px;
  font-weight: 700;
  flex-shrink: 0;
}
.detail-icon img { width: 100%; height: 100%; object-fit: cover; }
</style>
