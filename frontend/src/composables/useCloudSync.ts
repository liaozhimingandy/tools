/**
 * 云端同步编排（组合式函数）：串联 Logto 登录态、HTTP 客户端、冲突判据与本地落盘。
 *
 * 零知识边界：本层搬运的始终是 {account(items 密文), items(密文), rev} 密封结构，
 * 不接触主密码、恢复码明文或 vaultKey。上传前无需解锁（密文直传），
 * 下载覆盖后强制回到「锁定」态，待用户用主密码重新解锁——与备份导入一致。
 *
 * 使用：由 useSafeKeep 创建并持有，UI 通过 sk.cloud 访问。
 */
import { computed, ref, type Ref } from 'vue'
import type { StorageAdapter } from '@/services/safekeep/storage.ts'
import {
  curRev, getAccount, getItems, getCloudRev, setCloudRev,
  setCloudSyncAt, getCloudSyncAt,
  getCloudBlobSig, setCloudBlobSig, clearCloudBlobSig,
} from '@/services/safekeep/storage.ts'
import {
  buildCloudBlob, decidePull, decidePush, toRemoteSummary,
  applyCloudBlob, BlobError, blobContentSig, type PushDecision,
} from '@/services/cloud/sync.ts'
import { fetchVault, fetchRevision, putVault, CloudError } from '@/services/cloud/client.ts'
import type { RemoteSummary } from '@/services/cloud/types.ts'
import { apiConfigured as apiConfiguredFn } from '@/config.ts'
import {
  isConfigured, currentSub, currentAccessToken, displayUser,
  cachedAuthState, signIn, type DisplayUser,
} from '@/services/auth/logto.ts'
import {
  markRestoreIntent, sessionRestoreStore,
} from '@/services/auth/restoreIntent.ts'
import type { Account } from '@/services/safekeep/types.ts'

// 设备标识：同一浏览器稳定，用于多端排障（明文元数据，非用户密钥）
function deviceId(): string {
  const key = 'sk.device'
  let id = globalThis.localStorage?.getItem(key)
  if (!id) {
    id = 'web-' + Math.random().toString(36).slice(2, 10)
    try { globalThis.localStorage?.setItem(key, id) } catch { /* 隐私模式忽略 */ }
  }
  return id.slice(0, 128)
}

export interface PushOutcome {
  ok: boolean
  message: string
  /** stale：云端被其他端更新，需要用户选择「拉取」或「强制覆盖」 */
  stale?: { remote: number; local: number }
  /** skipped：内容与上次同步一致，已跳过上传（云端版本号不变） */
  skipped?: boolean
}

export interface PullOutcome {
  ok: boolean
  message: string
  /** 已覆盖本地并需要重新解锁 */
  needUnlock?: boolean
  /** 云端空（404）：解锁页据此提示「先在本地创建或上传」 */
  empty?: boolean
}

/** 解锁页「从云端恢复」的编排结果，供 UI 分支处理。 */
export type RestoreKind = 'redirect' | 'need-api' | 'applied' | 'empty' | 'error'
export interface RestoreOutcome {
  kind: RestoreKind
  message: string
}

export function useCloudSync(
  store: StorageAdapter,
  deps: {
    /** 用远端 blob 覆盖本地后，通知上层刷新内存态并回到锁定态 */
    onApplied: (account: Account) => void
  },
) {
  // 同步读取 main.ts 挂载前 initAuth() 的结果，保证首屏即为正确登录态，不闪屏。
  // configured 只看 Logto：能登录即为 true；后端 API 是否就绪由 apiReady 单独表示，
  // 两者解耦后，未填后端地址时用户仍可先登录、看到账号态，恢复时得到可操作提示。
  const cached = cachedAuthState()
  const configured = ref(isConfigured())
  const apiReady = ref(apiConfiguredFn())
  const authenticated = ref(cached?.authenticated ?? false)
  const sub: Ref<string | null> = ref(cached?.sub ?? null)
  const user: Ref<DisplayUser | null> = ref(null)
  const busy = ref(false)
  const lastError = ref('')
  const cloudRev = ref(getCloudRev(store))
  const lastSyncedAt = ref(getCloudSyncAt(store))
  const remoteSummary: Ref<RemoteSummary | null> = ref(null)

  /** 完整同步能力：需 Logto 已配 + 后端 API 已配 + 已登录且有 sub。 */
  const canSync = computed(() => configured.value && apiReady.value && authenticated.value && !!sub.value)
  const statusText = computed(() => {
    if (!configured.value) return '仅本地 · 登录未配置'
    if (!authenticated.value) return '本地 · 可登录同步'
    if (!apiReady.value) return '已登录 · 云端地址未配置'
    return '已登录 · 可云端同步'
  })

  /**
   * 本机保险库被销毁后重置「同步记账」状态。
   * wipeAll 只清存储，不碰这些 ref；若不清，重建新库后 push 仍拿着旧 vault 的
   * cloudRev 去做 CAS，会被误判成冲突或直接覆盖错误版本。
   * 登录态本身保留（属于 Logto，不属于某个保险库）。
   */
  function resetLocal(): void {
    cloudRev.value = 0
    lastSyncedAt.value = null
    remoteSummary.value = null
    lastError.value = ''
    clearCloudBlobSig(store) // 内容签名属于旧库，销毁后必须归零，避免重建后误判「未变化」
  }

  /** 刷新登录态与用户信息（视图挂载后可调用，或登录态变化时）。 */
  async function refresh(): Promise<void> {
    const s = await currentSub()
    sub.value = s
    authenticated.value = !!s
    configured.value = isConfigured()
    apiReady.value = apiConfiguredFn()
    user.value = s ? await displayUser() : null
  }
  // 首屏若已登录，异步补齐展示信息（昵称/邮箱）
  if (authenticated.value) void refresh()

  async function login(): Promise<void> {
    await signIn() // 会跳转离开页面
  }
  async function logout(): Promise<void> {
    const { signOut } = await import('@/services/auth/logto.ts')
    await signOut() // 会跳转离开页面
  }

  /**
   * 解锁页「从云端恢复」：确保登录（未登录则标记意图并跳转），
   * 已登录且后端就绪则强制拉取覆盖（解锁页场景用户已主动点恢复，
   * 覆盖确认由 UI 在调用前完成）。回调落地后由 onMounted 续做真正的拉取。
   */
  async function restoreFromCloud(force = true): Promise<RestoreOutcome> {
    // 1) 未登录：标记「云端恢复」意图，避免回调后不知道要续做什么
    if (!authenticated.value || !sub.value) {
      markRestoreIntent(sessionRestoreStore())
      try {
        await login() // 跳转 Logto（可能不抛错但页面会卸载）
        return { kind: 'redirect', message: '正在跳转登录，回来后将自动从云端下载密文' }
      } catch (e) {
        return { kind: 'error', message: '登录跳转失败：' + (e as Error).message }
      }
    }
    // 2) 已登录但后端云端地址未配：给可操作提示，不静默失败
    if (!apiReady.value) {
      return {
        kind: 'need-api',
        message: '已登录，但后端云端地址尚未配置：请在仓库 Settings → Variables 添加 VITE_API_BASE_URL 并重新部署前端。',
      }
    }
    // 3) 已登录 + 后端就绪：拉取密文覆盖本机（onApplied 会锁定并提示重新解锁）
    const r = await pull(force)
    if (!r.ok) return { kind: r.empty ? 'empty' : 'error', message: r.message }
    return { kind: 'applied', message: r.message }
  }

  function requireOpts() {
    if (!sub.value) return null
    return {
      userSub: sub.value,
      getToken: currentAccessToken,
      device: deviceId(),
    }
  }

  /** 拉取远端摘要（拉取前确认用），不改动本地。 */
  async function inspect(): Promise<RemoteSummary | null> {
    const opts = requireOpts()
    if (!opts) {
      lastError.value = '请先登录再查看云端状态'
      return null
    }
    busy.value = true
    lastError.value = ''
    try {
      const remote = await fetchVault(opts)
      remoteSummary.value = toRemoteSummary(
        remote !== null,
        remote?.blob ?? null,
        remote ? { revision: remote.revision, updatedAt: remote.updatedAt, device: remote.device } : null,
      )
      return remoteSummary.value
    } catch (e) {
      lastError.value = friendlyError(e)
      return null
    } finally {
      busy.value = false
    }
  }

  /**
   * 上传本地密文到云端。expected_revision 用本地记录的 cloudRev 做 CAS。
   * force=true 时以当前远端 revision 为 base 强推（覆盖其他端改动）。
   *
   * 内容判重：若本次打包的内容与上次成功同步完全一致（排除 savedAt 时间戳），
   * 直接跳过 PUT，不调用 setCloudRev——云端版本号不会无谓自增（修复「上传相同内容版本也+1」）。
   */
  async function push(force = false): Promise<PushOutcome> {
    if (!canSync.value) return { ok: false, message: '请先登录并配置云端' }
    const account = getAccount(store)
    if (!account) return { ok: false, message: '本机还没有保险库，请先创建或拉取云端数据' }
    const opts = requireOpts()!
    const blob = buildCloudBlob(account, getItems(store), curRev(store))

    // —— 内容判重：相同则跳过，避免版本号空转 ——
    const sig = blobContentSig(blob)
    if (sig === getCloudBlobSig(store)) {
      return { ok: true, message: '内容未变化，已跳过上传（云端版本保持不变）', skipped: true }
    }

    busy.value = true
    lastError.value = ''
    try {
      const remoteRev = await fetchRevision(opts)
      const decision: PushDecision = decidePush(remoteRev, cloudRev.value)
      if (decision.kind === 'stale' && !force) {
        const msg = '云端已被其他设备更新，请先「从云端拉取」合并；确认要覆盖请用强制上传。'
        lastError.value = msg
        return { ok: false, message: msg, stale: { remote: decision.remote, local: decision.local } }
      }
      let expected: number
      if (decision.kind === 'create') expected = 0
      else if (force) expected = remoteRev ?? 0
      else if (decision.kind === 'update') expected = decision.base
      else expected = remoteRev ?? 0 // stale 且未强推：不会再走到这里（上面已 return）

      const res = await putVault(opts, blob, expected)
      setCloudRev(store, res.revision)
      setCloudSyncAt(store, Date.now())
      cloudRev.value = res.revision
      lastSyncedAt.value = Date.now()
      setCloudBlobSig(store, sig) // 记录本次成功上传的内容签名，供下次判重
      const msg = `已加密上传 ${Object.keys(blob.items).length} 条密文到云端（版本 ${res.revision}）`
      return { ok: true, message: msg }
    } catch (e) {
      const msg = friendlyError(e)
      lastError.value = msg
      return { ok: false, message: msg }
    } finally {
      busy.value = false
    }
  }

  /**
   * 从云端拉取并覆盖本地。任何覆盖都需显式 force（UI 二次确认),
   * 避免静默丢弃本机较新条目。覆盖后强制重新解锁。
   */
  async function pull(force = false): Promise<PullOutcome> {
    if (!canSync.value) return { ok: false, message: '请先登录并配置云端' }
    const opts = requireOpts()!
    busy.value = true
    lastError.value = ''
    try {
      const remote = await fetchVault(opts)
      if (!remote) return { ok: false, message: '云端还没有同步数据', empty: true }
      const localRev = curRev(store)
      const decision = decidePull(remote.blob.rev, localRev)
      if (decision.kind === 'up-to-date' && !force) {
        return { ok: false, message: '本机与云端版本一致，无需拉取' }
      }
      if (decision.kind === 'older' && !force) {
        const msg = `云端条目版本（${remote.blob.rev}）比本机（${localRev}）更旧，覆盖会丢失本机较新数据；确认请强制拉取。`
        lastError.value = msg
        return { ok: false, message: msg }
      }
      const account = applyCloudBlob(store, remote.blob)
      setCloudRev(store, remote.revision)
      setCloudSyncAt(store, Date.now())
      cloudRev.value = remote.revision
      lastSyncedAt.value = Date.now()
      setCloudBlobSig(store, blobContentSig(remote.blob)) // 拉取后本地内容==远端，刷新签名，避免随后无谓上传
      remoteSummary.value = toRemoteSummary(
        true, remote.blob,
        { revision: remote.revision, updatedAt: remote.updatedAt, device: remote.device },
      )
      deps.onApplied(account) // 通知上层清空内存明文、锁定、刷新账户显示
      return { ok: true, message: '已从云端拉取密文并覆盖本机，请用主密码重新解锁', needUnlock: true }
    } catch (e) {
      const msg = friendlyError(e)
      lastError.value = msg
      return { ok: false, message: msg }
    } finally {
      busy.value = false
    }
  }

  return {
    configured, apiReady, authenticated, sub, user, busy, lastError,
    cloudRev, lastSyncedAt, remoteSummary, canSync, statusText,
    refresh, login, logout, inspect, push, pull, restoreFromCloud, resetLocal,
  }
}

/** 把底层错误转成面向用户的可读信息，且绝不泄漏 value 内容。 */
export function friendlyError(e: unknown): string {
  if (e instanceof CloudError) {
    if (e.code === 'NOT_CONFIGURED') return '云端同步未配置'
    if (e.code === 'REVISION_CONFLICT') return '版本冲突：其他设备刚更新过，请拉取后重试'
    if (e.code === 'VALUE_TOO_LARGE') return '数据超过云端大小上限，请精简条目或导出备份'
    if (e.code === 'UNAUTHORIZED') return '登录已失效，请重新登录'
    return e.message || `云端请求失败（${e.status}）`
  }
  if (e instanceof BlobError) return `云端数据不可用：${e.message}`
  if (e instanceof TypeError && /fetch|network|Failed/i.test(e.message)) {
    return '无法连接云端，请检查网络与 API 地址'
  }
  return (e as Error)?.message || '云端同步发生未知错误'
}

export type CloudSync = ReturnType<typeof useCloudSync>
