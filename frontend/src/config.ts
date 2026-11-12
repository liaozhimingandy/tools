/**
 * 前端构建期配置（VITE_* 环境变量在 `vite build` 时内联进产物）。
 *
 * 所有部署差异（API 地址、Logto 租户、公网 base）都在这里集中读取并做校验，
 * 业务代码不要直接散读 import.meta.env，便于统一处理「未配置 = 降级」。
 *
 * 关键契约（本轮起把「能否登录」与「能否云端同步」解耦）：
 *  - logtoEnabled()    = endpoint + appId + redirectUri 齐全 => 可以走 Logto 登录；
 *  - apiConfigured()   = 有 VITE_API_BASE_URL（缺省回退 DEFAULT_API_BASE_URL）=> 后端云端地址就绪；
 *  - cloudEnabled()    = 两者都齐                            => 完整云端同步可用。
 *  这样即使后端地址还没填，用户也能先登录、看到账号态；点云端恢复时得到
 *  「后端地址未配置」的可操作提示，而不是被一个总开关整体隐藏。
 *
 * Logto 配置内联默认值说明：
 *  - endpoint / appId 是 OAuth2 的**公开客户端标识**（Public Client），设计上本就
 *    暴露在浏览器里（官方集成示例也是明文写在前端），不是密钥，故内联为默认值，
 *    让部署开箱可登录；若要换租户，仍可用 VITE_LOGTO_* 覆盖，无需改代码。
 *  - appSecret 一律不进前端（本应用是 PKCE 公共客户端，无 secret）。
 *
 * Node 安全：import.meta.env 在 Node 单测里不存在，统一经 ENV 守卫读取，
 * 使 client/sync/config 等纯逻辑可在 node --test 下直接 import。
 */

/** 构建期环境变量快照；Node 下为空对象（用 as 断言补齐 Vite 注入的内置键）。 */
const ENV = ((import.meta as unknown as { env?: ImportMetaEnv }).env ?? {}) as ImportMetaEnv

/** Logto 公开客户端配置默认值（可被 VITE_LOGTO_* 覆盖）。非密钥。 */
export const DEFAULT_LOGTO_ENDPOINT = 'https://account.alsoapp.com'
export const DEFAULT_LOGTO_APP_ID = '0z2t6jrnf4z9lzy4miusg'
/** 后端 API 根默认值（可被 VITE_API_BASE_URL 覆盖）。非密钥，内联为默认值开箱即用。 */
export const DEFAULT_API_BASE_URL = 'https://api-tools.alsoapp.com'

/** 运行时公网基路径（Vite 已注入；hash 路由下 hash 前的前缀，如 /tools/）。 */
export const PUBLIC_BASE: string = ENV.BASE_URL || '/'

export interface CloudConfig {
  /** API 根，如 https://api.example.com（不含尾斜杠）。空 = 未启用。 */
  apiBase: string
}

export interface LogtoConfig {
  enabled: boolean
  /** Logto endpoint，如 https://tenant.logto.app（无尾斜杠） */
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

/** 构造不带尾斜杠的 API 根（未注入 VITE_API_BASE_URL 时回退 DEFAULT_API_BASE_URL）。 */
function apiBase(): string {
  return trim(ENV.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/+$/, '')
}

/** 后端云端地址是否已配置（与 Logto 登录解耦）。 */
export function apiConfigured(): boolean {
  return !!apiBase()
}

export function cloudConfig(): CloudConfig {
  return { apiBase: apiBase() }
}

/** 是否具备「走 Logto 登录」的全部条件（不要求后端 API 已配）。 */
export function logtoEnabled(): boolean {
  return logtoConfig().enabled
}

/** 是否具备启用云端同步的全部条件（API 地址 + Logto 三件套）。 */
export function cloudEnabled(): boolean {
  return apiConfigured() && logtoEnabled()
}

/**
 * 纯解析函数（可注入 env / origin，便于 Node 单测，不依赖 import.meta 与 window）。
 * 生产走下方的 logtoConfig()；测试直接喂 deps 覆盖默认值与回调拼装。
 */
export function resolveLogtoConfig(
  env: Partial<ImportMetaEnv> = {},
  origin: string = '',
): LogtoConfig {
  const endpoint = (trim(env.VITE_LOGTO_ENDPOINT) || DEFAULT_LOGTO_ENDPOINT).replace(/\/+$/, '')
  const appId = trim(env.VITE_LOGTO_APP_ID) || DEFAULT_LOGTO_APP_ID
  const rawRedirect = trim(env.VITE_LOGTO_REDIRECT_URI)
  let redirectUri = rawRedirect
  if (!redirectUri && origin) {
    const publicBase = trim(env.BASE_URL) || '/'
    redirectUri = new URL(publicBase, origin).toString().replace(/\/?$/, '/')
  }
  const postLogoutRedirectUri = trim(env.VITE_LOGTO_POST_LOGOUT_REDIRECT_URI) || redirectUri
  const resource = trim(env.VITE_LOGTO_RESOURCE)
  const rawScopes = trim(env.VITE_LOGTO_SCOPES)
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

export function logtoConfig(): LogtoConfig {
  const origin = typeof window === 'undefined'
    ? ''
    : window.location.origin
  return resolveLogtoConfig(ENV, origin)
}
