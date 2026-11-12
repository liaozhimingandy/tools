<script setup lang="ts">
/** 备份与恢复：导出加密备份、从备份导入（覆盖需二次确认）。 */
import { ref } from 'vue'
import { DownloadIcon, UploadIcon, ErrorCircleIcon } from 'tdesign-icons-vue-next'

const props = defineProps<{
  lastBackupAt: number | null
  itemCount: number
}>()
const emit = defineEmits<{
  close: []
  export: []
  import: [text: string, force: boolean]
  toast: [msg: string]
}>()

const visible = ref(true)
const fileInput = ref<HTMLInputElement | null>(null)
const pendingText = ref<string | null>(null)

function fmtTime(ts: number | null): string {
  return ts ? new Date(ts).toLocaleString('zh-CN') : '从未'
}
function onFile(e: Event): void {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    const text = String(reader.result || '')
    try {
      emit('import', text, false)
    } catch {
      // 父级抛 CONFIRM_OVERWRITE，这里弹二次确认
      pendingText.value = text
    }
  }
  reader.onerror = () => emit('toast', '文件读取失败')
  reader.readAsText(file)
  input.value = ''
}
function forceImport(): void {
  if (pendingText.value) emit('import', pendingText.value, true)
  pendingText.value = null
}
</script>

<template>
  <t-dialog
    v-model:visible="visible"
    :header="pendingText ? '导入会覆盖当前保险库' : '备份与恢复'"
    width="500px"
    :footer="false"
    @close="emit('close')"
  >
    <template v-if="!pendingText">
      <p class="dlg-desc">备份文件是完整密文（含被主密码包裹的密钥），可离线保存、跨设备导入；没有主密码或恢复码，谁也打不开。</p>
      <div class="kv"><span>上次导出</span><span>{{ fmtTime(lastBackupAt) }}</span></div>
      <div class="kv"><span>条目密文数</span><span>{{ itemCount }}</span></div>
      <div class="kv"><span>当前版本库格式</span><span>safekeep-local v1</span></div>
      <t-alert theme="warning" class="my-4">
        <template #message>浏览器清理站点数据、无痕模式关闭、换设备或换浏览器都会导致本地数据丢失。<b>导出的加密备份是唯一副本</b>，请定期更新并离线保管。</template>
      </t-alert>
      <div class="flex gap-2">
        <t-button theme="primary" class="flex-1" @click="emit('export')"><template #icon><DownloadIcon /></template>导出加密备份</t-button>
        <t-button theme="default" variant="outline" class="flex-1" @click="fileInput?.click()"><template #icon><UploadIcon /></template>从备份导入</t-button>
      </div>
      <p class="hint">导入会覆盖本机现有保险库，操作前会二次确认。</p>
      <input ref="fileInput" type="file" accept=".json,application/json" style="display: none" @change="onFile" />
    </template>
    <template v-else>
      <p class="dlg-desc">当前设备已有一个保险库。导入备份会替换本机全部密文，且无法撤销。建议先导出当前库的备份。</p>
      <t-alert theme="error" class="my-4">
        <template #message><ErrorCircleIcon class="mr-1" />如果当前库里还有未备份的条目，请先取消并导出。</template>
      </t-alert>
      <div class="flex gap-2">
        <t-button theme="danger" class="flex-1" @click="forceImport">确认覆盖导入</t-button>
        <t-button theme="default" variant="outline" class="flex-1" @click="pendingText = null">取消</t-button>
      </div>
    </template>
  </t-dialog>
</template>
