/**
 * 「登录后启动应用」意图：未登录用户点应用 → 记下 code → 跳 Logto →
 * 回调回门户后自动续做启动，不用用户再点一次。
 *
 * 与 restoreIntent.ts 同构（sessionStorage + TTL + 一次性消费）：
 * 纯逻辑部分不碰 SDK / DOM / Vue，可在 node --test 下直接测。
 */

const KEY = 'portal.launchIntent'
export const LAUNCH_INTENT_TTL_MS = 10 * 60 * 1000

interface LaunchIntent {
  code: string
  at: number
}

export interface StringStore {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

export function sessionLaunchStore(): StringStore {
  if (typeof globalThis.sessionStorage === 'undefined') {
    const m = new Map<string, string>()
    return {
      getItem: (k) => m.get(k) ?? null,
      setItem: (k, v) => { m.set(k, v) },
      removeItem: (k) => { m.delete(k) },
    }
  }
  return {
    getItem: (k) => { try { return globalThis.sessionStorage.getItem(k) } catch { return null } },
    setItem: (k, v) => { try { globalThis.sessionStorage.setItem(k, v) } catch { /* 隐私模式 */ } },
    removeItem: (k) => { try { globalThis.sessionStorage.removeItem(k) } catch { /* 忽略 */ } },
  }
}

/** 记录启动意图。now 可注入以便测试。 */
export function markLaunchIntent(store: StringStore, code: string, now = Date.now()): void {
  store.setItem(KEY, JSON.stringify({ code, at: now } satisfies LaunchIntent))
}

/** 读取未过期意图（不消费）。 */
export function peekLaunchIntent(store: StringStore, now = Date.now()): string | null {
  const raw = store.getItem(KEY)
  if (!raw) return null
  try {
    const v = JSON.parse(raw) as Partial<LaunchIntent>
    if (typeof v.code !== 'string' || !v.code || typeof v.at !== 'number') return null
    if (!Number.isFinite(v.at) || now - v.at > LAUNCH_INTENT_TTL_MS || now < v.at) return null
    return v.code
  } catch {
    return null
  }
}

/** 一次性消费意图；过期/损坏也清理，避免陈旧数据滞留。 */
export function consumeLaunchIntent(store: StringStore, now = Date.now()): string | null {
  const code = peekLaunchIntent(store, now)
  store.removeItem(KEY)
  return code
}

export function clearLaunchIntent(store: StringStore): void {
  store.removeItem(KEY)
}
