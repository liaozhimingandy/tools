import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { initAuth } from '@/services/auth/logto.ts'
import { hasRestoreIntent, sessionRestoreStore, shouldRestoreRoute } from '@/services/auth/restoreIntent.ts'

// TDesign Vue Next：全量注册 + 全局基础样式（组件外观为未分层 CSS，不受 Tailwind preflight 影响）
import TDesign from 'tdesign-vue-next'
import 'tdesign-vue-next/es/style/index.css'

// 主题与工具样式：顺序敏感——先令牌覆盖，再 Tailwind 工具类与少量复用样式
import './styles/theme.css'
import './styles/global.css'

/**
 * 挂载前先处理 Logto OAuth 回调：
 *  - 若 URL 带 ?code=&state=，换取 token 并清理 URL 临时参数；
 *  - 结果写入模块级缓存，供后续 useCloudSync 同步读取，避免首屏登录态闪动。
 * initAuth 内部对「未配置」与任何异常都降级为空操作，绝不阻断应用挂载（不白屏）。
 */
async function boot(): Promise<void> {
  try {
    await initAuth()
  } catch {
    /* 任何意外都降级：不阻断挂载，保证绝不白屏 */
  }
  // 「从云端恢复」登录回跳：OAuth 回调必落在站点根（无 fragment），
  // 若存在未消费的恢复意图，把路由定位回锦囊，让 useSafeKeep 挂载后续做拉取。
  // 意图的消费与过期由 useSafeKeep.onMounted 负责，这里只做路由归位，绝不重复拉取。
  //
  // ⚠️ 必须用 router.replace 而不是 window.history.replaceState：
  // createWebHashHistory() 在模块导入时就缓存了初始 location（回调 URL 无 hash → 解析为 '/'），
  // 挂载时 router 的初始导航会把我们直接改写的 hash 覆盖回 '#/'，导致停在门户、续做不触发。
  // 走 router API 才能让内部状态与 URL 同步。
  const needRestore =
    typeof window !== 'undefined' &&
    hasRestoreIntent(sessionRestoreStore()) &&
    shouldRestoreRoute(window.location.hash)

  createApp(App).use(router).use(TDesign).mount('#app')

  if (needRestore) {
    // 等 router 完成初始导航后再 replace，避免与初始导航竞争
    void router.isReady().then(() => router.replace('/safekeep'))
  }
}
void boot()
