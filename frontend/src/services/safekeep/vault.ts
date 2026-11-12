/**
 * 业务编排层（无 DOM、无 UI）。
 *
 * 收拢示例 index.html 应用层函数：创建/解锁、条目 CRUD、回收站、备份、
 * 改密、恢复码刷新。全部以 StorageAdapter 为参数，明文只在返回值/入参的
 * 内存对象里流转，写盘前一律经 crypto.encryptJSON 变成 {iv,ct}。
 *
 * 视图/composable 负责响应式状态与副作用（定时器、剪贴板、toast），本层不碰。
 */
import * as VC from './crypto.ts'
import { LS, curRev, getAccount, getItems, nextRev, setAccount, setItems, setRev } from './storage.ts'
import type { StorageAdapter } from './storage.ts'
import type {
  Account,
  BackupDoc,
  PendingVault,
  PlainItem,
  PlainItems,
  Prefs,
  SealedRecord,
  StoredItem,
  StoredItems,
  UnlockResult,
} from './types'

export const DEFAULT_PREFS: Prefs = { idleMs: 300000, hideLock: true, clipSec: 15 }

export const TYPE_NAME: Record<PlainItem['type'], string> = {
  login: '登录',
  note: '安全笔记',
  card: '银行卡',
  wifi: 'WiFi',
  apikey: 'API 密钥',
}

/**
 * 深拷贝明文条目，供 UI 表单在保存/编辑时脱离 Vue 响应式 Proxy。
 *
 * PlainItem 全是 JSON 安全字段，JSON 深拷贝语义等价。刻意不用 structuredClone：
 * reactive() 返回 Proxy，structuredClone 克隆 Proxy 会抛 DataCloneError，
 * 在表单 submit 里会导致 save 事件发不出去（表现为「点保存没反应」）。
 * 此函数无 DOM/无 Vue 依赖，可在 Node 里直接测试。
 */
export function cloneItem(p: PlainItem): PlainItem {
  return JSON.parse(JSON.stringify(p)) as PlainItem
}

/** 构造一条空白明文条目 */
export function newPlain(): PlainItem {
  const t = VC.now()
  return {
    id: VC.uuid(),
    v: 1,
    type: 'login',
    title: '',
    fields: { username: '', password: '', totp: '' },
    urls: [],
    note: '',
    tags: [],
    favorite: false,
    createdAt: t,
    updatedAt: t,
    _deleted: false,
  }
}

/** 创建保险库：只在内存产出 PendingVault，落盘由 commitVault 在确认抄写后执行 */
export function createVault(masterPassword: string): Promise<PendingVault> {
  return VC.makeVault(masterPassword)
}

/** 确认抄写恢复码后，才把账户与空库落盘 */
export function commitVault(store: StorageAdapter, made: PendingVault): Account {
  setAccount(store, made.account)
  setItems(store, {})
  setRev(store, 0)
  return made.account
}

/** 解密全部条目；返回损坏的 id 列表（对应示例 decryptAll） */
export async function decryptAll(store: StorageAdapter, vk: Uint8Array): Promise<{ plain: PlainItems; broken: string[] }> {
  const items = getItems(store)
  const plain: PlainItems = {}
  const broken: string[] = []
  for (const id of Object.keys(items)) {
    const r = items[id]!
    if (!r || !r.ct) continue
    try {
      const p = (await VC.decryptJSON(vk, r)) as PlainItem
      p._deleted = !!r.deleted
      plain[id] = p
    } catch {
      broken.push(id)
    }
  }
  return { plain, broken }
}

/** 用主密码或恢复码解锁：校验密钥 + 解密全部 + 给出损坏清单 */
export async function unlock(store: StorageAdapter, secret: string, useRecovery: boolean): Promise<UnlockResult> {
  const a = getAccount(store)
  if (!a) throw new Error('未找到本地保险库')
  const vk = await VC.unwrap(secret, a, !!useRecovery)
  const { plain, broken } = await decryptAll(store, vk)
  return { vk, account: a, plain, broken }
}

/** 加密并写入一条条目（新增/编辑/收藏/恢复/软删共用） */
export async function saveItem(store: StorageAdapter, vk: Uint8Array, p: PlainItem): Promise<PlainItems> {
  const rec = await VC.encryptJSON(vk, p)
  const items = getItems(store)
  const stored: StoredItem = { id: p.id, rev: nextRev(store), iv: rec.iv, ct: rec.ct, deleted: !!p._deleted }
  items[p.id] = stored
  setItems(store, items)
  return { [p.id]: p }
}

/** 删除：purge=true 彻底删除，否则软删（进回收站）；软删会重加密以同步 _deleted */
export async function deleteItem(
  store: StorageAdapter,
  vk: Uint8Array,
  plain: PlainItems,
  id: string,
  purge: boolean,
): Promise<void> {
  const items = getItems(store)
  if (!items[id]) return
  const p = plain[id]
  if (purge) {
    delete items[id]
    delete plain[id]
  } else {
    items[id]!.deleted = true
    items[id]!.rev = nextRev(store)
    if (p) {
      p._deleted = true
      p.updatedAt = VC.now()
      const rec = await VC.encryptJSON(vk, p)
      items[id]!.iv = rec.iv
      items[id]!.ct = rec.ct
    }
  }
  setItems(store, items)
}

/** 从回收站恢复条目 */
export async function restoreItem(store: StorageAdapter, vk: Uint8Array, plain: PlainItems, id: string): Promise<void> {
  const items = getItems(store)
  if (!items[id]) return
  const p = plain[id]
  items[id]!.deleted = false
  items[id]!.rev = nextRev(store)
  if (p) {
    p._deleted = false
    p.updatedAt = VC.now()
    const rec = await VC.encryptJSON(vk, p)
    items[id]!.iv = rec.iv
    items[id]!.ct = rec.ct
  }
  setItems(store, items)
}

/** 构造加密备份文本（account + 全量密文 + rev） */
export function buildBackupText(store: StorageAdapter, account: Account): string {
  return VC.buildBackup(account, getItems(store), curRev(store))
}

/** 标记已导出备份（更新时间戳，便于 7 天提醒） */
export function markBackedUp(store: StorageAdapter, account: Account): Account {
  const a: Account = { ...account, lastBackupAt: VC.now() }
  setAccount(store, a)
  return a
}

export class BackupError extends Error {}

/** 应用备份；force=false 且本机已有库时抛 CONFIRM_OVERWRITE，由 UI 二次确认 */
export function applyBackup(store: StorageAdapter, text: string, force: boolean): Account {
  const d: BackupDoc = VC.parseBackup(text)
  const existing = getAccount(store)
  if (existing && !force) throw new BackupError('CONFIRM_OVERWRITE')
  setAccount(store, d.account)
  setItems(store, d.items || {})
  setRev(store, d.rev || 0)
  return d.account
}

/** 改主密码：只重新包裹同一把 vaultKey，条目密文不动 */
export async function changePassword(store: StorageAdapter, vk: Uint8Array, newPassword: string): Promise<Account> {
  const a = getAccount(store)
  if (!a) throw new Error('未找到本地保险库')
  const r = await VC.rewrap(vk, newPassword)
  const next: Account = { ...a, salt: r.salt, wrapped: r.wrapped }
  setAccount(store, next)
  return next
}

/** 重新生成恢复码：确认后才作废旧码 */
export async function refreshRecovery(vk: Uint8Array): Promise<{ code: string; recovery: Account['recovery'] }> {
  return VC.refreshRecovery(vk)
}

/** 应用新恢复码到账户 */
export function commitRecovery(store: StorageAdapter, recovery: Account['recovery']): Account {
  const a = getAccount(store)
  if (!a) throw new Error('未找到本地保险库')
  const next: Account = { ...a, recovery }
  setAccount(store, next)
  return next
}

/** 列表筛选 + 排序（对应示例 render 的过滤逻辑，纯函数便于测试） */
export function filterItems(
  plain: PlainItems,
  opts: { view: string; tag: string; filter: string },
): PlainItem[] {
  const all = Object.keys(plain).map((k) => plain[k]!)
  const f = opts.filter.toLowerCase()
  const list = all.filter((p) => {
    if (opts.view === 'trash') {
      if (!p._deleted) return false
    } else if (p._deleted) return false
    else if (opts.view === 'fav' && !p.favorite) return false
    else if (opts.view.indexOf('type:') === 0 && p.type !== opts.view.slice(5)) return false
    if (opts.tag && !(p.tags || []).includes(opts.tag)) return false
    if (!f) return true
    return [p.title, p.fields && p.fields.username, p.note, (p.urls || []).join(' '), (p.tags || []).join(' ')]
      .join(' ')
      .toLowerCase()
      .includes(f)
  })
  return list.sort((a, b) => (b.favorite ? 1 : 0) - (a.favorite ? 1 : 0) || (b.updatedAt || 0) - (a.updatedAt || 0))
}

/** 统计各视图计数（全部/收藏/回收站） */
export function viewCounts(plain: PlainItems): { all: number; fav: number; trash: number } {
  const all = Object.keys(plain).map((k) => plain[k]!)
  return {
    all: all.filter((p) => !p._deleted).length,
    fav: all.filter((p) => !p._deleted && p.favorite).length,
    trash: all.filter((p) => p._deleted).length,
  }
}

/** 类型重导出，供 composable 单一来源导入 */
export type { Account, PlainItem, PlainItems, Prefs, SealedRecord, StoredItem, StoredItems, PendingVault, UnlockResult }
export { LS }
