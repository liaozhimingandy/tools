<script setup lang="ts">
/** 重新生成恢复码：生成 → 抄写 → 输入确认 → 才作废旧码。 */
import { onMounted, ref } from 'vue'
import { normCode } from '@/services/safekeep/crypto.ts'
import type { Account } from '@/services/safekeep/types.ts'

const props = defineProps<{ generate: () => Promise<{ code: string; recovery: Account['recovery'] }> }>()
const emit = defineEmits<{ close: []; commit: [recovery: Account['recovery']]; toast: [msg: string] }>()

const visible = ref(true)
const pending = ref<{ code: string; recovery: Account['recovery'] } | null>(null)
const confirm = ref('')

onMounted(async () => {
  try {
    pending.value = await props.generate()
  } catch (e) {
    emit('toast', '生成失败：' + (e as Error).message)
    emit('close')
  }
})

function submit(): void {
  if (!pending.value) return
  if (normCode(confirm.value) !== normCode(pending.value.code)) return emit('toast', '恢复码不匹配')
  emit('commit', pending.value.recovery)
}
</script>

<template>
  <t-dialog
    v-model:visible="visible"
    header="重新生成恢复码"
    width="500px"
    :footer="false"
    @close="emit('close')"
  >
    <p class="dlg-desc">旧恢复码在确认前仍然有效。请抄写新码并确认，确认后旧码立即作废。</p>
    <div v-if="pending" class="recovery">{{ pending.code }}</div>
    <label class="field-label">输入新恢复码以确认</label>
    <t-input v-model="confirm" class="code-input" placeholder="粘贴或输入新恢复码" autocomplete="off" :spellcheck="false" @enter="submit" />
    <div class="flex gap-2 mt-5">
      <t-button theme="primary" :disabled="!pending" class="flex-1" @click="submit">确认并作废旧码</t-button>
      <t-button theme="default" variant="outline" class="flex-1" @click="emit('close')">取消</t-button>
    </div>
  </t-dialog>
</template>

<style scoped>
.code-input :deep(.t-input__inner) {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  letter-spacing: 0.04em;
}
</style>
