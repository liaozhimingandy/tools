/** 门户管理 API 客户端：所有请求复用公开的 authHeaders（Bearer + X-User-Sub）。 */
import type { PortalApp, PortalCategory } from './api.ts'
import { PortalApiError } from './api.ts'
import { apiConfigured, cloudConfig } from '@/config.ts'
import { currentAccessToken, currentSub } from '@/services/auth/logto.ts'

async function adminRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!apiConfigured()) throw new PortalApiError('后端 API 未配置', 0, 'API_NOT_CONFIGURED')
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(init.headers as Record<string, string> | undefined),
  }
  const token = await currentAccessToken().catch(() => null)
  if (token) headers.Authorization = `Bearer ${token}`
  const sub = await currentSub().catch(() => null)
  if (sub) headers['X-User-Sub'] = sub

  const res = await fetch(`${cloudConfig().apiBase}${path}`, {
    ...init,
    headers,
    signal: AbortSignal.timeout(15000),
  })
  const body = await res.json().catch(() => ({})) as Record<string, unknown>
  if (!res.ok) {
    throw new PortalApiError(
      String(body.message ?? '请求失败'), res.status, String(body.error ?? 'HTTP_ERROR'),
    )
  }
  return body as T
}

function json(value: unknown): RequestInit {
  return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) }
}

/** 表单用类型：所有字段必填（reactive 表单需要确定的形状，避免 optional 导致 v-model 推断歧义）。 */
export interface AppForm {
  code: string
  name: string
  subtitle: string
  description: string
  detail: string
  icon_url: string
  cover_url: string
  launch_url: string
  app_type: string
  open_mode: string
  status: string
  visibility: string
  auth_required: boolean
  is_featured: boolean
  show_on_home: boolean
  is_new: boolean
  sort_order: number
  categories: string[]
}

export type AppPayload = Partial<AppForm> & Pick<AppForm, 'name'>

export const adminApi = {
  listApps: () => adminRequest<{ items: PortalApp[]; total: number }>('/v1/portal/admin/apps'),
  getApp: (id: string) => adminRequest<{ app: PortalApp }>(`/v1/portal/admin/apps/${encodeURIComponent(id)}`),
  createApp: (payload: AppPayload) => adminRequest<{ app: PortalApp }>('/v1/portal/admin/apps', json(payload)),
  updateApp: (id: string, payload: Partial<AppPayload>) => adminRequest<{ app: PortalApp }>(
    `/v1/portal/admin/apps/${encodeURIComponent(id)}`,
    { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) },
  ),
  deleteApp: (id: string) => adminRequest<{ ok: boolean }>(`/v1/portal/admin/apps/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  publish: (id: string) => adminRequest<{ app: PortalApp }>(`/v1/portal/admin/apps/${encodeURIComponent(id)}/publish`, { method: 'POST' }),
  disable: (id: string) => adminRequest<{ app: PortalApp }>(`/v1/portal/admin/apps/${encodeURIComponent(id)}/disable`, { method: 'POST' }),
  listCategories: () => adminRequest<{ items: PortalCategory[] }>('/v1/portal/admin/categories'),
  createCategory: (payload: { code: string; name: string; description?: string; icon?: string; sort_order?: number }) =>
    adminRequest<{ category: PortalCategory }>('/v1/portal/admin/categories', json(payload)),
  updateCategory: (id: string, payload: Partial<PortalCategory>) => adminRequest<{ category: PortalCategory }>(
    `/v1/portal/admin/categories/${encodeURIComponent(id)}`,
    { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) },
  ),
  deleteCategory: (id: string) => adminRequest<{ ok: boolean }>(
    `/v1/portal/admin/categories/${encodeURIComponent(id)}`, { method: 'DELETE' },
  ),
  setHomepage: (items: Array<{ id: string; show_on_home?: boolean; is_featured?: boolean; sort_order?: number }>) =>
    adminRequest<{ ok: boolean }>(
      '/v1/portal/admin/homepage',
      { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ items }) },
    ),
}
