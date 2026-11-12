<script setup lang="ts">
/** 设置：空闲锁定、后台锁定、剪贴板秒数 + 危险操作入口。 */
import { reactive, ref } from 'vue'
import { SettingIcon, LockOnIcon, RefreshIcon, DeleteIcon } from 'tdesign-icons-vue-next'
import type { Prefs } from '@/services/safekeep/types.ts'
import type { Account } from '@/services/safekeep/types.ts'

const props = defineProps<{ prefs: Prefs; account: Account | null }>()
const emit = defineEmits<{
  close: []
  save: [p: Prefs]
  changePw: []
  newRecovery: []
  wipe: []
}>()

const visible = ref(true)
const idleOptions: Array<[number, string]> = [
  [0, '关闭（不推荐）'], [60000, '1 分钟'], [300000, '5 分钟'], [900000, '15 分钟'], [1800000, '30 分钟'],
]
const form = reactive({
  idleMs: props.prefs.idleMs,
  hideLock: props.prefs.hideLock,
  clipSec: props.prefs.clipSec,
})
function fmtTime(ts: number | null): string {
  return ts ? new Date(ts).toLocaleString('zh-CN') : '从未'
}
function save(): void {
  emit('save', { idleMs: Number(form.idleMs) || 0, hideLock: !!form.hideLock, clipSec: Math.max(5, Math.min(120, Number(form.clipSec) || 15)) })
}
</script>

<template>
  <t-dialog
    v-model:visible="visible"
    header="设置"
    width="500px"
    :footer="false"
    @close="emit('close')"
  >
    <p class="dlg-desc">这些偏好不是敏感数据，明文保存在本地；保险库内容始终加密。</p>

    <label class="field-label">空闲自动锁定</label>
    <t-select v-model="form.idleMs" class="mb-3.5">
      <t-option v-for="[v, label] in idleOptions" :key="v" :value="v" :label="label" />
    </t-select>
    <div class="flex items-center gap-2 mb-3.5">
      <t-switch v-model="form.hideLock" />
      <span class="text-[12.5px] text-ink-2">切到后台立即锁定</span>
    </div>
    <label class="field-label">剪贴板自动清除（秒）</label>
    <t-input-number v-model="form.clipSec" :min="5" :max="120" theme="normal" class="w-full mb-4" />

    <t-divider />
    <div class="kv"><span>加密方式</span><span>AES-256-GCM · PBKDF2-SHA256 600k</span></div>
    <div class="kv"><span>保险库创建</span><span>{{ fmtTime(account?.createdAt ?? null) }}</span></div>
    <div class="kv"><span>上次导出备份</span><span>{{ fmtTime(account?.lastBackupAt ?? null) }}</span></div>

    <div class="flex gap-2 mt-5 flex-wrap">
      <t-button theme="primary" @click="save"><template #icon><SettingIcon /></template>保存偏好</t-button>
      <t-button theme="default" variant="outline" @click="emit('changePw')"><template #icon><LockOnIcon /></template>修改主密码</t-button>
      <t-button theme="default" variant="outline" @click="emit('newRecovery')"><template #icon><RefreshIcon /></template>重新生成恢复码</t-button>
    </div>
    <div class="mt-3">
      <t-button theme="danger" variant="outline" block @click="emit('wipe')"><template #icon><DeleteIcon /></template>清空本机全部数据</t-button>
    </div>
  </t-dialog>
</template>
