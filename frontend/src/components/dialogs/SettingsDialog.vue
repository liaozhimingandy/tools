<script setup lang="ts">
/** 设置：自动锁定方式、空闲时长、剪贴板秒数 + 危险操作入口。 */
import { computed, reactive, ref } from 'vue'
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
const lockOptions: Array<{ value: Prefs['lockMode']; label: string }> = [
  { value: 'leave', label: '离开页面即锁定' },
  { value: 'idle', label: '空闲超时锁定' },
  { value: 'both', label: '两者都启用' },
]
const form = reactive({
  lockMode: (props.prefs.lockMode || 'leave') as Prefs['lockMode'],
  idleMs: props.prefs.idleMs,
  clipSec: props.prefs.clipSec,
})
const idleEnabled = computed(() => form.lockMode === 'idle' || form.lockMode === 'both')
function fmtTime(ts: number | null): string {
  return ts ? new Date(ts).toLocaleString('zh-CN') : '从未'
}
function save(): void {
  emit('save', {
    lockMode: form.lockMode,
    idleMs: Number(form.idleMs) || 0,
    clipSec: Math.max(5, Math.min(120, Number(form.clipSec) || 15)),
  })
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

    <label class="field-label">自动锁定方式</label>
    <t-radio-group v-model="form.lockMode" variant="default-filled" class="mb-3.5">
      <t-radio-button v-for="o in lockOptions" :key="o.value" :value="o.value">{{ o.label }}</t-radio-button>
    </t-radio-group>
    <template v-if="idleEnabled">
      <label class="field-label">空闲超时时长</label>
      <t-select v-model="form.idleMs" class="mb-3.5">
        <t-option v-for="[v, label] in idleOptions" :key="v" :value="v" :label="label" />
      </t-select>
    </template>
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
