/**
 * Also Apps 门户 API 客户端。
 *
 * 设计要点：
 *  1. 所有应用展示数据来自后端 /v1/portal/*，前端零硬编码应用列表——
 *     管理员在后台新增应用后无需重新构建前端。
 *  2. 身份头由 Logto 提供：Authorization: Bearer <access_token>；
 *     passthrough/dev 阶段同时发 X-User-Sub，切到 logto 后后端以 token 为准。
 *  3. 不重定向登录：401 由调用方决定（跳 Logto 并带回跳意图）。
 *  4. 超时 + 错误摊平：网络异常转成可展示的 PortalApiError，不泄漏内部细节。
 */

import { apiConfigured, cloudConfig } from '@/config.ts'
import { currentAccessToken, currentSub } from '@/services/auth/logto.ts'

export interface PortalApp {
  id: string
  code: string
  name: string
  subtitle: string
  description: string
  detail: string
  icon_url: string
  cover_url: string
  launch_url: string
  app_type: 'application' | 'tool' | 'game' | 'service'
  open_mode: 'same_tab' | 'new_tab'
  status: 'draft' | 'published' | 'disabled'
  visibility: 'public' | 'private'
  auth_required: boolean
  is_featured: boolean
  show_on_home: boolean
  is_new: boolean
  sort_order: number
  published_at: string | null
  categories: string[]
  created_at: string
  updated_at: string
  favorited?: boolean
  sort_order_user?: number
  last_visited_at?: string
  visit_count?: number
}

export interface PortalCategory {
  id: string
  code: string
  name: string
  description: string
  icon: string
  parent_id: string | null
  sort_order: number
  status: string
}

export interface AppListResult {
  items: PortalApp[]
  total: number
  page: number
  page_size: number
}

export interface LaunchCheck {
  allowed: boolean
  reason: 'LOGIN_REQUIRED' | 'NOT_DEPLOYED' | 'APP_FORBIDDEN' | null
  message: string
  app: PortalApp
  url?: string
  open_mode?: 'same_tab' | 'new_tab'
}

export class PortalApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
  ) {
    super(message)
    this.name = 'PortalApiError'
  }
}

async function authHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = await currentAccessToken().catch(() => null)
  if (token) headers.Authorization = `Bearer ${token}`
  const sub = await currentSub().catch(() => null)
  if (sub) headers['X-User-Sub'] = sub
  return headers
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!apiConfigured()) throw new PortalApiError('后端 API 未配置', 0, 'API_NOT_CONFIGURED')
  const base = cloudConfig().apiBase
  const url = `${base}${path}`
  let res: Response
  try {
    res = await fetch(url, {
      ...init,
      headers: { ...(await authHeaders()), ...(init.headers ?? {}) },
      signal: AbortSignal.timeout(15000),
    })
  } catch {
    // 不把原始网络异常的堆栈透出到 UI，仅保留稳定的机器可读码
    throw new PortalApiError('网络请求失败，请稍后重试', 0, 'NETWORK_ERROR')
  }
  const body = await res.json().catch(() => ({})) as Record<string, unknown>
  if (!res.ok) {
    throw new PortalApiError(
      String(body.message ?? '请求失败'),
      res.status,
      String(body.error ?? 'HTTP_ERROR'),
    )
  }
  return body as T
}

function jsonBody(value: unknown): RequestInit {
  return { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) }
}

// --------------------------------------------------------------------------- 公开目录
export function listApps(params: {
  category?: string
  keyword?: string
  featured?: boolean
  home?: boolean
  page?: number
  pageSize?: number
} = {}): Promise<AppListResult> {
  const q = new URLSearchParams()
  if (params.category) q.set('category', params.category)
  if (params.keyword) q.set('keyword', params.keyword)
  if (params.featured) q.set('featured', 'true')
  if (params.home) q.set('home', 'true')
  if (params.page) q.set('page', String(params.page))
  if (params.pageSize) q.set('page_size', String(params.pageSize))
  const suffix = q.toString() ? `?${q}` : ''
  return request<AppListResult>(`/v1/portal/apps${suffix}`)
}

export function listFeatured(): Promise<{ items: PortalApp[]; total: number }> {
  return request('/v1/portal/apps/featured')
}

export function searchApps(q: string, category = ''): Promise<{ items: PortalApp[]; total: number }> {
  const params = new URLSearchParams()
  if (q) params.set('q', q)
  if (category) params.set('category', category)
  return request(`/v1/portal/apps/search?${params}`)
}

export function getApp(code: string): Promise<PortalApp & { favorited: boolean }> {
  return request(`/v1/portal/apps/${encodeURIComponent(code)}`)
}

export function listCategories(): Promise<{ items: PortalCategory[]; total: number }> {
  return request('/v1/portal/categories')
}

export function checkLaunch(code: string): Promise<LaunchCheck> {
  return request(`/v1/portal/apps/${encodeURIComponent(code)}/launch`, { method: 'POST' })
}

// --------------------------------------------------------------------------- 用户功能
export function listFavorites(): Promise<{ items: PortalApp[]; total: number }> {
  return request('/v1/portal/me/favorites')
}

export function addFavorite(appId: string): Promise<{ ok: boolean }> {
  return request(`/v1/portal/me/favorites/${encodeURIComponent(appId)}`, { method: 'POST' })
}

export function removeFavorite(appId: string): Promise<{ ok: boolean }> {
  return request(`/v1/portal/me/favorites/${encodeURIComponent(appId)}`, { method: 'DELETE' })
}

export function reorderFavorites(appIds: string[]): Promise<{ items: PortalApp[] }> {
  return request('/v1/portal/me/favorites/order', {
    method: 'PUT',
    ...jsonBody({ app_ids: appIds }),
  })
}

export function listRecent(limit = 10): Promise<{ items: PortalApp[]; total: number }> {
  return request(`/v1/portal/me/recent?limit=${limit}`)
}

export function recordVisit(appId: string): Promise<{ ok: boolean }> {
  return request(`/v1/portal/me/recent/${encodeURIComponent(appId)}`, { method: 'POST' })
}
