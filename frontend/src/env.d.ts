/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

/** 构建期环境变量（vite build 时内联；见 src/config.ts）。 */
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_LOGTO_ENDPOINT?: string
  readonly VITE_LOGTO_APP_ID?: string
  readonly VITE_LOGTO_RESOURCE?: string
  readonly VITE_LOGTO_REDIRECT_URI?: string
  readonly VITE_LOGTO_POST_LOGOUT_REDIRECT_URI?: string
  readonly VITE_LOGTO_SCOPES?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

/**
 * @logto/browser@3.1.2 的 package.json 声明 types=./lib/index.d.ts，
 * 但发布包 lib/ 里只有 .js、缺少该 .d.ts，直接 import 会触发 TS7016。
 * 这里按该 SDK 真实的运行时导出（核对 lib/index.js + @logto/client 类型）补一份最小声明。
 */
declare module '@logto/browser' {
  export interface IdTokenClaims {
    sub: string
    iss?: string
    aud?: string | string[]
    exp?: number
    iat?: number
    email?: string
    name?: string
    picture?: string
    username?: string
    [key: string]: unknown
  }
  export interface UserInfoResponse {
    sub: string
    email?: string
    name?: string
    picture?: string
    username?: string
    [key: string]: unknown
  }
  export interface LogtoConfig {
    endpoint: string
    appId: string
    appSecret?: string
    scopes?: string[]
    resources?: string[]
    prompt?: string | string[]
    requestTimeoutMs?: number
  }
  export interface SignInOptions {
    redirectUri: string | URL
    postRedirectUri?: string | URL
    prompt?: string
  }
  export default class LogtoClient {
    constructor(config: LogtoConfig, enableCache?: boolean)
    isAuthenticated(): Promise<boolean>
    signIn(options: SignInOptions): Promise<void>
    signIn(redirectUri: string | URL): Promise<void>
    signOut(postLogoutRedirectUri?: string): Promise<void>
    handleSignInCallback(callbackUri: string): Promise<void>
    isSignInRedirected(url: string): Promise<boolean>
    getIdTokenClaims(): Promise<IdTokenClaims>
    getIdToken(): Promise<string | null>
    getAccessToken(resource?: string): Promise<string>
    clearAllTokens(): Promise<void>
    fetchUserInfo(): Promise<UserInfoResponse>
  }
}
