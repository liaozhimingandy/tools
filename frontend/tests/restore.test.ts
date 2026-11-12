/**
 * 登录配置 + 云端恢复意图的单测（node --test，无 DOM / 无网络 / 无 SDK）。
 *
 * 覆盖：
 *  - resolveLogtoConfig：内联公开默认值、VITE_* 覆盖优先级、redirectUri 无 fragment、
 *    scopes 拆分、enabled 判定；
 *  - restoreIntent：mark/consume 幂等、TTL 过期、损坏数据、清空、
 *    普通打开（无意图）不误触发。
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import {
  resolveLogtoConfig, DEFAULT_LOGTO_ENDPOINT, DEFAULT_LOGTO_APP_ID,
} from '../src/config.ts'
import {
  markRestoreIntent, hasRestoreIntent, consumeRestoreIntent, clearRestoreIntent,
  shouldRestoreRoute, RESTORE_INTENT_TTL_MS,
} from '../src/services/auth/restoreIntent.ts'
import { memoryStorage } from '../src/services/safekeep/storage.ts'

// --------------------------------------------------------------------------- #
// Logto 配置解析
// --------------------------------------------------------------------------- #

test('内联 Logto 公开默认值生效（无需任何 VITE_* 即可登录配置）', () => {
  const c = resolveLogtoConfig({}, 'https://liaozhimingandy.github.io')
  assert.equal(c.endpoint, DEFAULT_LOGTO_ENDPOINT)
  assert.equal(c.appId, DEFAULT_LOGTO_APP_ID)
  assert.equal(c.endpoint, 'https://account.alsoapp.com')
  // Pages 子路径：BASE_URL 默认 '/' → 回调落站点根（hash 路由无 fragment，符合 OAuth）
  assert.equal(c.redirectUri, 'https://liaozhimingandy.github.io/')
  assert.equal(c.enabled, true)
  assert.ok(!c.redirectUri.includes('#'))
})

test('GitHub Pages 子路径部署：redirectUri 落到 /tools/，无 #', () => {
  const c = resolveLogtoConfig({ BASE_URL: '/tools/' }, 'https://liaozhimingandy.github.io')
  assert.equal(c.redirectUri, 'https://liaozhimingandy.github.io/tools/')
  assert.equal(c.postLogoutRedirectUri, c.redirectUri) // 未单独配置时同回调
  assert.ok(!c.redirectUri.includes('#'))
})

test('VITE_* 覆盖内联默认值，endpoint 去尾斜杠', () => {
  const c = resolveLogtoConfig(
    {
      VITE_LOGTO_ENDPOINT: 'https://custom.logto.app/oidc/',
      VITE_LOGTO_APP_ID: 'custom-app-id',
      VITE_LOGTO_RESOURCE: 'https://api.example.com',
      VITE_LOGTO_REDIRECT_URI: 'https://x.github.io/tools/',
      VITE_LOGTO_POST_LOGOUT_REDIRECT_URI: 'https://x.github.io/',
      VITE_LOGTO_SCOPES: 'email, profile ,custom:scope',
    },
    'https://ignored.example.com',
  )
  assert.equal(c.endpoint, 'https://custom.logto.app/oidc')
  assert.equal(c.appId, 'custom-app-id')
  assert.equal(c.resource, 'https://api.example.com')
  assert.equal(c.redirectUri, 'https://x.github.io/tools/') // 显式配置优先于拼装
  assert.equal(c.postLogoutRedirectUri, 'https://x.github.io/')
  assert.deepEqual(c.scopes, ['email', 'profile', 'custom:scope'])
  assert.equal(c.enabled, true)
})

test('无 origin 且无显式 redirectUri 时降级为未启用（Node/SSR 安全）', () => {
  const c = resolveLogtoConfig({}, '')
  assert.equal(c.redirectUri, '')
  assert.equal(c.enabled, false) // endpoint/appId 有，但缺回调 → 不可登录
})

// --------------------------------------------------------------------------- #
// 云端恢复意图
// --------------------------------------------------------------------------- #

test('恢复意图：mark 后存在，consume 读取一次即清除（幂等/防重复拉取）', () => {
  const s = memoryStorage()
  assert.equal(hasRestoreIntent(s, 1000), false) // 普通打开：无意图
  markRestoreIntent(s, 1000)
  assert.equal(hasRestoreIntent(s, 1001), true)
  assert.equal(consumeRestoreIntent(s, 1002), true) // 第一次消费成功
  assert.equal(consumeRestoreIntent(s, 1003), false) // 再消费为空 → 不会重复覆盖
  assert.equal(hasRestoreIntent(s, 1004), false)
})

test('恢复意图：超过 TTL 视为过期，且消费时一并清理', () => {
  const s = memoryStorage()
  markRestoreIntent(s, 1000)
  assert.equal(hasRestoreIntent(s, 1000 + RESTORE_INTENT_TTL_MS), true) // 边界内有效
  assert.equal(hasRestoreIntent(s, 1000 + RESTORE_INTENT_TTL_MS + 1), false) // 过期
  assert.equal(consumeRestoreIntent(s, 1000 + RESTORE_INTENT_TTL_MS + 1), false)
  assert.equal(hasRestoreIntent(s, 1000), false) // 已被清理
})

test('恢复意图：时钟回拨（now < at）判为无效，防伪造', () => {
  const s = memoryStorage()
  markRestoreIntent(s, 5000)
  assert.equal(hasRestoreIntent(s, 4000), false)
})

test('恢复意图：损坏 / 非对象 / 缺字段的 JSON 一律拒绝并清理，不污染状态', () => {
  const s = memoryStorage()
  s.setItem('sk.cloudRestoreIntent', 'not-json')
  assert.equal(hasRestoreIntent(s, 1000), false)
  assert.equal(consumeRestoreIntent(s, 1000), false)

  s.setItem('sk.cloudRestoreIntent', JSON.stringify({ foo: 'bar' }))
  assert.equal(hasRestoreIntent(s, 1000), false) // 缺 at 字段

  s.setItem('sk.cloudRestoreIntent', JSON.stringify({ at: 'soon' }))
  assert.equal(hasRestoreIntent(s, 1000), false) // at 非数字
})

test('恢复意图：clear 直接清除（登录失败 / 取消恢复时用）', () => {
  const s = memoryStorage()
  markRestoreIntent(s, 1000)
  clearRestoreIntent(s)
  assert.equal(hasRestoreIntent(s, 1000), false)
})

// --------------------------------------------------------------------------- #
// 回调落地后的路由归位判定
// 回归：OAuth 回调落在站点根（无 fragment）时，必须把路由定位回锦囊；
// 用户已经在锦囊或其它子页时不改路由，避免打断当前位置。
// --------------------------------------------------------------------------- #

test('shouldRestoreRoute：回调落在站点根 / 门户时需要归位', () => {
  assert.equal(shouldRestoreRoute(''), true)
  assert.equal(shouldRestoreRoute('/'), true)
  assert.equal(shouldRestoreRoute('#/'), true)
})

test('shouldRestoreRoute：已在锦囊或其它子页时保持原位', () => {
  assert.equal(shouldRestoreRoute('#/safekeep'), false)
  assert.equal(shouldRestoreRoute('#/safekeep?tab=x'), false)
  assert.equal(shouldRestoreRoute('#/404'), false)
})
