/**
 * 存储层（可注入适配器）。
 *
 * 零知识边界：本层只读写「被主密码包裹的账户 + 条目密文 + 非敏感偏好」。
 * 明文 vaultKey 与解密后的条目只存在于内存（由 vault.ts / composable 持有），
 * 绝不经过本层，因此后端与本地存储都看不到任何明文。
 *
 * 适配器让同一份业务逻辑可在浏览器（localStorage）与 Node 测试（内存）间复用。
 */
import type { Account, Prefs, StoredItems } from './types.ts'

/** 存储键前缀统一为 sk.*（锦囊 SafeKeep） */
export const LS = {
  a: 'sk.account',
  i: 'sk.items',
  r: 'sk.rev',
  p: 'sk.prefs',
  /** 上次成功同步到的「后端 revision」，用于判断云端是否被其他设备更新（非明文） */
  c: 'sk.cloudRev',
  /** 上次成功同步的时间戳（毫秒），仅展示用 */
  t: 'sk.cloudSyncAt',
  /** 上次成功同步的「内容签名」（排除 savedAt 时间戳），用于判重，避免相同内容重复上传导致版本号无谓自增 */
  s: 'sk.cloudBlobSig',
} as const

/** 最小存储契约，对齐 Storage 的同步子集 */
export interface StorageAdapter {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

/** 浏览器实现：直接委托 localStorage */
export function browserStorage(): StorageAdapter {
  return {
    getItem: (k) => globalThis.localStorage.getItem(k),
    setItem: (k, v) => globalThis.localStorage.setItem(k, v),
    removeItem: (k) => globalThis.localStorage.removeItem(k),
  }
}

/** Node 测试实现：进程内 Map */
export function memoryStorage(): StorageAdapter {
  const m = new Map<string, string>()
  return {
    getItem: (k) => (m.has(k) ? m.get(k)! : null),
    setItem: (k, v) => {
      m.set(k, v)
    },
    removeItem: (k) => {
      m.delete(k)
    },
  }
}

function readJSON<T>(store: StorageAdapter, key: string, fallback: T): T {
  try {
    const raw = store.getItem(key)
    if (raw === null) return fallback
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

export function getAccount(store: StorageAdapter): Account | null {
  const v = readJSON<Account | null>(store, LS.a, null)
  return v && typeof v === 'object' ? v : null
}
export function setAccount(store: StorageAdapter, a: Account): void {
  store.setItem(LS.a, JSON.stringify(a))
}
export function getItems(store: StorageAdapter): StoredItems {
  return readJSON<StoredItems>(store, LS.i, {})
}
export function setItems(store: StorageAdapter, o: StoredItems): void {
  store.setItem(LS.i, JSON.stringify(o))
}
export function curRev(store: StorageAdapter): number {
  return parseInt(store.getItem(LS.r) || '0', 10) || 0
}
export function setRev(store: StorageAdapter, n: number): void {
  store.setItem(LS.r, String(n))
}
export function nextRev(store: StorageAdapter): number {
  const r = curRev(store) + 1
  setRev(store, r)
  return r
}
/** 偏好可能来自旧版本或首次运行，字段不一定齐全，故返回 Partial，由调用方用默认值补齐 */
export function getPrefs(store: StorageAdapter): Partial<Prefs> {
  return readJSON<Partial<Prefs>>(store, LS.p, {})
}
export function setPrefs(store: StorageAdapter, p: Prefs): void {
  try {
    store.setItem(LS.p, JSON.stringify(p))
  } catch {
    /* 偏好写入失败不影响保险库 */
  }
}
/** 上次成功同步到的后端 revision；0 表示从未同步。 */
export function getCloudRev(store: StorageAdapter): number {
  const n = parseInt(store.getItem(LS.c) || '0', 10)
  return Number.isSafeInteger(n) && n >= 0 ? n : 0
}
export function setCloudRev(store: StorageAdapter, n: number): void {
  store.setItem(LS.c, String(n))
}
/** 上次成功同步时间戳；null 表示从未同步。 */
export function getCloudSyncAt(store: StorageAdapter): number | null {
  const raw = store.getItem(LS.t)
  if (raw === null) return null
  const n = parseInt(raw, 10)
  return Number.isSafeInteger(n) && n > 0 ? n : null
}
export function setCloudSyncAt(store: StorageAdapter, ts: number): void {
  store.setItem(LS.t, String(ts))
}
/** 上次成功同步的「内容签名」；空串表示从未同步。 */
export function getCloudBlobSig(store: StorageAdapter): string {
  return store.getItem(LS.s) || ''
}
export function setCloudBlobSig(store: StorageAdapter, sig: string): void {
  store.setItem(LS.s, sig)
}
export function clearCloudBlobSig(store: StorageAdapter): void {
  store.removeItem(LS.s)
}

export function wipeAll(store: StorageAdapter): void {
  Object.values(LS).forEach((k) => store.removeItem(k))
}

/** 导出存储原始文本，供「本地存储自检」验证只存密文 */
export function rawSnapshot(store: StorageAdapter): string {
  return [LS.a, LS.i, LS.p].map((k) => store.getItem(k) || '').join('\n')
}
