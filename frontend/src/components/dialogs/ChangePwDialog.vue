<script setup lang="ts">
/** 修改主密码（含恢复码解锁后的强制改密）。 */
import { ref } from 'vue'

const props = defineProps<{ force: boolean }>()
const emit = defineEmits<{ close: []; save: [newPassword: string]; toast: [msg: string] }>()

const visible = ref(true)
const pw = ref('')
const pw2 = ref('')
const busy = ref(false)

function onClose(): void {
  if (!props.force) emit('close')
}
async function submit(): Promise<void> {
  if (pw.value.length < 10) return emit('toast', '至少 10 位')
  if (pw.value !== pw2.value) return emit('toast', '两次输入不一致')
  busy.value = true
  try {
    emit('save', pw.value)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <t-dialog
    v-model:visible="visible"
    :header="force ? '请设置新的主密码' : '修改主密码'"
    width="460px"
    :footer="false"
    :close-on-overlay-click="!force"
    :close-btn="!force"
    @close="onClose"
  >
    <p class="dlg-desc">
      {{ force
        ? '你刚用恢复码解锁，说明原主密码已遗忘，请立即设置一个新主密码。'
        : '只重新包裹密钥，所有条目密文原样不动，不会重加密，也不会影响恢复码。' }}
    </p>

    <div class="mb-3.5">
      <label class="field-label">新主密码（至少 10 位）</label>
      <t-input v-model="pw" type="password" autocomplete="new-password" placeholder="至少 10 位" />
    </div>
    <div class="mb-3.5">
      <label class="field-label">确认新主密码</label>
      <t-input v-model="pw2" type="password" autocomplete="new-password" placeholder="再次输入新主密码" @enter="submit" />
    </div>

    <div class="flex gap-2 mt-5">
      <t-button v-if="!force" theme="default" variant="outline" class="flex-1" @click="emit('close')">取消</t-button>
      <t-button theme="primary" :loading="busy" class="flex-1" @click="submit">保存新主密码</t-button>
    </div>
  </t-dialog>
</template>
