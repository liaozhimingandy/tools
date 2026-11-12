<script setup lang="ts">
/** 密码生成器：拒绝采样、真实熵值展示，全部本机计算。 */
import { computed, ref, watch } from 'vue'
import { RefreshIcon, CopyIcon, AddIcon } from 'tdesign-icons-vue-next'
import { genPassword } from '@/services/safekeep/crypto.ts'
import type { GeneratedPassword } from '@/services/safekeep/types.ts'

const emit = defineEmits<{ close: []; copy: [text: string]; use: [value: string] }>()
const visible = ref(true)

const len = ref(20)
const phrase = ref(false)
const upper = ref(true)
const lower = ref(true)
const digits = ref(true)
const symbols = ref(true)
const exclude = ref(true)
const result = ref<GeneratedPassword>(genPassword({ length: 20, exclude: true }))

// 参数变化自动重算
watch([len, phrase, upper, lower, digits, symbols, exclude], () => regenerate())
function regenerate(): void {
  result.value = genPassword({
    length: phrase.value ? Math.max(3, Math.round(len.value / 4)) : len.value,
    phrase: phrase.value,
    upper: upper.value,
    lower: lower.value,
    digits: digits.value,
    symbols: symbols.value,
    exclude: exclude.value,
  })
}
const entropyHint = computed(() => {
  const r = result.value
  return (phrase.value ? '词表 ' + r.charset + ' 词 · ' : '字符集 ' + r.charset + ' 种 · ') + '约 ' + r.entropy + ' bit 熵' +
    (r.entropy < 60 ? '（偏低，建议提高长度或改用随机字符模式）' : '（≥60 bit，适合绝大多数场景）')
})
</script>

<template>
  <t-dialog
    v-model:visible="visible"
    header="密码生成器"
    width="600px"
    :footer="false"
    @close="emit('close')"
  >
    <p class="dlg-desc">全部在本机生成，用 crypto.getRandomValues 取随机字节并做拒绝采样，不发送任何数据。</p>

    <div class="flex items-center gap-3 flex-wrap my-3">
      <div class="flex items-center gap-2">
        <span class="text-[12px] text-ink-2 whitespace-nowrap">长度</span>
        <t-slider v-model="len" :min="8" :max="40" class="w-32" />
        <span class="mono text-[12px] w-6">{{ len }}</span>
      </div>
      <t-checkbox v-model="phrase">易记短语模式</t-checkbox>
    </div>
    <div class="flex items-center gap-3 flex-wrap my-3">
      <t-checkbox v-model="upper" :disabled="phrase">大写</t-checkbox>
      <t-checkbox v-model="lower" :disabled="phrase">小写</t-checkbox>
      <t-checkbox v-model="digits">数字</t-checkbox>
      <t-checkbox v-model="symbols" :disabled="phrase">符号</t-checkbox>
      <t-checkbox v-model="exclude" :disabled="phrase">排除易混淆字符</t-checkbox>
    </div>

    <div class="genout mono">{{ result.value }}</div>
    <p class="hint">{{ entropyHint }}</p>

    <div class="flex gap-2 mt-5">
      <t-button theme="primary" @click="regenerate"><template #icon><RefreshIcon /></template>重新生成</t-button>
      <t-button theme="default" variant="outline" @click="emit('copy', result.value)"><template #icon><CopyIcon /></template>复制</t-button>
      <t-button theme="default" variant="outline" @click="emit('use', result.value)"><template #icon><AddIcon /></template>用于新条目</t-button>
    </div>
  </t-dialog>
</template>

<style scoped>
.genout {
  font-size: 15px;
  background: var(--color-brand-softer);
  border: 1px solid var(--color-line);
  border-radius: 8px;
  padding: 11px 12px;
  word-break: break-all;
  min-height: 42px;
  margin: 12px 0;
  color: var(--color-ink);
}
</style>
