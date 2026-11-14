/**
 * 锦囊响应式编排（组合式函数）。
 *
 * 职责：持有 UI 状态（ref/reactive）、驱动 service、管理副作用（自动锁定定时器、
 * 剪贴板清除、可见性监听）。业务规则全部下沉到 services/safekeep，本文件只编排。
 * 遵循 vue.md §3/§4：派生值用 computed；定时器/监听在 onMounted 建立、onUnmounted 清理。
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch, type Ref } from 'vue'
import * as VC from '@/services/safekeep/crypto.ts'
import * as vault from '@/services/safekeep/vault.ts'
import { useCloudSync } from '@/composables/useCloudSync.ts'
import {
  consumeRestoreIntent, clearRestoreIntent, hasRestoreIntent, sessionRestoreStore,
} from '@/services/auth/restoreIntent.ts'
import {
  LS,
  browserStorage,
  getAccount,
  getPrefs,
  rawSnapshot,
  setPrefs,
  wipeAll,
  type StorageAdapter,
} from '@/services/safekeep/storage.ts'
import type { Account, PlainItem, PlainItems, Prefs } from '@/services/safekeep/types.ts'

export type Screen = 'welcome' | 'recovery' | 'locked' | 'vault'
export type DialogKind = 'editor' | 'generator' | 'health' | 'backup' | 'settings' | 'changePw' | 'newRecovery' | 'account' | 'storage' | null

export function useSafeKeep(store: StorageAdapter = browserStorage()) {
  // ---- 响应式状态 ----
  const screen: Ref<Screen> = ref('welcome')
  const account: Ref<Account | null> = ref(null)
  const plain = reactive<PlainItems>({})
  const revealed = reactive<Record<string, boolean>>({})
  const vk: Ref<Uint8Array | null> = ref(null)
  const pending: Ref<vault.PendingVault | null> = ref(null)
  const busy: Ref<boolean> = ref(false)
  const toastText: Ref<string> = ref('')
  const dialog: Ref<DialogKind> = ref(null)
  const editorTarget: Ref<PlainItem | null> = ref(null)

  const filter = ref('')
  const tag = ref('')
  const view = ref('all')
  const failCount = ref(0)
  const failHint: Ref<string> = ref('')
  const useRecovery = ref(false)
  const lastBackupAt: Ref<number | null> = ref(null)
  const countdown: Ref<string> = ref('')
  /** 云端恢复的阶段提示：让「登录 → 回跳 → 下载密文」每一步都可见，避免点了没反应。 */
  const restoreStage: Ref<string> = ref('')

  const prefs = reactive<Prefs>({ lockMode: 'leave', idleMs: 300000, clipSec: 15 })
  let lastActivity = Date.now()
  let lockTimer: ReturnType<typeof setInterval> | null = null
  let toastTimer: ReturnType<typeof setTimeout> | null = null
  let autoPushTimer: ReturnType<typeof setTimeout> | null = null
  let lastCopied: string | null = null
  let forcedChangePw = false

  // ---- 派生值 ----
  const unlocked = computed(() => vk.value !== null)
  const allItems = computed(() => Object.values(plain))
  const counts = computed(() => vault.viewCounts(plain))
  const visibleItems = computed(() =>
    vault.filterItems(plain, { view: view.value, tag: tag.value, filter: filter.value }),
  )
  const typeNav = computed(() => {
    const c: Record<string, number> = {}
    allItems.value.filter((p) => !p._deleted).forEach((p) => (c[p.type] = (c[p.type] || 0) + 1))
    return Object.keys(vault.TYPE_NAME).map((t) => ({ type: t, name: vault.TYPE_NAME[t as PlainItem['type']], count: c[t] || 0 }))
  })
  const tagNav = computed(() => {
    const c: Record<string, number> = {}
    allItems.value.filter((p) => !p._deleted).forEach((p) => (p.tags || []).forEach((t: string) => (c[t] = (c[t] || 0) + 1)))
    return Object.keys(c).sort().map((t) => ({ tag: t, count: c[t]! }))
  })
  const needBackup = computed(() => {
    const a = account.value
    return !a || !a.lastBackupAt || Date.now() - a.lastBackupAt > 7 * 86400000
  })
  /** 恢复码只显示这一次：从内存 pending 读取，确认后随 pending 清空而消失 */
  const pendingRecoveryCode = computed(() => pending.value?.recoveryCode ?? '')
  /** 密码生成器「用于新条目」的预填值 */
  const prefillPassword = ref('')
  /** 锁定模式派生：离开即锁 / 空闲超时锁 各自是否启用（both 时两者都开） */
  const lockOnHide = computed(() => prefs.lockMode === 'leave' || prefs.lockMode === 'both')
  const lockOnIdle = computed(() => prefs.lockMode === 'idle' || prefs.lockMode === 'both')
  const statusText = computed(() => {
    if (!account.value) return '未初始化'
    return unlocked.value ? '本地 · 已解锁' : '本地 · 已锁定'
  })

  // ---- 通用反馈 ----
  function toast(msg: string): void {
    toastText.value = msg
    if (toastTimer) clearTimeout(toastTimer)
    toastTimer = setTimeout(() => (toastText.value = ''), 2600)
  }

  function touch(): void {
    lastActivity = Date.now()
  }

  function stopAutoPush(): void {
    if (autoPushTimer) {
      clearTimeout(autoPushTimer)
      autoPushTimer = null
    }
  }

  /**
   * 编辑后自动上传（防抖 3s）：仅当已登录且可同步（canSync）时生效。
   * 期间再有编辑会顺延；到点调用 cloud.push()，若内容无变化会被 push 内部判重跳过，
   * 不会空转版本号。冲突（云端被其他端更新）不自动强推，交用户在同步面板手动处理。
   */
  function scheduleAutoPush(): void {
    if (!cloud.canSync.value) return
    stopAutoPush()
    autoPushTimer = setTimeout(() => {
      autoPushTimer = null
      void cloud.push().then((r) => {
        if (!r.ok && r.stale) {
          toast('云端有更新，自动上传已跳过，请在同步面板处理冲突')
        }
      })
    }, 3000)
  }

  // ---- 创建 / 恢复码确认 ----
  async function create(password: string, confirm: string): Promise<void> {
    if (password.length < 10) return toast('主密码至少 10 位，建议用一句长口令')
    if (password !== confirm) return toast('两次输入不一致')
    busy.value = true
    try {
      pending.value = await vault.createVault(password) // 只在内存
      screen.value = 'recovery'
    } catch (e) {
      toast('创建失败：' + (e as Error).message)
    } finally {
      busy.value = false
    }
  }

  function confirmRecovery(code: string): void {
    if (!pending.value) {
      screen.value = 'welcome'
      return
    }
    if (VC.normCode(code) !== VC.normCode(pending.value.recoveryCode)) return toast('恢复码不匹配，请重新核对')
    const made = pending.value
    pending.value = null
    account.value = vault.commitVault(store, made)
    lastBackupAt.value = null
    setPrefs(store, { ...prefs })
    Object.keys(plain).forEach((k) => delete plain[k])
    vk.value = made.vk
    lastActivity = Date.now()
    screen.value = 'vault'
    startLockTimer()
    toast('保险库已创建，现在就可以添加条目')
  }

  // ---- 解锁 / 锁定 ----
  async function unlock(secret: string, recovery: boolean): Promise<boolean> {
    busy.value = true
    try {
      const r = await vault.unlock(store, secret, recovery)
      vk.value = r.vk
      account.value = r.account
      lastBackupAt.value = r.account.lastBackupAt
      failCount.value = 0
      failHint.value = ''
      Object.keys(plain).forEach((k) => delete plain[k])
      Object.assign(plain, r.plain)
      Object.keys(revealed).forEach((k) => delete revealed[k])
      lastActivity = Date.now()
      screen.value = 'vault'
      startLockTimer()
      toast('已解锁 ' + Object.keys(r.plain).length + ' 条条目' + (r.broken.length ? '，' + r.broken.length + ' 条密文损坏已跳过' : ''))
      if (recovery) {
        forcedChangePw = true
        setTimeout(() => {
          dialog.value = 'changePw'
        }, 400)
        toast('恢复码解锁成功，请立即设置新的主密码')
      }
      return true
    } catch {
      vk.value = null
      Object.keys(plain).forEach((k) => delete plain[k])
      failCount.value++
      const wait = Math.min(30, Math.pow(2, failCount.value - 1))
      failHint.value = (recovery ? '恢复码' : '主密码') + '不正确（第 ' + failCount.value + ' 次失败）。请等待 ' + wait + ' 秒再试；连续失败会持续加长等待。'
      return false
    } finally {
      busy.value = false
    }
  }

  function lock(reason?: string): void {
    vk.value = null
    Object.keys(plain).forEach((k) => delete plain[k])
    Object.keys(revealed).forEach((k) => delete revealed[k])
    filter.value = ''
    tag.value = ''
    view.value = 'all'
    void clearClipboardIfOurs()
    stopLockTimer()
    stopAutoPush()
    dialog.value = null
    countdown.value = ''
    failHint.value = ''
    failCount.value = 0
    screen.value = 'locked'
    syncLockedHint()
    if (reason) toast(reason)
  }

  function syncLockedHint(): void {
    account.value = getAccount(store)
  }

  // ---- 自动锁定定时器 ----
  function stopLockTimer(): void {
    if (lockTimer) {
      clearInterval(lockTimer)
      lockTimer = null
    }
  }
  function startLockTimer(): void {
    stopLockTimer()
    lockTimer = setInterval(() => {
      if (!vk.value) return
      const hidden = typeof document !== 'undefined' && document.hidden
      const forceHide = lockOnHide.value && hidden
      // 锁定的唯一判据：离开页面（forceHide）或 空闲超时（仅 idle/both 时按 idleMs 计）。
      // 离开即锁模式下传入 idleMs=0，等价于关闭空闲超时，不会误锁。
      if (VC.shouldLock(Date.now(), lastActivity, lockOnIdle.value ? prefs.idleMs : 0, forceHide)) {
        lock(forceHide ? '已切到后台，保险库自动锁定' : '空闲超时，已自动锁定')
        return
      }
      if (lockOnIdle.value && prefs.idleMs > 0) {
        const left = Math.max(0, prefs.idleMs - (Date.now() - lastActivity))
        const m = Math.floor(left / 60000)
        const s = Math.floor((left % 60000) / 1000)
        countdown.value = '自动锁定 ' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0')
      } else {
        countdown.value = lockOnHide.value ? '离开页面即锁定' : '自动锁定已关闭'
      }
    }, 1000)
  }

  // ---- 剪贴板 ----
  async function clearClipboardIfOurs(): Promise<void> {
    if (!lastCopied) return
    const own = lastCopied
    try {
      const c = await navigator.clipboard.readText()
      if (c === own) await navigator.clipboard.writeText('')
    } catch {
      /* 无权限则忽略 */
    }
    if (lastCopied === own) lastCopied = null
  }
  async function copyWithClear(text: string): Promise<void> {
    lastCopied = text
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      /* 降级：部分环境无剪贴板权限，提示用户手动复制 */
    }
    toast('已复制，' + prefs.clipSec + ' 秒后自动清除剪贴板')
    setTimeout(() => void clearClipboardIfOurs(), prefs.clipSec * 1000)
  }

  // ---- 条目 CRUD ----
  async function save(p: PlainItem): Promise<void> {
    if (!vk.value) return toast('保险库已锁定')
    busy.value = true
    try {
      Object.assign(plain, await vault.saveItem(store, vk.value, p))
      toast('已加密保存到本地')
      scheduleAutoPush()
    } finally {
      busy.value = false
    }
  }
  async function remove(id: string, purge: boolean): Promise<void> {
    if (!vk.value) return
    await vault.deleteItem(store, vk.value, plain, id, purge)
    if (purge) delete revealed[id]
    toast(purge ? '已彻底删除' : '已移入回收站')
    scheduleAutoPush()
  }
  async function restore(id: string): Promise<void> {
    if (!vk.value) return
    await vault.restoreItem(store, vk.value, plain, id)
    toast('已恢复条目')
    scheduleAutoPush()
  }
  async function toggleFav(id: string): Promise<void> {
    if (!vk.value) return
    const p = plain[id]
    if (!p) return
    p.favorite = !p.favorite
    p.updatedAt = Date.now()
    await save(p)
    toast(p.favorite ? '已收藏' : '已取消收藏')
  }
  function newEntry(prefill = ''): void {
    editorTarget.value = null
    prefillPassword.value = prefill
    dialog.value = 'editor'
  }
  function editEntry(id: string): void {
    const p = plain[id]
    if (!p) return
    editorTarget.value = JSON.parse(JSON.stringify(p)) as PlainItem
    prefillPassword.value = ''
    dialog.value = 'editor'
  }

  // ---- 备份 / 偏好 / 改密 / 恢复码 ----
  function exportBackupText(): string {
    if (!account.value) return ''
    const a = vault.markBackedUp(store, account.value)
    account.value = a
    lastBackupAt.value = a.lastBackupAt
    return vault.buildBackupText(store, a)
  }
  function importBackupText(text: string, force: boolean): void {
    try {
      account.value = vault.applyBackup(store, text, force)
      lastBackupAt.value = account.value.lastBackupAt
      vk.value = null
      Object.keys(plain).forEach((k) => delete plain[k])
      stopLockTimer()
      dialog.value = null
      screen.value = 'locked'
      syncLockedHint()
      toast('备份已导入，请用备份文件对应的主密码解锁')
    } catch (e) {
      if ((e as Error).message === 'CONFIRM_OVERWRITE') throw e
      toast('导入失败：' + (e as Error).message)
    }
  }
  async function changePassword(newPassword: string): Promise<void> {
    if (!vk.value) return
    account.value = await vault.changePassword(store, vk.value, newPassword)
    forcedChangePw = false
    dialog.value = null
    toast('主密码已更新，条目密文未改动')
    scheduleAutoPush()
  }
  async function makeNewRecovery(): Promise<{ code: string; recovery: Account['recovery'] }> {
    if (!vk.value) throw new Error('保险库已锁定')
    return vault.refreshRecovery(vk.value)
  }
  function commitNewRecovery(recovery: Account['recovery']): void {
    account.value = vault.commitRecovery(store, recovery)
    toast('恢复码已更新，旧码已作废')
    scheduleAutoPush()
  }
  function savePrefs(next: Prefs): void {
    Object.assign(prefs, next)
    setPrefs(store, { ...prefs })
    lastActivity = Date.now()
    startLockTimer()
  }
  /**
   * 销毁本机保险库并回到欢迎页（可重新创建）。
   * 解锁页也必须能调用：主密码与恢复码都忘记时，这是唯一的出路，
   * 否则用户永远卡在 locked 页（旧版清空入口只在需解锁后才能打开的设置弹窗里）。
   */
  function wipe(): void {
    wipeAll(store)
    clearRestoreIntent(sessionRestoreStore()) // 清空本机后不要再用云端密文覆盖回来
    cloud.resetLocal() // 同步记账（cloudRev / 摘要）属于旧库，必须一并归零
    restoreStage.value = ''
    vk.value = null
    pending.value = null
    account.value = null
    lastBackupAt.value = null
    failCount.value = 0
    failHint.value = ''
    Object.keys(plain).forEach((k) => delete plain[k])
    Object.keys(revealed).forEach((k) => delete revealed[k])
    stopLockTimer()
    dialog.value = null
    screen.value = 'welcome'
    toast('本机密文已彻底清空，现在可以创建新的保险库')
  }
  function storageRaw(): string {
    return rawSnapshot(store)
  }
  function isForcedChangePw(): boolean {
    return forcedChangePw
  }

  // ---- 云端同步（零知识：密文直传；拉取覆盖后强制重新解锁）----
  const cloud = useCloudSync(store, {
    onApplied: () => {
      // 远端密文已写入本地存储；内存中的明文/密钥可能属于旧库，一律清空并锁定，
      // 让用户用（与云端一致的）主密码重新解锁，避免密钥与 salt 错配。
      lock('已从云端拉取密文，请用主密码重新解锁')
    },
  })

  // 登录态可能晚于视图挂载才就绪（SDK 异步 / OAuth 回跳二次加载）：持续观察，
  // 一旦就绪且仍有意图就续做。resumeCloudRestore 幂等，不会重复拉取覆盖。
  watch([cloud.authenticated, cloud.sub], () => resumeCloudRestore())

  // ---- 生命周期 ----
  function onVisibility(): void {
    if (typeof document === 'undefined') return
    const hidden = document.hidden
    if (hidden) {
      if (lockOnHide.value && vk.value) lock('已切到后台，保险库自动锁定')
    } else if (vk.value && lockOnIdle.value && VC.shouldLock(Date.now(), lastActivity, prefs.idleMs, false)) {
      lock('空闲超时，已自动锁定')
    }
    touch()
  }
  function onPointer(): void {
    touch()
  }
  function onStorage(e: StorageEvent): void {
    if (e.key === LS.a && !vk.value) syncLockedHint()
  }

  /**
   * 云端恢复续做（幂等）：判据只有「存在未过期意图」+「确实已登录」。
   *
   * 不再要求「本次刚消费过 OAuth 回调」——那是模块级瞬时标志，二次跳转、
   * 刷新或 SDK 异步就绪都会把它弄丢，正是本地流程断掉的原因之一。
   * 登录态尚未就绪时**保留意图**，由 watch(cloud.authenticated) 在就绪后重试；
   * TTL（10 分钟）+ 一次性消费保证不会静默反复覆盖本机。
   */
  function resumeCloudRestore(): void {
    const store = sessionRestoreStore()
    if (!hasRestoreIntent(store)) return
    if (!cloud.authenticated.value || !cloud.sub.value) {
      restoreStage.value = '登录尚未完成，请在 10 分钟内重新点「从云端恢复」'
      return
    }
    if (!consumeRestoreIntent(store)) return
    restoreStage.value = '登录成功，正在从云端下载密文…'
    void cloud.restoreFromCloud(true).then((r) => {
      if (r.kind === 'applied') {
        restoreStage.value = '' // onApplied 已 lock + 提示重新解锁
        return
      }
      restoreStage.value = r.message
      toast(r.message)
    })
  }

  /** 解锁页入口：撤掉待续做意图避免重复拉取，并把 outcome 转成可见提示。 */
  async function restoreFromCloud(): Promise<void> {
    clearRestoreIntent(sessionRestoreStore())
    restoreStage.value = '正在准备云端恢复…'
    const r = await cloud.restoreFromCloud(true)
    restoreStage.value = r.kind === 'applied' ? '' : r.message
    if (r.kind !== 'applied') toast(r.message)
  }

  onMounted(() => {
    const p = getPrefs(store) as Partial<Prefs> & { hideLock?: boolean }
    // 旧版用 hideLock 布尔，新版用 lockMode 三态：做向后兼容迁移，避免老用户偏好丢失。
    if (p.lockMode === 'leave' || p.lockMode === 'idle' || p.lockMode === 'both') {
      prefs.lockMode = p.lockMode
    } else if (p.hideLock === false) {
      prefs.lockMode = 'idle' // 旧版关掉了后台锁 → 仅空闲超时锁
    } else {
      prefs.lockMode = 'leave' // 默认：离开页面即锁定（亦覆盖旧版默认值）
    }
    prefs.idleMs = typeof p.idleMs === 'number' ? p.idleMs : 300000
    prefs.clipSec = p.clipSec || 15
    account.value = getAccount(store)
    lastBackupAt.value = account.value?.lastBackupAt ?? null
    screen.value = account.value ? 'locked' : 'welcome'
    document.addEventListener('visibilitychange', onVisibility)
    document.addEventListener('pointerdown', onPointer)
    document.addEventListener('keydown', onPointer)
    window.addEventListener('storage', onStorage)
    // 登录后回到锦囊：自动续做一次云端拉取（有严格三重判定，见上）
    resumeCloudRestore()
  })
  onUnmounted(() => {
    stopLockTimer()
    stopAutoPush()
    if (toastTimer) clearTimeout(toastTimer)
    document.removeEventListener('visibilitychange', onVisibility)
    document.removeEventListener('pointerdown', onPointer)
    document.removeEventListener('keydown', onPointer)
    window.removeEventListener('storage', onStorage)
  })

  return {
    // 状态
    screen, account, plain, revealed, busy, toastText, dialog, editorTarget,
    filter, tag, view, failCount, failHint, useRecovery, needBackup, countdown, prefs,
    forcedChangePw, pendingRecoveryCode, prefillPassword, restoreStage,
    // 派生
    unlocked, allItems, counts, visibleItems, typeNav, tagNav, statusText,
    // 云端同步
    cloud,
    // 方法
    toast, create, confirmRecovery, unlock, lock, copyWithClear, restoreFromCloud,
    save, remove, restore, toggleFav, newEntry, editEntry,
    exportBackupText, importBackupText, changePassword, makeNewRecovery, commitNewRecovery,
    savePrefs, wipe, storageRaw, isForcedChangePw,
  }
}
