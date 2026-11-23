/**
 * 统一应用启动流程 composable。
 *
 * 流程（服务端二次校验，前端隐藏不算权限控制）：
 *   1. POST /v1/portal/apps/{code}/launch 检查发布状态 / 登录要求 / 可见范围；
 *   2. allowed → 记录最近访问 + 按 open_mode 打开；
 *   3. LOGIN_REQUIRED → 记录「登录后启动」意图 + 跳 Logto，登录后自动续做；
 *   4. NOT_DEPLOYED / APP_FORBIDDEN → 明确提示，不静默失败。
 */

import { MessagePlugin } from 'tdesign-vue-next'
import {
  checkLaunch,
  recordVisit,
  type PortalApp,
  PortalApiError,
} from '@/services/portal/api.ts'
import { isAuthenticated, signIn } from '@/services/auth/logto.ts'
import { usePortalStore } from './store.ts'
import {
  markLaunchIntent,
  consumeLaunchIntent,
  sessionLaunchStore,
} from './launchIntent.ts'

export function useAppLaunch() {
  const { touchRecent } = usePortalStore()

  async function launch(app: PortalApp): Promise<void> {
    let result
    try {
      result = await checkLaunch(app.code)
    } catch (e) {
      const msg = e instanceof PortalApiError ? e.message : '启动检查失败，请稍后重试'
      await MessagePlugin.error(msg)
      return
    }

    if (!result.allowed) {
      if (result.reason === 'LOGIN_REQUIRED') {
        const authed = await isAuthenticated().catch(() => false)
        if (!authed) {
          markLaunchIntent(sessionLaunchStore(), app.code)
          try { await signIn() } catch { await MessagePlugin.warning('登录跳转失败，请重试') }
          return
        }
      }
      await MessagePlugin.warning(result.message || '当前无法访问该应用')
      return
    }

    // 记录最近访问（失败不影响打开）
    try { await recordVisit(result.app.id) } catch { /* 访问记录非关键路径 */ }
    touchRecent(result.app)

    const url = result.url
    if (!url) {
      await MessagePlugin.warning('该应用尚未开放访问')
      return
    }
    if (result.open_mode === 'same_tab') {
      window.location.assign(url)
    } else {
      window.open(url, '_blank', 'noopener,noreferrer')
    }
  }

  /** 登录回调后调用：若有未消费的启动意图，自动续做一次。 */
  async function resumeAfterLogin(): Promise<void> {
    const authed = await isAuthenticated().catch(() => false)
    if (!authed) return
    const code = consumeLaunchIntent(sessionLaunchStore())
    if (!code) return
    const { state } = usePortalStore()
    const app = state.apps.find((a) => a.code === code)
    if (app) await launch(app)
  }

  return { launch, resumeAfterLogin }
}
