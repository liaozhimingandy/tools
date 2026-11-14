/**
 * 锦囊 SafeKeep 的数据契约。
 * 与示例 index.html 的 VC / 存储结构保持字段级一致，保证备份格式向后兼容。
 */

/** AES-GCM 密封记录：iv 与 ct 均为 base64 文本 */
export interface SealedRecord {
  iv: string
  ct: string
}

export interface KdfSpec {
  alg: string
  iterations: number
}

/** 恢复码包裹块（复用 SealedRecord 的 iv/ct，额外带独立 salt） */
export interface RecoveryBlock {
  salt: string
  iv: string
  ct: string
}

/**
 * 账户记录：只含被主密码/恢复码包裹的密钥，绝不含 vaultKey 明文。
 * 存储键 sk.account。
 */
export interface Account {
  v: number
  app: 'safekeep-local'
  mode: 'local'
  createdAt: number
  salt: string
  kdf: KdfSpec
  wrapped: SealedRecord
  recovery: RecoveryBlock
  lastBackupAt: number | null
}

export type ItemType = 'login' | 'note' | 'card' | 'apikey'

export interface ItemFields {
  username?: string
  password?: string
  totp?: string
  [key: string]: string | undefined
}

/** 明文条目，仅在内存存在；整条序列化后加密，元数据不外泄 */
export interface PlainItem {
  id: string
  v: number
  type: ItemType
  title: string
  fields: ItemFields
  urls: string[]
  note: string
  tags: string[]
  favorite: boolean
  createdAt: number
  updatedAt: number
  _deleted: boolean
}

/** 存储中的条目：只有密文 + 非敏感元数据 */
export interface StoredItem {
  id: string
  rev: number
  iv: string
  ct: string
  deleted: boolean
}

export type StoredItems = Record<string, StoredItem>
export type PlainItems = Record<string, PlainItem>

/** 非敏感偏好，明文存储 */
export interface Prefs {
  /** 自动锁定方式：leave=离开页面即锁定（默认）；idle=空闲超时锁定；both=两者都启用 */
  lockMode: 'leave' | 'idle' | 'both'
  /** 空闲超时时长（毫秒）；lockMode 为 idle/both 时生效，0 表示不设超时 */
  idleMs: number
  clipSec: number
}

/** 加密备份文件结构 */
export interface BackupDoc {
  app: 'safekeep-backup'
  v: number
  exportedAt: number
  account: Account
  rev: number
  items: StoredItems
}

export interface PasswordOptions {
  length?: number
  phrase?: boolean
  upper?: boolean
  lower?: boolean
  digits?: boolean
  symbols?: boolean
  exclude?: boolean
}

export interface GeneratedPassword {
  value: string
  entropy: number
  charset: number
}

export interface HealthResult {
  total: number
  withPw: number
  weak: number
  reused: number
  old: number
  score: number
  weakItems: PlainItem[]
  reuseItems: PlainItem[]
  oldItems: PlainItem[]
}

/** makeVault 的内存结果：确认抄写恢复码前绝不落盘 */
export interface PendingVault {
  account: Account
  recoveryCode: string
  vk: Uint8Array
}

export interface UnlockResult {
  vk: Uint8Array
  account: Account
  plain: PlainItems
  broken: string[]
}
