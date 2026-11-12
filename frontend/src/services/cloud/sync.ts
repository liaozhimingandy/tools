/**
 * 零知识同步的纯逻辑层（无 DOM / 无网络 / 无 Vue，可在 Node 直接测试）。
 *
 * 职责：
 *  1. buildCloudBlob：把本地密封结构打包成不透明 blob（绝不含明文/密钥）；
 *  2. parseCloudBlob：严格校验远端 blob 结构，防云端被污染后污染本地库；
 *  3. decidePush / decidePull：跨设备冲突判据（基于后端 revision 与本地逻辑时钟 rev）；
 *  4. applyCloudBlob / snapshotLocal：远端↔本地落盘（经 StorageAdapter）。
 *
 * 版本语义（两个正交时钟，切勿混淆）：
 *  - 后端 revision：整条云端记录的乐观锁版本，每次 PUT +1，CAS 用；
 *  - blob.rev / 本地 sk.rev：条目级逻辑时钟，跨设备判断「谁的条目变更更多」。
 * 冲突策略刻意保守：不做自动合并，任何覆盖都需 UI 二次确认，避免静默丢数据。
 */
import type { StorageAdapter } from '../safekeep/storage.ts'
import {
  curRev, getAccount, getItems, setAccount, setItems, setRev,
} from '../safekeep/storage.ts'
import type { Account, StoredItems } from '../safekeep/types.ts'
import {
  CLOUD_FORMAT, CLOUD_SCHEMA, type CloudVaultBlob, type RemoteSummary,
} from './types.ts'

export class BlobError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'BlobError'
  }
}

/** 把本地密封结构打包成云端不透明 blob。明文条目不参与，只搬密文。 */
export function buildCloudBlob(
  account: Account,
  items: StoredItems,
  rev: number,
  savedAt: number = Date.now(),
): CloudVaultBlob {
  return {
    fmt: CLOUD_FORMAT,
    schema: CLOUD_SCHEMA,
    savedAt,
    rev,
    // 结构化拷贝，避免后续本地内存改动意外影响待上传对象
    account: JSON.parse(JSON.stringify(account)) as Account,
    items: JSON.parse(JSON.stringify(items)) as StoredItems,
  }
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === 'object' && !Array.isArray(v)
}

/** 严格校验远端 blob：结构损坏 / 版本不兼容 / 混入明文一律拒绝，绝不写进本地库。 */
export function parseCloudBlob(value: unknown): CloudVaultBlob {
  if (!isPlainObject(value)) throw new BlobError('云端数据不是对象')
  if (value.fmt !== CLOUD_FORMAT) throw new BlobError('不是锦囊的云端数据格式')
  if (value.schema !== CLOUD_SCHEMA) {
    throw new BlobError(`云端数据版本不兼容（schema=${String(value.schema)}）`)
  }
  if (!Number.isSafeInteger(value.rev) || (value.rev as number) < 0) {
    throw new BlobError('云端逻辑时钟 rev 非法')
  }
  if (!Number.isSafeInteger(value.savedAt)) throw new BlobError('云端保存时间非法')
  const a = value.account
  if (!isPlainObject(a) || a.app !== 'safekeep-local' || !a.wrapped || !a.salt || !a.kdf || !a.recovery) {
    throw new BlobError('云端账户密封结构损坏')
  }
  const items = value.items
  if (!isPlainObject(items)) throw new BlobError('云端条目集合损坏')
  for (const [id, raw] of Object.entries(items)) {
    if (!isPlainObject(raw)) throw new BlobError(`条目 ${id} 结构损坏`)
    if (typeof raw.iv !== 'string' || typeof raw.ct !== 'string') {
      throw new BlobError(`条目 ${id} 缺少密文字段`)
    }
  }
  return {
    fmt: CLOUD_FORMAT,
    schema: value.schema,
    savedAt: value.savedAt as number,
    rev: value.rev as number,
    account: a as unknown as Account,
    items: items as unknown as StoredItems,
  }
}

export type PushDecision =
  | { kind: 'create' }                 // 云端无此记录，expected_revision=0
  | { kind: 'update'; base: number }   // 与上次同步版本一致，可 CAS 更新
  | { kind: 'stale'; remote: number; local: number } // 云端被其他端更新过，须先拉取

/**
 * 上传前判据：用「上次成功同步时记录的后端 revision」判断云端是否被别的设备改过。
 * localCloudRev=0 且云端有记录 => stale（本机从未同步，不能盲目覆盖）。
 */
export function decidePush(
  remoteRevision: number | null,
  localCloudRevision: number,
): PushDecision {
  if (remoteRevision === null) return { kind: 'create' }
  if (remoteRevision === localCloudRevision) return { kind: 'update', base: remoteRevision }
  return { kind: 'stale', remote: remoteRevision, local: localCloudRevision }
}

/** CAS 冲突后是否允许「强制覆盖」：force 时以当前远端 revision 为 base 重试。 */
export function forcePushBase(remoteRevision: number): number {
  return remoteRevision
}

export type PullDecision =
  | { kind: 'up-to-date' }   // 两端逻辑时钟一致
  | { kind: 'apply' }        // 云端更新，可应用
  | { kind: 'older' }        // 云端比本地旧，应用会回退，须显式确认

/** 下载前判据：比较 blob.rev 与本地 sk.rev（条目级逻辑时钟）。 */
export function decidePull(remoteRev: number, localRev: number): PullDecision {
  if (remoteRev === localRev) return { kind: 'up-to-date' }
  if (remoteRev < localRev) return { kind: 'older' }
  return { kind: 'apply' }
}

/** 远端 blob 覆盖本地（解锁态下主密码不变，条目密文原样写回）。 */
export function applyCloudBlob(store: StorageAdapter, blob: CloudVaultBlob): Account {
  setAccount(store, blob.account)
  setItems(store, blob.items)
  setRev(store, blob.rev)
  return blob.account
}

/** 采集本地密封结构快照，用于生成远端摘要前的对比（不返回明文）。 */
export function snapshotLocal(store: StorageAdapter): { rev: number; itemCount: number; hasAccount: boolean } {
  return {
    rev: curRev(store),
    itemCount: Object.keys(getItems(store)).length,
    hasAccount: !!getAccount(store),
  }
}

/** 由远端记录生成 UI 摘要。 */
export function toRemoteSummary(
  exists: boolean,
  blob: CloudVaultBlob | null,
  meta: { revision: number; updatedAt: string; device: string | null } | null,
): RemoteSummary {
  if (!exists || !blob || !meta) {
    return {
      exists: false, revision: 0, blobRev: 0, itemCount: 0,
      updatedAt: '', device: null, savedAt: 0,
    }
  }
  return {
    exists: true,
    revision: meta.revision,
    blobRev: blob.rev,
    itemCount: Object.keys(blob.items).length,
    updatedAt: meta.updatedAt,
    device: meta.device,
    savedAt: blob.savedAt,
  }
}
