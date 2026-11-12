/**
 * 生产部署默认值静态守卫（node --test，纯文本断言，无浏览器）。
 *
 * 回归背景（2026-11-12）：公网入口 `https://www.alsoapp.com/tools/#/safekeep`
 * 看不到「登录并从云端恢复」，排查出三层与仓库配置直接相关的问题：
 *   1) 生产回调/登出地址内联的是 `liaozhimingandy.github.io`，而实际访问域是
 *      自定义域 `www.alsoapp.com`（前者会 301 到后者）。跨 origin 会让
 *      sessionStorage 里的「恢复意图」丢失，且该 URI 未在 Logto 登记（400）。
 *   2) 后端 CORS 白名单填的是 Pages 源站，浏览器实际 origin 是自定义域。
 *   3) 自定义域 CDN 把 `/tools/` 的 HTML 缓存 30 天，Actions 部署成功但公网仍是旧版。
 *
 * 本测试只守住仓库能控制的部分（1、2 与部署提示），CDN / DNS / Logto 白名单
 * 属于外部控制台配置，见 README「A.6」与「需人工验证」清单。
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(fileURLToPath(new URL('../..', import.meta.url)))

function read(rel: string): string {
  return readFileSync(resolve(ROOT, rel), 'utf8')
}

const PROD_ORIGIN = 'https://www.alsoapp.com'
const PROD_CALLBACK = 'https://www.alsoapp.com/tools/'
const PROD_API = 'https://api.alsoapp.com'

test('Pages 工作流生产回调与登出回跳必须是自定义域（与访问域同 origin）', () => {
  const wf = read('.github/workflows/deploy-github-pages.yml')
  // 校验步骤 + 构建 env 各两处，合计 4 处默认值
  const hits = wf.match(/https:\/\/www\.alsoapp\.com\/tools\//g) ?? []
  assert.ok(hits.length >= 4, `生产回调默认值出现 ${hits.length} 次，应至少 4 次`)
  assert.equal(PROD_CALLBACK.includes('#'), false, 'OAuth redirect_uri 不能带 fragment')
  assert.doesNotMatch(
    wf,
    /https:\/\/liaozhimingandy\.github\.io\/tools\//,
    '不能再用 Pages 源站作为生产回调：它会 301 到自定义域，恢复意图按 origin 隔离会丢',
  )
})

test('生产地址全 HTTPS：API 根 / Logto endpoint / 回调 / 登出', () => {
  const wf = read('.github/workflows/deploy-github-pages.yml')
  assert.match(wf, /\$\{\{ vars\.VITE_API_BASE_URL \|\| 'https:\/\/api\.alsoapp\.com' \}\}/)
  assert.match(wf, /VITE_API_BASE_URL:.*https:\/\/api\.alsoapp\.com/)
  assert.match(wf, /VITE_LOGTO_ENDPOINT:.*https:\/\/account\.alsoapp\.com/)
  assert.match(wf, /VITE_LOGTO_REDIRECT_URI:.*https:\/\/www\.alsoapp\.com\/tools\//)
  assert.match(wf, /VITE_LOGTO_POST_LOGOUT_REDIRECT_URI:.*https:\/\/www\.alsoapp\.com\/tools\//)
  assert.equal(PROD_API.startsWith('https://'), true)
  assert.equal(PROD_ORIGIN.startsWith('https://'), true)
})

test('后端 CORS 白名单填前端 origin，不是后端域名', () => {
  const env = read('backend/.env.example')
  assert.match(env, /^TOOLS_CORS_ORIGINS=https:\/\/www\.alsoapp\.com$/m)
  assert.doesNotMatch(env, /^TOOLS_CORS_ORIGINS=.*api\.alsoapp\.com/m)
  assert.equal(PROD_ORIGIN.endsWith('/'), false, 'CORS origin 不带尾斜杠')
})

test('后端镜像名固定为 fastapi-tools', () => {
  const wf = read('.github/workflows/build-images.yml')
  assert.match(wf, /^\s*IMAGE_NAME: fastapi-tools$/m)
  assert.doesNotMatch(wf, /tools-backend|fastapi_tuiwen/)
  for (const f of [
    'backend/.env.example',
    'backend/docker-compose.image.yml',
    'README.md',
  ]) {
    assert.match(read(f), /fastapi-tools/, `${f} 未同步新镜像名`)
  }
})

test('部署作业输出 CDN cache-buster 验证地址', () => {
  const wf = read('.github/workflows/deploy-github-pages.yml')
  assert.match(wf, /公网验证地址（绕过 CDN 缓存）/)
  assert.match(wf, /https:\/\/www\.alsoapp\.com\/tools\/\?v=\$\{TS\}#\/safekeep/)
  assert.match(read('README.md'), /### A\.6 自定义域 CDN 缓存/)
})
