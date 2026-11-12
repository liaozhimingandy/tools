/**
 * 云端同步的数据契约（零知识边界）。
 *
 * 云端 `tool_configs.value` 只保存与「加密备份文件」同构的密封结构：
 *   - account：含被主密码/恢复码包裹的 wrapped/recovery（密文），无 vaultKey 明文；
 *   - items：每条的 {iv, ct, deleted, rev}，ct 为 AES-256-GCM 密文；
 *   - rev：条目级逻辑时钟（正整数），用于跨设备判断新旧，与后端 revision 正交。
 * 主密码、恢复码明文、vaultKey 绝不进入本结构，也不上网。
 */
import type { Account, StoredItems } from '../safekeep/types.ts'

export const CLOUD_FORMAT = 'safekeep-vault' as const
export const CLOUD_SCHEMA = 1 as const

export interface CloudVaultBlob {
  fmt: typeof CLOUD_FORMAT
  schema: number
  /** 上传时刻（毫秒），仅用于展示「云端最近保存时间」 */
  savedAt: number
  /** 条目级逻辑时钟，对应本地 sk.rev */
  rev: number
  account: Account
  items: StoredItems
}

/** 云端一条记录的同步元信息（由后端 revision 派生，不含明文）。 */
export interface RemoteVault {
  /** 后端乐观锁版本，PUT 时作为 expected_revision */
  revision: number
  /** 后端 updated_at（ISO 字符串） */
  updatedAt: string
  /** 写入设备标识（明文元数据，可选） */
  device: string | null
  blob: CloudVaultBlob
}

/** 供 UI 展示的云端摘要（拉取前确认用）。 */
export interface RemoteSummary {
  exists: boolean
  revision: number
  blobRev: number
  itemCount: number
  updatedAt: string
  device: string | null
  savedAt: number
}
