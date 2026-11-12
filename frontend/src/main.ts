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
  // 「从云端恢复」登录回跳：只要存在未消费的恢复意图，就把路由定位回锦囊，
  // 让 useSafeKeep 依据「意图 + 已登录」续做拉取。这里只做路由归位，不消费意图、不拉取。
  //
  // 两个历史坑（都已规避）：
  //  1) createWebHashHistory() 在模块导入阶段就把无 fragment 的回调 URL 补成 '...#/'，
  //     所以不能靠「回调 URL 有没有 hash」判断是否归位，只认意图本身；
  //  2) 必须用 router.replace 而不是 window.history.replaceState：router 缓存了初始
  //     location，直接改写 hash 会被初始导航覆盖回 '#/'，导致停在门户、续做不触发。
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
