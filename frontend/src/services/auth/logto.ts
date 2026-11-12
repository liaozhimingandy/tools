/**
 * Logto 登录态封装（@logto/browser 3.1.2）。
 *
 * 设计要点：
 *  1. 未配置（VITE_LOGTO_ENDPOINT / APP_ID 缺失）时全部降级为空操作，
 *     绝不 new LogtoClient、绝不跳转，保证 Pages 上纯本地模式照常可用、不白屏。
 *  2. OAuth 回调落在站点根（如 /tools/?code=..&state=..），无 fragment，符合规范。
 *     hash 路由下 window.location.href 形如 .../tools/?code=..#/safekeep，
 *     SDK 用 full href 消费 code/state；成功后清理 query，避免刷新重复处理。
 *  3. 只向业务层暴露 sub / accessToken / isAuthenticated，不触碰主密码与 vaultKey。
 */
import LogtoClient from '@logto/browser'
import { logtoConfig, type LogtoConfig } from '@/config.ts'

let client: LogtoClient | null = null
/** main.ts 在挂载前 initAuth() 的结果缓存，供各视图同步读取初始登录态。 */
let lastAuthState: AuthState | null = null

function cfg(): LogtoConfig {
  return logtoConfig()
}

/** 同步读取最近一次 initAuth 的登录态（挂载前已就绪），避免视图重复走回调逻辑。 */
export function cachedAuthState(): AuthState | null {
  return lastAuthState
}

/** 惰性构造客户端；未配置返回 null（降级信号）。 */
function getClient(): LogtoClient | null {
  if (!cfg().enabled) return null
  if (client === null) {
    const c = cfg()
    client = new LogtoClient(
      {
        endpoint: c.endpoint,
        appId: c.appId,
        resources: c.resource ? [c.resource] : [],
        scopes: c.scopes,
        requestTimeoutMs: 10000,
      },
      true, // enableCache：sessionStorage 缓存 discovery，减少重复请求
    )
  }
  return client
}

export interface AuthState {
  configured: boolean
  authenticated: boolean
  sub: string | null
}

/** 是否配置了可用的 Logto 登录。 */
export function isConfigured(): boolean {
  return cfg().enabled
}

/** 当前 URL 是否是 OAuth 回调（带 code/state）。供启动时判断是否要消费。 */
export function hasCallbackParams(): boolean {
  if (typeof window === 'undefined') return false
  const q = new URLSearchParams(window.location.search)
  return q.has('code') && q.has('state')
}

/**
 * 启动序列：若当前 URL 带 code/state 则消费回调，然后返回最新登录态。
 * 必须在 createApp().mount() 之前 await，保证回调完成后 UI 读到的是已登录态，
 * 且 URL 里的临时参数已清理（刷新不会再触发一次 handleSignInCallback）。
 * 任何异常都吞掉并降级为未登录，绝不阻断应用挂载。
 */
export async function initAuth(): Promise<AuthState> {
  let c: LogtoClient | null
  try {
    c = getClient()
  } catch {
    // 配置有误（如 endpoint 非法）导致构造失败，降级为未配置，绝不阻断挂载
    lastAuthState = { configured: false, authenticated: false, sub: null }
    return lastAuthState
  }
  if (!c) {
    lastAuthState = { configured: false, authenticated: false, sub: null }
    return lastAuthState
  }
  try {
    if (hasCallbackParams()) {
      await c.handleSignInCallback(window.location.href)
      stripCallbackParams()
    }
    const authed = await c.isAuthenticated()
    const sub = authed ? (await c.getIdTokenClaims()).sub : null
    lastAuthState = { configured: true, authenticated: authed, sub: sub ?? null }
    return lastAuthState
  } catch {
    lastAuthState = { configured: true, authenticated: false, sub: null }
    return lastAuthState
  }
}

/** 去掉 URL 里的 code/state/iss 等临时参数，保留 hash 路由，避免刷新重放。 */
function stripCallbackParams(): void {
  if (typeof window === 'undefined') return
  const url = new URL(window.location.href)
  for (const k of ['code', 'state', 'iss', 'session_state', 'error', 'error_description']) {
    url.searchParams.delete(k)
  }
  const clean = url.pathname + url.search + url.hash
  window.history.replaceState(window.history.state, '', clean)
}

/** 发起登录跳转（redirect_uri 白名单里的无 fragment 地址）。 */
export async function signIn(): Promise<void> {
  const c = getClient()
  if (!c) return
  await c.signIn({ redirectUri: cfg().redirectUri })
}

/** 发起登出并回跳。 */
export async function signOut(): Promise<void> {
  const c = getClient()
  if (!c) return
  await c.signOut(cfg().postLogoutRedirectUri)
}

/** 当前是否已登录。 */
export async function isAuthenticated(): Promise<boolean> {
  const c = getClient()
  if (!c) return false
  try {
    return await c.isAuthenticated()
  } catch {
    return false
  }
}

/** 当前用户 sub（未登录返回 null）。 */
export async function currentSub(): Promise<string | null> {
  const c = getClient()
  if (!c) return null
  try {
    if (!(await c.isAuthenticated())) return null
    return (await c.getIdTokenClaims()).sub ?? null
  } catch {
    return null
  }
}

/** access token 提供器；供 client.ts 作为 Bearer 附带，切 logto 模式时后端会校验。 */
export async function currentAccessToken(): Promise<string | null> {
  const c = getClient()
  if (!c) return null
  try {
    if (!(await c.isAuthenticated())) return null
    return await c.getAccessToken(cfg().resource || undefined)
  } catch {
    return null
  }
}

/** 用户展示信息（昵称/邮箱），仅用于 UI，不构成身份判据。 */
export interface DisplayUser {
  sub: string
  name: string
  email: string
  picture: string
}
export async function displayUser(): Promise<DisplayUser | null> {
  const c = getClient()
  if (!c) return null
  try {
    if (!(await c.isAuthenticated())) return null
    const claims = await c.getIdTokenClaims()
    return {
      sub: claims.sub,
      name: String(claims.name ?? claims.username ?? ''),
      email: String(claims.email ?? ''),
      picture: String(claims.picture ?? ''),
    }
  } catch {
    return null
  }
}
