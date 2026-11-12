/**
 * 加密核心测试：KAT（已知答案向量）+ 纯函数不变量。
 * 运行：node --test tests/crypto.test.ts
 *
 * KAT 期望值由本模块在 Node 22 Web Crypto 上生成后固化，用于锁定
 * PBKDF2-SHA256 600k / AES-256-GCM 的字节级行为，防止"优化"改动破坏
 * 与示例及既有加密备份的兼容性。
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import * as VC from '../src/services/safekeep/crypto.ts'
import type { PlainItem } from '../src/services/safekeep/types.ts'

const enc = new TextEncoder()

test('KAT: PBKDF2-SHA256 600k 派生密钥字节稳定', async () => {
  const salt = enc.encode('000102030405060708090a0b0c0d0e0f')
  const key = await VC.derive('correct horse battery staple', salt)
  assert.equal(Buffer.from(key).toString('hex'), 'd1321c7f8fdc46df5b0eb71c5dd8c19a572d9a4fb6102fc2c7fbdea660ae7719')
})

test('KAT: AES-256-GCM 固定密钥+iv 密文稳定（压缩语义不变）', async () => {
  const salt = enc.encode('000102030405060708090a0b0c0d0e0f')
  const key = await VC.derive('correct horse battery staple', salt)
  const k = await crypto.subtle.importKey('raw', key as BufferSource, 'AES-GCM', false, ['encrypt'])
  const iv = enc.encode('0f0e0d0c0b0a090807060504')
  const ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv, tagLength: 128 }, k, enc.encode('hello 锦囊'))
  assert.equal(Buffer.from(ct).toString('hex'), 'f24a9302a23f161e7a0e8aad0794bcffb30d54d6bd3d312f4453ee12')
})

test('seal/unseal 往返正确，且密文不含明文', async () => {
  const key = VC.rnd(32)
  const rec = await VC.seal(key, enc.encode('s3cr3t-明文'))
  assert.ok(rec.iv && rec.ct)
  assert.ok(!JSON.stringify(rec).includes('s3cr3t'))
  const out = await VC.unseal(key, rec)
  assert.equal(new TextDecoder().decode(out), 's3cr3t-明文')
})

test('unseal 用错密钥会失败（GCM 认证标签生效）', async () => {
  const rec = await VC.seal(VC.rnd(32), enc.encode('data'))
  await assert.rejects(() => VC.unseal(VC.rnd(32), rec))
})

test('encryptJSON/decryptJSON 往返保留对象结构', async () => {
  const key = VC.rnd(32)
  const obj = { title: 'GitHub', fields: { password: 'P@ss' }, tags: ['dev', '工作'] }
  const rec = await VC.encryptJSON(key, obj)
  const back = (await VC.decryptJSON(key, rec)) as typeof obj
  assert.deepEqual(back, obj)
})

test('makeVault：主密码与恢复码是两把独立钥匙，都能解开同一把 vk', async () => {
  const made = await VC.makeVault('MasterPass-2026!')
  assert.equal(made.vk.length, 32)
  assert.equal(made.account.app, 'safekeep-local')
  assert.equal(made.account.kdf.iterations, 600000)
  const byPw = await VC.unwrap('MasterPass-2026!', made.account, false)
  const byCode = await VC.unwrap(made.recoveryCode, made.account, true)
  assert.deepEqual(byPw, made.vk)
  assert.deepEqual(byCode, made.vk)
})

test('unwrap 错误主密码 / 错误恢复码均失败', async () => {
  const made = await VC.makeVault('right-password')
  await assert.rejects(() => VC.unwrap('wrong-password', made.account, false))
  await assert.rejects(() => VC.unwrap('AAAA-AAAA-AAAA-AAAA-AAAA', made.account, true))
})

test('恢复码归一化：忽略连字符、大小写、O→0、I/L→1', async () => {
  const made = await VC.makeVault('pw-for-norm')
  const noisy = made.recoveryCode.toLowerCase().replace(/0/g, 'O').replace(/1/g, 'l')
  const vk = await VC.unwrap(noisy, made.account, true)
  assert.deepEqual(vk, made.vk)
})

test('rewrap：改主密码只换包裹，vk 不变，旧密码失效', async () => {
  const made = await VC.makeVault('old-password')
  const r = await VC.rewrap(made.vk, 'new-password')
  const account = { ...made.account, salt: r.salt, wrapped: r.wrapped }
  assert.deepEqual(await VC.unwrap('new-password', account, false), made.vk)
  await assert.rejects(() => VC.unwrap('old-password', account, false))
  // 恢复码不受改密影响
  assert.deepEqual(await VC.unwrap(made.recoveryCode, account, true), made.vk)
})

test('refreshRecovery：新码生效、旧码作废，vk 不变', async () => {
  const made = await VC.makeVault('pw-keep')
  const fresh = await VC.refreshRecovery(made.vk)
  const account = { ...made.account, recovery: fresh.recovery }
  assert.deepEqual(await VC.unwrap(fresh.code, account, true), made.vk)
  await assert.rejects(() => VC.unwrap(made.recoveryCode, account, true))
})

test('genRecovery 格式：Crockford Base32、无 I/L/O/U、4 位分组', () => {
  for (let i = 0; i < 20; i++) {
    const code = VC.genRecovery()
    assert.match(code, /^[0-9A-HJKMNP-TV-Z]{4}(-[0-9A-HJKMNP-TV-Z]{4})+$/)
    assert.ok(!/[ILOU]/.test(code))
  }
})

test('genPassword 随机模式：长度/字符集正确且排除易混淆字符', () => {
  const r = VC.genPassword({ length: 40, exclude: true })
  assert.equal(r.value.length, 40)
  assert.ok(!/[1lI0OoS5Z2]/.test(r.value))
  assert.ok(r.entropy >= 200)
})

test('genPassword 短语模式：词表组合 + 可选数字后缀', () => {
  const r = VC.genPassword({ phrase: true, length: 6, digits: true })
  assert.equal(r.value.split('-').length, 7)
  assert.match(r.value.split('-').slice(-1)[0]!, /^\d{2}$/)
})

test('shouldLock 判据：后台即锁、关闭不锁、超时锁', () => {
  assert.equal(VC.shouldLock(1000, 0, 5000, true), true)
  assert.equal(VC.shouldLock(9999, 0, 0, false), false)
  assert.equal(VC.shouldLock(4999, 0, 5000, false), false)
  assert.equal(VC.shouldLock(5000, 0, 5000, false), true)
})

test('health：识别弱密码、复用、过期，评分随问题下降', () => {
  const base: PlainItem = {
    id: 'x', v: 1, type: 'login', title: 't', fields: {}, urls: [], note: '', tags: [],
    favorite: false, createdAt: 0, updatedAt: VC.now(), _deleted: false,
  }
  const items: PlainItem[] = [
    { ...base, id: '1', fields: { password: '123' } },
    { ...base, id: '2', fields: { password: '123' } },
    { ...base, id: '3', fields: { password: 'VeryLongAndStrongP@ssw0rd!' }, updatedAt: 0 },
    { ...base, id: '4', _deleted: true, fields: { password: 'weak' } },
  ]
  const h = VC.health(items)
  assert.equal(h.total, 3) // 排除已删除的 id4
  assert.equal(h.withPw, 3)
  assert.equal(h.weak, 2) // 仅 '123','123' 两条 <12 位；长密码与已删项不计
  assert.equal(h.reused, 2)
  assert.equal(h.old, 1) // id3 updatedAt=0
  assert.equal(h.score, 69) // 100 - 2*8 - 2*6 - 1*3
})

test('buildBackup/parseBackup：往返 + 拒绝非锦囊/损坏文件', async () => {
  const made = await VC.makeVault('backup-pw')
  const items = { 'id-1': { id: 'id-1', rev: 1, ...(await VC.encryptJSON(made.vk, { title: 'x' })), deleted: false } }
  const text = VC.buildBackup(made.account, items, 1)
  const parsed = VC.parseBackup(text)
  assert.equal(parsed.app, 'safekeep-backup')
  assert.equal(parsed.rev, 1)
  assert.deepEqual(parsed.items, items)
  assert.deepEqual(parsed.account.wrapped, made.account.wrapped)
  assert.throws(() => VC.parseBackup('{not json'), /不是有效的 JSON/)
  assert.throws(() => VC.parseBackup('{"app":"other"}'), /不是锦囊/)
  const broken = JSON.parse(text)
  delete broken.account.recovery
  assert.throws(() => VC.parseBackup(JSON.stringify(broken)), /结构损坏/)
})
