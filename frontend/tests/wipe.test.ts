/**
 * 「忘记主密码 + 恢复码 → 销毁旧库 → 重新创建」闭环回归。
 *
 * 旧缺陷：清空入口只在设置弹窗里，而设置弹窗必须解锁后才能打开，
 * 用户被永久卡在 locked 页。修复后解锁页必须自带带确认的销毁通道，
 * 且 wipe 之后要能真正创建一份全新、可用新主密码解开的保险库。
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  LS, memoryStorage, setAccount, setItems, setRev, setPrefs, setCloudRev, setCloudSyncAt,
  getAccount, getItems, curRev, getCloudRev, getCloudSyncAt, getPrefs, wipeAll,
} from '../src/services/safekeep/storage.ts'
import * as vault from '../src/services/safekeep/vault.ts'

const SRC = resolve(fileURLToPath(new URL('../src', import.meta.url)))
function read(rel: string): string {
  return readFileSync(join(SRC, rel), 'utf8')
}

test('wipeAll 清掉全部 sk.* 键（含云端同步记账），不留旧库残骸', () => {
  const store = memoryStorage()
  setAccount(store, { app: 'old', wrapped: 'w', salt: 's', kdf: { name: 'PBKDF2' }, recovery: { wrapped: 'r' } } as never)
  setItems(store, { item1: { iv: 'iv', ct: 'ct' } } as never)
  setRev(store, 42)
  setPrefs(store, { lockMode: 'idle', idleMs: 1000, clipSec: 5 } as never)
  setCloudRev(store, 9)
  setCloudSyncAt(store, Date.now())

  wipeAll(store)

  assert.equal(getAccount(store), null)
  assert.deepEqual(getItems(store), {})
  assert.equal(curRev(store), 0)
  assert.deepEqual(getPrefs(store), {})
  assert.equal(getCloudRev(store), 0)
  assert.equal(getCloudSyncAt(store), null)
  for (const k of Object.values(LS)) assert.equal(store.getItem(k), null, `${k} 未清除`)
})

test('销毁后能用新主密码重新创建并解锁一份新保险库', async () => {
  const store = memoryStorage()
  // 先放一份旧库（用户已解不开）
  setAccount(store, { app: 'old', wrapped: 'w', salt: 's', kdf: { name: 'PBKDF2' }, recovery: { wrapped: 'r' } } as never)
  setRev(store, 7)
  setCloudRev(store, 3)

  wipeAll(store)

  const made = await vault.createVault('a-brand-new-passphrase-2026')
  const account = vault.commitVault(store, made)
  assert.ok(account)
  assert.equal(getAccount(store)?.app, account.app)
  const r = await vault.unlock(store, 'a-brand-new-passphrase-2026', false)
  assert.ok(r.vk instanceof Uint8Array)
  assert.deepEqual(r.plain, {})
})

test('解锁页自带销毁通道：入口、输入确认、真实 wipe 调用三者齐全', () => {
  const view = read('views/SafeKeepView.vue')
  const locked = view.slice(view.indexOf('锁定 / 解锁'), view.indexOf('<!-- 主界面 -->'))
  assert.match(locked, /主密码和恢复码都忘了/, 'locked 页缺少「忘记全部凭据」入口')
  assert.match(locked, /清空本机数据，重新创建/)
  assert.match(locked, /wipeWord\.trim\(\) !== WIPE_CONFIRM_WORD/, '缺少输入确认词校验')
  assert.match(locked, /@click="onWipeFromLocked"/, '确认按钮未绑定处理函数')
  assert.match(locked, /theme="danger"/, '危险操作未用 danger 主题')
  // 操作按钮必须在 t-alert 之外，避免插槽名写错导致按钮静默消失
  assert.match(locked, /<div v-if="confirmWipe" class="wipe-zone/, '确认区必须是独立 DOM 而非组件插槽')

  const script = view.slice(0, view.indexOf('</script>'))
  assert.match(script, /onWipe\(\)|sk\.wipe\(\)/, '销毁未接到真正的 wipe')

  const comp = read('composables/useSafeKeep.ts')
  assert.match(comp, /function wipe\(\): void \{[\s\S]*?cloud\.resetLocal\(\)/, 'wipe 未重置云端同步记账')
  assert.match(comp, /function wipe\(\): void \{[\s\S]*?screen\.value = 'welcome'/, 'wipe 后未回到欢迎页')

  const cloud = read('composables/useCloudSync.ts')
  assert.match(cloud, /function resetLocal\(\): void \{[\s\S]*?cloudRev\.value = 0/)
})
