import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { initAuth } from '@/services/auth/logto.ts'

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
  createApp(App).use(router).use(TDesign).mount('#app')
}
void boot()
