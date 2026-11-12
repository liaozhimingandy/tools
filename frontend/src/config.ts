/**
 * 前端构建期配置（VITE_* 环境变量在 `vite build` 时内联进产物）。
 *
 * 所有部署差异（API 地址、Logto 租户、公网 base）都在这里集中读取并做校验，
 * 业务代码不要直接散读 import.meta.env，便于统一处理「未配置 = 降级」。
 *
 * 关键契约：
 *  - VITE_API_BASE_URL 为空 => 云端同步不可用，锦囊保持纯本地（绝不白屏）；
 *  - VITE_LOGTO_* 未配齐 => Logto 登录不可用，同样降级为纯本地；
 *  - 两者都配齐才启用「登录后云端同步」完整链路。
 *
 * Node 安全：import.meta.env 在 Node 单测里不存在，统一经 ENV 守卫读取，
 * 使 client/sync 等纯逻辑可在 node --test 下直接 import。
 */

/** 构建期环境变量快照；Node 下为空对象（用 as 断言补齐 Vite 注入的内置键）。 */
const ENV = ((import.meta as unknown as { env?: ImportMetaEnv }).env ?? {}) as ImportMetaEnv

/** 运行时公网基路径（Vite 已注入；hash 路由下 hash 前的前缀，如 /tools/）。 */
export const PUBLIC_BASE: string = ENV.BASE_URL || '/'

export interface CloudConfig {
  /** API 根，如 https://api.example.com（不含尾斜杠）。空 = 未启用。 */
  apiBase: string
}

export interface LogtoConfig {
  enabled: boolean
  /** Logto endpoint，如 https://tenant.logto.app */
  endpoint: string
  appId: string
  /** 需要访问的 API resource（可选；用于拿 access token 的 audience） */
  resource: string
  /** 回调地址，必须是 OAuth redirect_uri 白名单里的「无 fragment」绝对地址 */
  redirectUri: string
  /** 登出回跳地址 */
  postLogoutRedirectUri: string
  scopes: string[]
}

function trim(v: string | undefined): string {
  return (v ?? '').trim()
}

/** 构造不带尾斜杠的 API 根。 */
function apiBase(): string {
  return trim(ENV.VITE_API_BASE_URL).replace(/\/+$/, '')
}

export function cloudConfig(): CloudConfig {
  return { apiBase: apiBase() }
}

/** 是否具备启用云端同步的全部条件（API 地址 + Logto 三件套）。 */
export function cloudEnabled(): boolean {
  return !!apiBase() && logtoConfig().enabled
}

/**
 * 回调地址拼装：部署在 GitHub Pages 子路径时，redirect_uri 落到站点根 index.html，
 * Logto 携带 ?code=&state= 回来；hash 路由保证不带 #，符合 OAuth 规范。
 */
function buildRedirectUri(raw: string): string {
  const value = trim(raw)
  if (value) return value
  if (typeof window === 'undefined') return ''
  const base = new URL(PUBLIC_BASE, window.location.origin).toString()
  return base.replace(/\/?$/, '/')
}

export function logtoConfig(): LogtoConfig {
  const endpoint = trim(ENV.VITE_LOGTO_ENDPOINT).replace(/\/+$/, '')
  const appId = trim(ENV.VITE_LOGTO_APP_ID)
  const redirectUri = buildRedirectUri(trim(ENV.VITE_LOGTO_REDIRECT_URI))
  const postLogoutRedirectUri =
    trim(ENV.VITE_LOGTO_POST_LOGOUT_REDIRECT_URI) || redirectUri
  const resource = trim(ENV.VITE_LOGTO_RESOURCE)
  const rawScopes = trim(ENV.VITE_LOGTO_SCOPES)
  const scopes = rawScopes
    ? rawScopes.split(',').map((s) => s.trim()).filter(Boolean)
    : []
  return {
    enabled: !!endpoint && !!appId && !!redirectUri,
    endpoint,
    appId,
    resource,
    redirectUri,
    postLogoutRedirectUri,
    scopes,
  }
}
