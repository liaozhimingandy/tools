/**
 * 公共配置表 HTTP 客户端（零知识同步的网络层）。
 *
 * 契约（对齐后端 /api/v1/configs/{tool_id}/{key}）：
 *  - 身份：X-User-Sub 头 = 前端 Logto 登录拿到的 sub；本阶段后端 passthrough 不校验签名，
 *    但前端「有登录信息才构造客户端」，作为软门禁。切 logto 模式时后端自行校验 Bearer。
 *  - value：不透明密文 blob，本层不解析、不记录内容。
 *  - 乐观锁：PUT 带 expected_revision（首次 0），409 视为冲突交给上层判定。
 *
 * 依赖倒置：fetch 可注入，便于 Node 单测（不依赖真实网络/DOM）。
 */
import { cloudConfig } from '../../config.ts'
import type { CloudVaultBlob, RemoteVault } from './types.ts'
import { parseCloudBlob } from './sync.ts'

export const TOOL_ID = 'safekeep'
export const VAULT_KEY = 'vault'

export class CloudError extends Error {
  readonly code: string
  readonly status: number
  readonly detail?: { expected: number; actual: number }

  constructor(
    message: string,
    code: string,
    status: number,
    detail?: { expected: number; actual: number },
  ) {
    super(message)
    this.name = 'CloudError'
    this.code = code
    this.status = status
    this.detail = detail
  }
}

export interface CloudClientOptions {
  /** 登录用户的 sub（Logto claims.sub），作为归属隔离维度 */
  userSub: string
  /** access token 提供函数；本阶段后端不校验，但保留以便无缝切 logto 模式 */
  getToken?: () => Promise<string | null>
  /** 设备标识（明文元数据，<=128 字符） */
  device?: string
  /** 注入 fetch（测试用），默认用全局 */
  fetchImpl?: typeof globalThis.fetch
  /** 显式 API 根（测试用）；不传则读 VITE_API_BASE_URL */
  base?: string
}

interface RecordResponse {
  value: unknown
  revision: number
  updated_at: string
  updated_by_device: string | null
  etag?: string
}

function endpoint(opts: CloudClientOptions): string {
  const apiBase = (opts.base ?? cloudConfig().apiBase).replace(/\/+$/, '')
  if (!apiBase) {
    throw new CloudError('云端同步未启用（缺少 VITE_API_BASE_URL）', 'NOT_CONFIGURED', 0)
  }
  return `${apiBase}/api/v1/configs/${TOOL_ID}/${VAULT_KEY}`
}

async function headers(opts: CloudClientOptions): Promise<Record<string, string>> {
  const h: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-User-Sub': opts.userSub,
  }
  if (opts.getToken) {
    try {
      const token = await opts.getToken()
      if (token) h.Authorization = `Bearer ${token}`
    } catch {
      /* token 获取失败不阻断：本阶段后端 passthrough 不校验 */
    }
  }
  return h
}

function doFetch(opts: CloudClientOptions): typeof globalThis.fetch {
  return opts.fetchImpl ?? globalThis.fetch.bind(globalThis)
}

/** 解析统一错误响应体 {error, message, detail}。不含 value 内容。 */
async function toCloudError(resp: Response): Promise<CloudError> {
  let code = 'HTTP_ERROR'
  let message = `请求失败（${resp.status}）`
  let detail: { expected: number; actual: number } | undefined
  try {
    const body = (await resp.json()) as { error?: string; message?: string; detail?: Record<string, unknown> }
    if (body.error) code = body.error
    if (body.message) message = body.message
    if (body.detail && typeof body.detail.actual === 'number') {
      detail = { expected: Number(body.detail.expected), actual: Number(body.detail.actual) }
    }
  } catch {
    /* 非 JSON 错误体，用默认 */
  }
  return new CloudError(message, code, resp.status, detail)
}

/** 拉取云端记录；不存在返回 null。 */
export async function fetchVault(opts: CloudClientOptions): Promise<RemoteVault | null> {
  const resp = await doFetch(opts)(endpoint(opts), {
    method: 'GET',
    headers: await headers(opts),
  })
  if (resp.status === 404) return null
  if (!resp.ok) throw await toCloudError(resp)
  const rec = (await resp.json()) as RecordResponse
  const blob = parseCloudBlob(rec.value) // 严格校验，污染数据不进内存
  return {
    revision: rec.revision,
    updatedAt: rec.updated_at,
    device: rec.updated_by_device,
    blob,
  }
}

/** 仅取远端 revision（上传前判重用），不下载整块 blob，省带宽。 */
export async function fetchRevision(opts: CloudClientOptions): Promise<number | null> {
  const resp = await doFetch(opts)(endpoint(opts), {
    method: 'GET',
    headers: await headers(opts),
  })
  if (resp.status === 404) return null
  if (!resp.ok) throw await toCloudError(resp)
  const rec = (await resp.json()) as RecordResponse
  return rec.revision
}

export interface PutResult {
  revision: number
  updatedAt: string
}

/** 上传（UPSERT）。expected_revision=0 表示仅首次创建。409 由上层处理。 */
export async function putVault(
  opts: CloudClientOptions,
  blob: CloudVaultBlob,
  expectedRevision: number,
): Promise<PutResult> {
  const resp = await doFetch(opts)(endpoint(opts), {
    method: 'PUT',
    headers: await headers(opts),
    body: JSON.stringify({
      value: blob,
      expected_revision: expectedRevision,
      schema_version: blob.schema,
      updated_by_device: opts.device ?? null,
    }),
  })
  if (!resp.ok) throw await toCloudError(resp)
  const rec = (await resp.json()) as RecordResponse
  return { revision: rec.revision, updatedAt: rec.updated_at }
}
