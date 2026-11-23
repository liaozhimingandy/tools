<script setup lang="ts">
/**
 * 应用切换器（Google Apps Launcher 风格）。
 * 数据来源：门户 store 缓存的收藏 / 最近 / 全部应用；搜索为本地过滤。
 * 点击应用 → 走统一 launch 流程（服务端二次校验）。
 */
import { computed, ref, watch } from 'vue'
import { AppIcon, SearchIcon, StarIcon, HistoryIcon } from 'tdesign-icons-vue-next'
import { usePortalStore } from '@/services/portal/store.ts'
import type { PortalApp } from '@/services/portal/api.ts'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'launch', app: PortalApp): void
}>()

const { state } = usePortalStore()
const keyword = ref('')
const tab = ref<'favorites' | 'recent' | 'all'>('all')

const filtered = computed(() => {
  const source = tab.value === 'favorites' ? state.favorites : tab.value === 'recent' ? state.recent : state.apps
  const q = keyword.value.trim().toLowerCase()
  if (!q) return source
  return source.filter((a) => `${a.name} ${a.code} ${a.subtitle}`.toLowerCase().includes(q))
})

watch(() => props.visible, (v) => { if (!v) keyword.value = '' })

function close(): void {
  emit('update:visible', false)
}
</script>

<template>
  <t-dialog
    :visible="visible"
    :header="false"
    :footer="false"
    width="min(760px, 92vw)"
    placement="center"
    :close-on-overlay-click="true"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="launcher">
      <div class="flex items-center gap-2 mb-3">
        <AppIcon size="20px" class="text-brand" />
        <span class="text-base font-semibold flex-1">应用切换器</span>
        <t-button size="small" variant="text" @click="close">关闭</t-button>
      </div>

      <t-input v-model="keyword" placeholder="搜索应用名称或编码" clearable>
        <template #prefix-icon><SearchIcon /></template>
      </t-input>

      <t-tabs v-model="tab" class="mt-3">
        <t-tab-panel value="all" label="全部应用" />
        <t-tab-panel value="favorites" label="常用" />
        <t-tab-panel value="recent" label="最近使用" />
      </t-tabs>

      <div class="grid grid-cols-3 sm:grid-cols-4 gap-2 mt-3 max-h-[46vh] overflow-auto">
        <button
          v-for="app in filtered"
          :key="app.id"
          type="button"
          class="launcher-item"
          @click="close(); emit('launch', app)"
        >
          <div class="launcher-icon">
            <img v-if="app.icon_url" :src="app.icon_url" :alt="app.name" />
            <span v-else>{{ app.name.charAt(0).toUpperCase() }}</span>
          </div>
          <span class="text-[12px] truncate w-full">{{ app.name }}</span>
        </button>
        <div v-if="!filtered.length" class="col-span-full text-center text-ink-3 py-8 text-sm">
          {{ tab === 'favorites' ? '还没有收藏应用，去应用中心点亮星标吧' : '没有匹配的应用' }}
        </div>
      </div>

      <div class="flex items-center gap-4 mt-3 pt-3 border-t border-line text-[12px] text-ink-3">
        <span class="flex items-center gap-1"><StarIcon size="13px" /> 收藏优先</span>
        <span class="flex items-center gap-1"><HistoryIcon size="13px" /> 最近 10 个</span>
      </div>
    </div>
  </t-dialog>
</template>

<style scoped>
.launcher { padding: 4px 2px; }
.launcher-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px 6px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  cursor: pointer;
  color: var(--color-ink);
  transition: background 0.15s ease, border-color 0.15s ease;
}
.launcher-item:hover {
  background: var(--color-brand-softer);
  border-color: var(--color-line);
}
.launcher-icon {
  width: 40px;
  height: 40px;
  border-radius: 11px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-brand-soft);
  color: var(--color-brand);
  font-weight: 700;
}
.launcher-icon img { width: 100%; height: 100%; object-fit: cover; }
</style>
