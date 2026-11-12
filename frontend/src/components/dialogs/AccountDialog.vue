<script setup lang="ts">
/**
 * 账号中心与云端同步（零知识）。
 *
 * 三种状态（Logto 登录能力与后端 API 已解耦）：
 *  1) Logto 未配置：说明如何开启，保持纯本地（内联默认值后一般不触发）；
 *  2) 已配 Logto 未登录：登录按钮；若后端 VITE_API_BASE_URL 未配会额外提示，
 *     但仍允许先登录，避免用总开关把登录入口整个藏掉；
 *  3) 已登录：若后端未配则显示可操作提示、隐藏同步操作；否则查看摘要、
 *     拉取 / 上传 / 强制覆盖，均二次确认。退出登录始终可用。
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
    <!-- 状态 1：Logto 未配置（内联默认值后一般不会触发，仅自定义构建可能） -->
    <template v-if="!cloud.configured.value">
      <p class="dlg-desc">当前是 <b>纯本地模式</b>：数据只保存在这台设备，不上传任何服务器。</p>
      <t-alert theme="info">
        <template #message>登录未启用。前端需配置 Logto endpoint / appId 才能登录并同步。</template>
      </t-alert>
      <p class="hint">当前构建已内置 Logto 公共客户端配置；若你看到此提示，请检查构建产物或改用官方工作流重新部署。</p>
      <div class="flex mt-5">
        <t-button theme="primary" variant="outline" block @click="close">知道了</t-button>
      </div>
    </template>

    <!-- 状态 2：已配置 Logto 但未登录 -->
    <template v-else-if="!cloud.authenticated.value">
      <p class="dlg-desc">登录后即可把密文同步到你的账号，或在换设备时从云端恢复。</p>
      <div class="kv"><span>状态</span><span class="mono">{{ cloud.statusText.value }}</span></div>
      <div class="kv"><span>上次同步</span><span>{{ fmtTime(cloud.lastSyncedAt.value) }}</span></div>
      <t-alert v-if="!cloud.apiReady.value" theme="warning" class="my-4">
        <template #message>后端云端地址尚未配置：请到仓库 <b>Settings → Variables</b> 添加 <code>VITE_API_BASE_URL</code>（后端 HTTPS 域名）并重新部署。此时可先登录，但上传/下载会提示未就绪。</template>
      </t-alert>
      <t-alert theme="warning" class="my-4">
        <template #message>当前后端为<b>暂时不鉴权</b>阶段：身份由浏览器声明、服务端不校验签名。密文无法被他人解密，但可能被覆盖/删除。请同时保留本地加密备份。</template>
      </t-alert>
      <div class="flex gap-2 mt-5">
        <t-button theme="primary" class="flex-1" :loading="cloud.busy.value" @click="onLogin">
          <CloudIcon class="mr-1" /> 登录
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

      <t-alert v-if="!cloud.apiReady.value" theme="warning" class="my-4">
        <template #message>已登录，但<b>后端云端地址尚未配置</b>，暂不能上传/下载。请到仓库 <b>Settings → Variables</b> 添加 <code>VITE_API_BASE_URL</code> 并重新部署前端；配置后回到这里点「检查云端」即可。</template>
      </t-alert>

      <template v-if="cloud.apiReady.value">
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
      </template>

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
