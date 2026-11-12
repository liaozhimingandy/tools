/**
 * 全链路测试：创建 → 恢复码 → CRUD → 回收站 → 备份 → 导入 → 锁定 → 改密。
 * 运行：node --test tests/vault.test.ts
 *
 * 关键安全断言：任何时刻存储原始文本里都搜不到条目明文（标题/账号/密码/网址/标签），
 * 证明"本地存储只有密文"这一零知识不变量在 service 层成立。
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { reactive } from 'vue'
import * as vault from '../src/services/safekeep/vault.ts'
import { memoryStorage, rawSnapshot, getItems, getAccount, getPrefs } from '../src/services/safekeep/storage.ts'
import type { StorageAdapter } from '../src/services/safekeep/storage.ts'
import type { PlainItem, PlainItems } from '../src/services/safekeep/types.ts'

const PW = 'Master-P@ss-2026!long'

function makeEntry(overrides: Partial<PlainItem> = {}): PlainItem {
  return {
    ...vault.newPlain(),
    title: 'GitHub 企业版',
    fields: { username: 'zhangsan@example.com', password: 'Sup3rSecret-Password!', totp: '' },
    urls: ['https://github.example.com'],
    tags: ['工作', '开发'],
    note: '内部代码仓库，双因素已开启',
    ...overrides,
  }
}

test('全链路：创建保险库 → 存储只有密文 → 主密码解锁还原明文', async () => {
  const store = memoryStorage()
  const made = await vault.createVault(PW)

  // 确认抄写前不落盘
  assert.equal(getAccount(store), null)
  const account = vault.commitVault(store, made)
  assert.equal(getAccount(store)!.app, 'safekeep-local')
  assert.equal(Object.keys(getItems(store)).length, 0)

  // 新增一条
  const entry = makeEntry()
  await vault.saveItem(store, made.vk, entry)
  const stored = getItems(store)[entry.id]!
  assert.ok(stored.iv && stored.ct)
  assert.ok(!('title' in stored) && !('fields' in stored))

  // 零知识核心断言：存储原文里搜不到任何明文片段
  const raw = rawSnapshot(store)
  for (const secret of [entry.title, 'zhangsan@example.com', 'Sup3rSecret-Password!', 'github.example.com', '工作', '内部代码仓库']) {
    assert.ok(!raw.includes(secret), `存储中泄漏了明文: ${secret}`)
  }

  // 重新解锁应还原明文
  const unlocked = await vault.unlock(store, PW, false)
  assert.deepEqual(unlocked.broken, [])
  assert.equal(unlocked.plain[entry.id]!.title, entry.title)
  assert.equal(unlocked.plain[entry.id]!.fields.password, 'Sup3rSecret-Password!')
})

test('恢复码是独立第二把钥匙，且解锁后 vk 与主密码一致', async () => {
  const store = memoryStorage()
  const made = await vault.createVault(PW)
  vault.commitVault(store, made)
  await vault.saveItem(store, made.vk, makeEntry())

  const byCode = await vault.unlock(store, made.recoveryCode, true)
  const byPw = await vault.unlock(store, PW, false)
  assert.deepEqual(byCode.vk, byPw.vk)
  assert.equal(byCode.plain[Object.keys(byCode.plain)[0]!]!.fields.password, 'Sup3rSecret-Password!')
  await assert.rejects(() => vault.unlock(store, 'wrong', false))
})

test('CRUD + 回收站：软删进站、恢复、彻底删除', async () => {
  const store = memoryStorage()
  const made = await vault.createVault(PW)
  vault.commitVault(store, made)
  const plain: PlainItems = {}

  const e1 = makeEntry({ title: 'A' })
  const e2 = makeEntry({ title: 'B' })
  for (const e of [e1, e2]) {
    const delta = await vault.saveItem(store, made.vk, e)
    Object.assign(plain, delta)
  }
  assert.equal(vault.viewCounts(plain).all, 2)

  await vault.deleteItem(store, made.vk, plain, e1.id, false)
  assert.equal(plain[e1.id]!._deleted, true)
  assert.equal(getItems(store)[e1.id]!.deleted, true)
  assert.equal(vault.viewCounts(plain).trash, 1)
  assert.equal(vault.viewCounts(plain).all, 1)

  await vault.restoreItem(store, made.vk, plain, e1.id)
  assert.equal(plain[e1.id]!._deleted, false)
  assert.equal(vault.viewCounts(plain).all, 2)

  await vault.deleteItem(store, made.vk, plain, e1.id, true)
  assert.equal(plain[e1.id], undefined)
  assert.equal(getItems(store)[e1.id], undefined)
})

test('filterItems：视图/标签/搜索组合筛选与收藏置顶排序', async () => {
  const store = memoryStorage()
  const made = await vault.createVault(PW)
  vault.commitVault(store, made)
  const plain: PlainItems = {}
  for (const e of [
    makeEntry({ title: 'Alpha', favorite: false, tags: ['dev'] }),
    makeEntry({ title: 'Beta', favorite: true, tags: ['work'] }),
    makeEntry({ title: 'Gamma', favorite: false, tags: ['dev'] }),
  ]) {
    Object.assign(plain, await vault.saveItem(store, made.vk, e))
  }

  assert.equal(vault.filterItems(plain, { view: 'all', tag: '', filter: '' }).length, 3)
  assert.equal(vault.filterItems(plain, { view: 'all', tag: 'dev', filter: '' }).length, 2)
  assert.equal(vault.filterItems(plain, { view: 'fav', tag: '', filter: '' }).length, 1)
  assert.equal(vault.filterItems(plain, { view: 'all', tag: '', filter: 'gamma' }).length, 1)
  const sorted = vault.filterItems(plain, { view: 'all', tag: '', filter: '' })
  assert.equal(sorted[0]!.title, 'Beta') // 收藏置顶
})

test('备份导出/导入：跨设备还原，密文与 vk 完整', async () => {
  const src = memoryStorage()
  const made = await vault.createVault(PW)
  vault.commitVault(src, made)
  const entry = makeEntry()
  await vault.saveItem(src, made.vk, entry)
  const backed = vault.markBackedUp(src, getAccount(src)!)
  assert.equal(getAccount(src)!.lastBackupAt, backed.lastBackupAt)

  const text = vault.buildBackupText(src, backed)

  // 换一台"设备"（全新存储）导入
  const dst = memoryStorage()
  const imported = vault.applyBackup(dst, text, false)
  assert.equal(imported.app, 'safekeep-local')
  const unlocked = await vault.unlock(dst, PW, false)
  assert.equal(Object.keys(unlocked.plain).length, 1)
  assert.equal(Object.values(unlocked.plain)[0]!.title, entry.title)
  assert.equal(Object.values(unlocked.plain)[0]!.fields.password, entry.fields.password)

  // 已有库时未 force 会要求二次确认
  assert.throws(() => vault.applyBackup(dst, text, false), /CONFIRM_OVERWRITE/)
  assert.doesNotThrow(() => vault.applyBackup(dst, text, true))
})

test('改主密码：vk 不变、条目密文不动、旧密码失效', async () => {
  const store = memoryStorage()
  const made = await vault.createVault(PW)
  vault.commitVault(store, made)
  const entry = makeEntry()
  await vault.saveItem(store, made.vk, entry)
  const ctBefore = getItems(store)[entry.id]!.ct

  const newAccount = await vault.changePassword(store, made.vk, 'Brand-New-P@ss-2026!')
  assert.equal(getItems(store)[entry.id]!.ct, ctBefore, '条目密文不应被重加密')
  assert.deepEqual(await vault.unlock(store, 'Brand-New-P@ss-2026!', false).then((r) => r.vk), made.vk)
  await assert.rejects(() => vault.unlock(store, PW, false))
  assert.ok(newAccount.wrapped.ct)
})

test('恢复码刷新：新码生效、旧码作废（确认后）', async () => {
  const store = memoryStorage()
  const made = await vault.createVault(PW)
  vault.commitVault(store, made)
  const fresh = await vault.refreshRecovery(made.vk)
  vault.commitRecovery(store, fresh.recovery)

  assert.deepEqual(await vault.unlock(store, fresh.code, true).then((r) => r.vk), made.vk)
  await assert.rejects(() => vault.unlock(store, made.recoveryCode, true))
})

test('损坏密文：解密时跳过并报告，不阻塞其余条目', async () => {
  const store = memoryStorage()
  const made = await vault.createVault(PW)
  vault.commitVault(store, made)
  await vault.saveItem(store, made.vk, makeEntry({ title: 'Good' }))
  const items = getItems(store)
  const goodId = Object.keys(items)[0]!
  items['broken-id'] = { id: 'broken-id', rev: 1, iv: 'AAAA', ct: 'AAAA', deleted: false }
  store.setItem('sk.items', JSON.stringify(items))

  const unlocked = await vault.unlock(store, PW, false)
  assert.deepEqual(unlocked.broken, ['broken-id'])
  assert.equal(unlocked.plain[goodId]!.title, 'Good')
})

test('getPrefs 缺省返回空对象，不抛错', () => {
  const store: StorageAdapter = memoryStorage()
  assert.deepEqual(getPrefs(store), {})
})

test('回归：cloneItem 能安全脱离 reactive Proxy（structuredClone 会抛 DataCloneError）', () => {
  // 复现 ItemEditorDialog 的真实形态：reactive 表单（Proxy）里含嵌套对象与数组
  const form = reactive<PlainItem>({
    ...vault.newPlain(),
    title: 'Proxy 表单',
    fields: { username: 'u@example.com', password: 'p@ss' },
    urls: ['https://example.com'],
    tags: ['工作'],
  })

  // 前提证实：structuredClone 对 Proxy 确实抛错（这正是「点保存没反应」的根因）
  // Node 全局未暴露 DataCloneError 构造器（实为 DOMException），故按 name 匹配
  assert.throws(() => structuredClone(form), (e: unknown) => (e as Error).name === 'DataCloneError')

  // cloneItem 不抛错，内容等价，且产出的是普通对象（可被再次 structuredClone / emit）
  const detached = vault.cloneItem(form)
  assert.deepEqual(JSON.parse(JSON.stringify(detached)), JSON.parse(JSON.stringify(form)))
  assert.doesNotThrow(() => structuredClone(detached))
  assert.equal(detached.title, 'Proxy 表单')
  assert.equal(detached.fields.password, 'p@ss')

  // 脱离 Proxy 后修改副本不反向影响表单（深拷贝而非引用）
  detached.tags.push('新增')
  assert.deepEqual(form.tags, ['工作'])
})

test('回归：reactive 表单经 cloneItem 后能走通加密保存并还原（模拟点保存）', async () => {
  const store = memoryStorage()
  const made = await vault.createVault(PW)
  vault.commitVault(store, made)

  const form = reactive<PlainItem>({ ...vault.newPlain(), title: '保存回归', fields: { password: 'secret-123' } })
  // 关键：保存前先 cloneItem 脱离 Proxy，等价于修复后的 submit 流程
  const saved = await vault.saveItem(store, made.vk, vault.cloneItem(form))

  assert.equal(saved[form.id]!.title, '保存回归')
  const unlocked = await vault.unlock(store, PW, false)
  assert.equal(unlocked.plain[form.id]!.fields.password, 'secret-123')
})
