/**
 * 「云端恢复意图」持久化（登录回跳续做的衔接点）。
 *
 * 场景：用户在锦囊解锁页点「登录并从云端恢复」→ 未登录 → 跳转 Logto →
 * OAuth 回调落在站点根 /tools/（hash 路由无 fragment）→ 需要：
 *   1) 知道用户原本是想「从云端恢复」而不是普通登录；
 *   2) 把路由定位回 #/safekeep；
 *   3) 登录成功后自动续做一次 pull，而不是要求用户再点一遍。
 *
 * 用 sessionStorage（登录是同一标签页会话内的事），带 TTL 防止陈旧意图：
 * 用户中途关闭/搁置太久，回来不会静默用云端覆盖本机。
 *
 * 纯逻辑 + 可注入 StorageAdapter，不碰 SDK / DOM / Vue，可在 node --test 下直测。
 */
import type { StorageAdapter } from '../safekeep/storage.ts'

const KEY = 'sk.cloudRestoreIntent'
/** 意图有效期：10 分钟。超时视为作废，避免隔天打开误触发覆盖。 */
export const RESTORE_INTENT_TTL_MS = 10 * 60 * 1000

interface RestoreIntent {
  /** 记录时刻（毫秒） */
  at: number
}

/** 浏览器会话存储实现；SSR/隐私模式降级为内存。 */
export function sessionRestoreStore(): StorageAdapter {
  if (typeof globalThis.sessionStorage === 'undefined') return memoryStore()
  return {
    getItem: (k) => {
      try { return globalThis.sessionStorage.getItem(k) } catch { return null }
    },
    setItem: (k, v) => {
      try { globalThis.sessionStorage.setItem(k, v) } catch { /* 隐私模式忽略 */ }
    },
    removeItem: (k) => {
      try { globalThis.sessionStorage.removeItem(k) } catch { /* 忽略 */ }
    },
  }
}

function memoryStore(): StorageAdapter {
  const m = new Map<string, string>()
  return {
    getItem: (k) => m.get(k) ?? null,
    setItem: (k, v) => { m.set(k, v) },
    removeItem: (k) => { m.delete(k) },
  }
}

/** 标记「接下来要云端恢复」。now 可注入以便测试。 */
export function markRestoreIntent(store: StorageAdapter, now: number = Date.now()): void {
  const intent: RestoreIntent = { at: now }
  store.setItem(KEY, JSON.stringify(intent))
}

/** 是否存在未过期的恢复意图。 */
export function hasRestoreIntent(store: StorageAdapter, now: number = Date.now()): boolean {
  const raw = store.getItem(KEY)
  if (!raw) return false
  try {
    const v = JSON.parse(raw) as Partial<RestoreIntent>
    if (typeof v.at !== 'number' || !Number.isFinite(v.at)) return false
    if (now - v.at > RESTORE_INTENT_TTL_MS || now < v.at) return false
    return true
  } catch {
    return false
  }
}

/**
 * 消费（读取并清除）恢复意图。过期或损坏一律返回 false 并清理，
 * 保证一个意图最多被续做一次，刷新页面不会重复拉取覆盖。
 */
export function consumeRestoreIntent(store: StorageAdapter, now: number = Date.now()): boolean {
  const ok = hasRestoreIntent(store, now)
  store.removeItem(KEY)
  return ok
}

/** 直接清除意图（取消恢复、登录失败时用）。 */
export function clearRestoreIntent(store: StorageAdapter): void {
  store.removeItem(KEY)
}

/**
 * 回调落在站点根时，是否应把路由归位到锦囊解锁页。
 *
 * 纯函数，便于 node --test 覆盖。只认「没有 hash / 仍旧是门户」三种形态；
 * 用户已经在 #/safekeep 或其它子页时不改路由，避免打断当前位置。
 */
export function shouldRestoreRoute(hash: string): boolean {
  return !hash || hash === '/' || hash === '#/'
}
