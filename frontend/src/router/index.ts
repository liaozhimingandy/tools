import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'

/**
 * 工具集路由表。
 * 新增工具 = 在 routes 里加一条记录 + 在 views/ 下加一个视图 + 在门户 HomeView 加卡片。
 *
 * 采用 hash 模式（/#/safekeep），原因有二：
 *   1. GitHub Pages 是纯静态托管，history 模式直接刷新 /tools/safekeep 会 404，hash 不发给服务器；
 *   2. OAuth2/Logto 的 redirect_uri 禁止带 fragment(#)，hash 路由让回调落在站点根 /tools/ 上，
 *      由 main.ts 在挂载前消费 code/state，再 replace 到 #/safekeep（详见 auth service）。
 */
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: '工具集' },
  },
  {
    path: '/safekeep',
    name: 'safekeep',
    component: () => import('@/views/SafeKeepView.vue'),
    meta: { title: '锦囊 SafeKeep' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.afterEach((to) => {
  const title = (to.meta.title as string | undefined) ?? '工具集'
  document.title = `${title} · tools`
})

export default router
