<script setup lang="ts">
/** 应用卡片：门户首页 / 应用中心 / 启动器共用。卡片整体可点击，收藏按钮独立阻止冒泡。 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { StarIcon, StarFilledIcon, JumpIcon, LockOnIcon } from 'tdesign-icons-vue-next'
import type { PortalApp } from '@/services/portal/api.ts'

const props = withDefaults(defineProps<{
  app: PortalApp
  favorited?: boolean
  compact?: boolean
  showFavorite?: boolean
}>(), {
  favorited: false,
  compact: false,
  showFavorite: true,
})

const emit = defineEmits<{
  (e: 'toggle-favorite', app: PortalApp): void
  (e: 'launch', app: PortalApp): void
}>()

const router = useRouter()

const typeLabel = computed(() => ({
  application: '应用', tool: '工具', game: '游戏', service: '服务',
}[props.app.app_type] ?? '应用'))

const initial = computed(() => props.app.name.trim().charAt(0).toUpperCase() || 'A')

function open(): void {
  emit('launch', props.app)
}

function goDetail(): void {
  void router.push({ name: 'app-detail', params: { code: props.app.code } })
}
</script>

<template>
  <t-card :hoverable="true" class="app-card" :class="{ 'app-card--compact': compact }" @click="open">
    <div class="flex items-start gap-3">
      <!-- 图标：无图标 URL 时用名称首字母占位，避免破图 -->
      <div class="app-icon shrink-0">
        <img v-if="app.icon_url" :src="app.icon_url" :alt="app.name" class="w-full h-full object-cover" />
        <span v-else>{{ initial }}</span>
      </div>

      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-1.5 flex-wrap">
          <span class="text-[15px] font-semibold text-ink leading-tight truncate">{{ app.name }}</span>
          <t-tag v-if="app.is_new" size="small" theme="success" variant="light">新</t-tag>
          <t-tag v-if="app.is_featured" size="small" theme="primary" variant="light">推荐</t-tag>
          <LockOnIcon v-if="app.auth_required" size="14px" class="text-ink-3 shrink-0" />
        </div>
        <div v-if="app.subtitle && !compact" class="text-[12px] text-ink-3 mt-0.5 truncate">{{ app.subtitle }}</div>
        <p v-if="!compact" class="text-[12.5px] text-ink-2 leading-relaxed mt-2 line-clamp-2">{{ app.description }}</p>
        <div class="flex items-center gap-2 mt-2.5">
          <t-tag size="small" variant="outline">{{ typeLabel }}</t-tag>
          <t-link v-if="!compact" size="small" theme="primary" hover="color" @click.stop="goDetail">详情</t-link>
        </div>
      </div>

      <div class="flex flex-col items-center gap-1.5 shrink-0">
        <t-button
          v-if="showFavorite"
          size="small"
          variant="text"
          :theme="favorited ? 'warning' : 'default'"
          :title="favorited ? '取消收藏' : '收藏'"
          @click.stop="emit('toggle-favorite', app)"
        >
          <StarFilledIcon v-if="favorited" size="18px" />
          <StarIcon v-else size="18px" />
        </t-button>
        <t-button size="small" variant="text" title="打开应用" @click.stop="open">
          <JumpIcon size="18px" />
        </t-button>
      </div>
    </div>
  </t-card>
</template>

<style scoped>
.app-card {
  border-radius: 14px;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.app-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.08);
}
.app-card :deep(.t-card__body) {
  padding: 16px;
}
.app-card--compact :deep(.t-card__body) {
  padding: 12px;
}
.app-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-brand-soft);
  color: var(--color-brand);
  font-weight: 700;
  font-size: 18px;
  overflow: hidden;
}
.app-card--compact .app-icon {
  width: 36px;
  height: 36px;
  font-size: 15px;
  border-radius: 10px;
}
.line-clamp-2 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}
</style>
