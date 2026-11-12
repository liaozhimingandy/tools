<script setup lang="ts">
/**
 * 账号中心与云端同步（零知识）。
 *
 * 三种状态：
 *  1) 未配置（缺 VITE_API_BASE_URL / VITE_LOGTO_*）：说明如何开启，保持纯本地；
 *  2) 已配置未登录：Logto 登录按钮，登录后才能同步；
 *  3) 已登录：查看云端摘要、从云端拉取 / 上传到云端 / 强制覆盖，均二次确认。
 * 上传的是 {account, items, rev} 密文密封结构，主密码/恢复码/vaultKey 永不上云。
 */
import { ref } from 'vue'
import { CloudIcon, LockOnIcon, RefreshIcon, UploadIcon, DownloadIcon, LogoutIcon } from 'tdesign-icons-vue-next'
import type { CloudSync } from '@/composables/useCloudSync.ts'

const props = defineProps<{ cloud: CloudSync }>()
const emit = defineEmits<{
  close: []
  toast: [msg: string]
  needUnlock: [msg: string]
}>()

const visible = ref(true)
/** 拉取/覆盖的二次确认：云端比本机旧、或覆盖会丢数据时置位 */
const confirmPull = ref(false)
const confirmForcePush = ref(false)

function fmtTime(ts: number | null | undefined): string {
  if (!ts) return '从未'
  return new Date(ts).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
function close(): void {
  visible.value = false
  emit('close')
}

async function onLogin(): Promise<void> {
  try { await props.cloud.login() } catch (e) { emit('toast', '登录跳转失败：' + (e as Error).message) }
}
async function onLogout(): Promise<void> {
  try { await props.cloud.logout() } catch (e) { emit('toast', '登出失败：' + (e as Error).message) }
}
async function onInspect(): Promise<void> {
  const s = await props.cloud.inspect()
  if (!s) return
  if (s.exists) emit('toast', `云端已有 ${s.itemCount} 条密文（逻辑版本 ${s.blobRev}）`)
  else emit('toast', '云端暂无数据，可上传本地密文')
}

/** 拉取：默认拒绝覆盖较新本地；older 时需用户二次确认强制拉取。 */
async function onPull(force = false): Promise<void> {
  if (!confirmPull.value) {
    const s = await props.cloud.inspect()
    if (s?.exists) {
      confirmPull.value = true // 展示确认条，用户再点一次
      return
    }
  }
  confirmPull.value = false
  const r = await props.cloud.pull(force)
  emit('toast', r.message)
  if (r.ok && r.needUnlock) {
    emit('needUnlock', r.message)
    close()
  }
}

/** 上传：遇 stale 需二次确认强制覆盖。 */
async function onPush(force = false): Promise<void> {
  if (confirmForcePush.value && !force) return
  const r = await props.cloud.push(force)
  if (!r.ok && r.stale) {
    confirmForcePush.value = true
    emit('toast', r.message)
    return
  }
  confirmForcePush.value = false
  emit('toast', r.message)
}
</script>

<template>
  <t-dialog
    v-model:visible="visible"
    header="账号中心与云端同步"
    width="560px"
    :footer="false"
    @close="emit('close')"
  >
    <!-- 状态 1：未配置 -->
    <template v-if="!cloud.configured.value">
      <p class="dlg-desc">当前是 <b>纯本地模式</b>：数据只保存在这台设备，不上传任何服务器。</p>
      <t-alert theme="info">
        <template #message>要启用「登录后云端同步」，需在构建前端时配置环境变量（不影响本地功能）。</template>
      </t-alert>
      <ul class="plan-list mono text-[12px]">
        <li>VITE_API_BASE_URL=https://你的后端域名</li>
        <li>VITE_LOGTO_ENDPOINT / VITE_LOGTO_APP_ID</li>
        <li>VITE_LOGTO_RESOURCE（API resource，可选）</li>
        <li>VITE_LOGTO_REDIRECT_URI=https://…/tools/ （无 #，且需在 Logto 控制台加白名单）</li>
      </ul>
      <p class="hint">缺任一配置都会自动保持纯本地，绝不影响离线使用。配置说明见项目 README。</p>
      <div class="flex mt-5">
        <t-button theme="primary" variant="outline" block @click="close">知道了</t-button>
      </div>
    </template>

    <!-- 状态 2：已配置未登录 -->
    <template v-else-if="!cloud.authenticated.value">
      <p class="dlg-desc">云端同步已就绪，登录后即可把密文同步到你的账号。</p>
      <div class="kv"><span>云端</span><span class="mono">{{ cloud.statusText.value }}</span></div>
      <div class="kv"><span>上次同步</span><span>{{ fmtTime(cloud.lastSyncedAt.value) }}</span></div>
      <t-alert theme="warning" class="my-4">
        <template #message>当前后端为<b>暂时不鉴权</b>阶段：身份由浏览器声明、服务端不校验签名。密文无法被他人解密，但可能被覆盖/删除。请同时保留本地加密备份。</template>
      </t-alert>
      <div class="flex gap-2 mt-5">
        <t-button theme="primary" class="flex-1" :loading="cloud.busy.value" @click="onLogin">
          <CloudIcon class="mr-1" /> 登录并启用同步
        </t-button>
        <t-button theme="default" variant="outline" class="flex-1" @click="close">暂不登录</t-button>
      </div>
    </template>

    <!-- 状态 3：已登录 -->
    <template v-else>
      <p class="dlg-desc">登录身份仅用于隔离云端密文；<b>主密码与密钥始终只在这台设备</b>，不会上传。</p>
      <div class="kv"><span>账号</span><span>{{ cloud.user.value?.name || cloud.user.value?.email || cloud.sub.value }}</span></div>
      <div class="kv"><span>用户 ID</span><span class="mono text-[11px]">{{ cloud.sub.value }}</span></div>
      <div class="kv"><span>本地逻辑版本</span><span class="mono">{{ cloud.cloudRev.value }}</span></div>
      <div class="kv"><span>上次同步</span><span>{{ fmtTime(cloud.lastSyncedAt.value) }}</span></div>

      <div v-if="cloud.remoteSummary.value?.exists" class="cipher-box mt-3">
        <div class="kv"><span>云端条目</span><span>{{ cloud.remoteSummary.value.itemCount }} 条密文</span></div>
        <div class="kv"><span>云端逻辑版本</span><span class="mono">{{ cloud.remoteSummary.value.blobRev }}</span></div>
        <div class="kv"><span>云端保存于</span><span>{{ fmtTime(cloud.remoteSummary.value.savedAt) }}</span></div>
      </div>
      <p v-else-if="cloud.remoteSummary.value" class="hint">云端暂无数据，可点击「上传到云端」建立第一份密文。</p>

      <t-alert v-if="cloud.lastError.value" theme="error" class="my-3">
        <template #message>{{ cloud.lastError.value }}</template>
      </t-alert>

      <!-- 强制覆盖二次确认 -->
      <t-alert v-if="confirmForcePush" theme="warning" class="my-3">
        <template #message>云端有另一个设备更新的版本。<b>强制上传会用本机密文覆盖它</b>，其他设备随后需重新拉取。确认继续？</template>
        <template #action>
          <t-button size="small" theme="warning" @click="onPush(true)">确认覆盖云端</t-button>
          <t-button size="small" variant="text" @click="confirmForcePush = false">取消</t-button>
        </template>
      </t-alert>
      <t-alert v-if="confirmPull" theme="warning" class="my-3">
        <template #message>拉取会<b>用云端密文覆盖本机</b>，本机较新的未同步条目可能丢失。建议先导出本地备份。确认继续？</template>
        <template #action>
          <t-button size="small" theme="warning" :loading="cloud.busy.value" @click="onPull(true)">确认覆盖本机</t-button>
          <t-button size="small" variant="text" @click="confirmPull = false">取消</t-button>
        </template>
      </t-alert>

      <div class="actions mt-5">
        <t-button variant="outline" :loading="cloud.busy.value" @click="onInspect">
          <template #icon><RefreshIcon /></template>检查云端
        </t-button>
        <t-button variant="outline" :loading="cloud.busy.value" @click="onPull()">
          <template #icon><DownloadIcon /></template>从云端拉取
        </t-button>
        <t-button theme="primary" :loading="cloud.busy.value" @click="onPush()">
          <template #icon><UploadIcon /></template>上传到云端
        </t-button>
      </div>

      <t-divider class="my-4" />
      <div class="flex items-center gap-2">
        <LockOnIcon class="text-ink-3" />
        <span class="hint flex-1 !mt-0">零知识：上传的是密封密文，云端与后端都看不到你的主密码、恢复码或明文条目。</span>
        <t-button size="small" variant="text" theme="danger" @click="onLogout">
          <LogoutIcon class="mr-1" /> 退出登录
        </t-button>
      </div>
    </template>
  </t-dialog>
</template>

<style scoped>
.plan-list {
  padding-left: 18px;
  color: var(--color-ink-2);
  line-height: 1.9;
  margin: 12px 0;
  background: var(--color-canvas);
  border: 1px solid var(--color-line);
  border-radius: 8px;
  padding: 12px 12px 12px 30px;
}
.cipher-box {
  background: var(--color-brand-softer);
  border: 1px solid var(--color-line);
  border-radius: 8px;
  padding: 4px 12px;
}
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.actions :deep(.t-button) { flex: 1; min-width: 130px; }
</style>
