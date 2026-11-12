<script setup lang="ts">
/** 安全体检：本机明文上计算弱密码/复用/过期，不联网。 */
import { ref } from 'vue'
import { CheckCircleIcon } from 'tdesign-icons-vue-next'
import { health } from '@/services/safekeep/crypto.ts'
import type { PlainItem } from '@/services/safekeep/types.ts'

const props = defineProps<{ items: PlainItem[] }>()
const emit = defineEmits<{ close: [] }>()
const h = health(props.items)
const visible = ref(true)
</script>

<template>
  <t-dialog
    v-model:visible="visible"
    header="安全体检"
    width="600px"
    :footer="false"
    @close="emit('close')"
  >
    <p class="dlg-desc">全部在本机明文上计算，不会上传任何密码；不联网、不调用泄露检测接口。</p>

    <div class="metrics">
      <div class="metric"><div class="n text-brand">{{ h.score }}</div><div class="l">健康评分</div></div>
      <div class="metric"><div class="n">{{ h.total }}</div><div class="l">条目总数</div></div>
      <div class="metric"><div class="n" :class="h.weak ? 'text-warn' : ''">{{ h.weak }}</div><div class="l">弱密码</div></div>
      <div class="metric"><div class="n" :class="h.reused ? 'text-warn' : ''">{{ h.reused }}</div><div class="l">重复复用</div></div>
    </div>

    <template v-if="h.weakItems.length || h.reuseItems.length || h.oldItems.length">
      <div v-if="h.weakItems.length" class="side-title mt-3.5">短于 12 位</div>
      <div v-for="p in h.weakItems.slice(0, 12)" :key="'w-' + p.id" class="kv"><span>{{ p.title }}</span><span>密码过短</span></div>
      <div v-if="h.reuseItems.length" class="side-title mt-3.5">重复使用</div>
      <div v-for="p in h.reuseItems.slice(0, 12)" :key="'r-' + p.id" class="kv"><span>{{ p.title }}</span><span>与其他条目相同</span></div>
      <div v-if="h.oldItems.length" class="side-title mt-3.5">超过 180 天未更新</div>
      <div v-for="p in h.oldItems.slice(0, 12)" :key="'o-' + p.id" class="kv"><span>{{ p.title }}</span><span>建议定期更换</span></div>
    </template>
    <t-alert v-else theme="success" class="my-3">
      <template #message><CheckCircleIcon class="mr-1" /> 当前没有明显的弱密码、复用或长期未更新问题。</template>
    </t-alert>

    <t-alert theme="info" class="my-3">
      <template #message>本版本不含 HIBP 泄露检测（需要联网且用 k-anonymity 只发哈希前 5 位）。生产版可加，但仍应保持密码不出设备。</template>
    </t-alert>

    <div class="flex mt-5">
      <t-button theme="default" variant="outline" block @click="emit('close')">关闭</t-button>
    </div>
  </t-dialog>
</template>

<style scoped>
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}
.metric {
  background: var(--color-brand-softer);
  border-radius: 9px;
  padding: 11px 12px;
}
.metric .n {
  font-size: 21px;
  font-weight: 600;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}
.metric .l {
  font-size: 11.5px;
  color: var(--color-ink-2);
  margin-top: 2px;
}
</style>
