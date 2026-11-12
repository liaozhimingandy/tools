/**
 * 云端同步纯逻辑单测（node --test，无 DOM / 无网络 / 无 Vue）。
 *
 * 覆盖：
 *  - 零知识：buildCloudBlob 只搬密文，绝不混入主密码/恢复码明文/vaultKey；
 *  - parseCloudBlob：结构损坏 / 版本不兼容 / 混入明文一律拒绝；
 *  - decidePush / decidePull：跨设备冲突判据（stale / older）；
 *  - applyCloudBlob：远端覆盖本地后账号与密文往返一致；
 *  - CloudClient：X-User-Sub 头、Bearer、404→null、409→REVISION_CONFLICT、
 *    PUT body 形状（不透明 value + expected_revision）。
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { memoryStorage, getAccount, getItems, curRev, setAccount, setItems, setRev } from '../src/services/safekeep/storage.ts'
import type { Account, StoredItems } from '../src/services/safekeep/types.ts'
import {
  buildCloudBlob, parseCloudBlob, decidePush, decidePull, forcePushBase,
  applyCloudBlob, toRemoteSummary, BlobError,
} from '../src/services/cloud/sync.ts'
import { fetchVault, fetchRevision, putVault, CloudError } from '../src/services/cloud/client.ts'
import type { CloudClientOptions } from '../src/services/cloud/client.ts'
import type { CloudVaultBlob } from '../src/services/cloud/types.ts'

function makeAccount(): Account {
  return {
    v: 1, app: 'safekeep-local', mode: 'local', createdAt: 1000,
    salt: 'c2FsdA==', kdf: { alg: 'PBKDF2-SHA256', iterations: 600000 },
    wrapped: { iv: 'aXY=', ct: 'Y3Q=' },
    recovery: { salt: 'cnNhbHQ=', iv: 'cml2', ct: 'cmN0' },
    lastBackupAt: null,
  }
}
function makeItems(): StoredItems {
  return {
    'id-1': { id: 'id-1', rev: 1, iv: 'AA==', ct: 'BB==', deleted: false },
    'id-2': { id: 'id-2', rev: 2, iv: 'CC==', ct: 'DD==', deleted: true },
  }
}

test('buildCloudBlob 只含密封结构与逻辑时钟，不含任何明文/密钥', () => {
  const blob = buildCloudBlob(makeAccount(), makeItems(), 42, 999)
  assert.equal(blob.fmt, 'safekeep-vault')
  assert.equal(blob.schema, 1)
  assert.equal(blob.rev, 42)
  assert.equal(blob.savedAt, 999)
  const text = JSON.stringify(blob)
  // 明文主密码 / vaultKey / 恢复码明文都不应出现；只有 iv/ct/salt 等密封字段
  assert.ok(!text.includes('vaultKey'))
  assert.ok(!text.includes('masterPassword'))
  assert.ok(!text.includes('recoveryCode'))
  assert.deepEqual(blob.items['id-1']!.ct, 'BB==')
})

test('buildCloudBlob 深拷贝：改动本地对象不影响已打包 blob', () => {
  const items = makeItems()
  const blob = buildCloudBlob(makeAccount(), items, 1, 0)
  items['id-1']!.ct = 'MUTATED'
  assert.equal(blob.items['id-1']!.ct, 'BB==')
})

test('parseCloudBlob 接受合法 blob 且往返一致', () => {
  const blob = buildCloudBlob(makeAccount(), makeItems(), 7, 123)
  const parsed = parseCloudBlob(JSON.parse(JSON.stringify(blob)))
  assert.deepEqual(parsed, blob)
})

test('parseCloudBlob 拒绝格式/版本/结构损坏', () => {
  const good = buildCloudBlob(makeAccount(), makeItems(), 1, 1)
  assert.throws(() => parseCloudBlob(null), BlobError)
  assert.throws(() => parseCloudBlob({ ...good, fmt: 'other' }), /格式/)
  assert.throws(() => parseCloudBlob({ ...good, schema: 99 }), /版本不兼容/)
  assert.throws(() => parseCloudBlob({ ...good, rev: -1 }), /逻辑时钟/)
  assert.throws(() => parseCloudBlob({ ...good, account: { app: 'evil' } }), /账户密封结构/)
  const badItems = { ...good, items: { x: { id: 'x', rev: 1 } } }
  assert.throws(() => parseCloudBlob(badItems), /密文字段/)
})

test('decidePush：首次创建 / 版本一致可更新 / 远端被改则 stale', () => {
  assert.deepEqual(decidePush(null, 0), { kind: 'create' })
  assert.deepEqual(decidePush(3, 3), { kind: 'update', base: 3 })
  assert.deepEqual(decidePush(4, 3), { kind: 'stale', remote: 4, local: 3 })
  // 本机从未同步但云端已有数据 -> stale，禁止盲覆盖
  assert.deepEqual(decidePush(1, 0), { kind: 'stale', remote: 1, local: 0 })
  assert.equal(forcePushBase(9), 9)
})

test('decidePull：云端更新可应用 / 一致 / 更旧须确认', () => {
  assert.deepEqual(decidePull(10, 8), { kind: 'apply' })
  assert.deepEqual(decidePull(8, 8), { kind: 'up-to-date' })
  assert.deepEqual(decidePull(5, 9), { kind: 'older' })
})

test('applyCloudBlob 覆盖本地：账号/密文/逻辑时钟往返一致', () => {
  const store = memoryStorage()
  const blob = buildCloudBlob(makeAccount(), makeItems(), 12, 5)
  const acct = applyCloudBlob(store, blob)
  assert.equal(acct.app, 'safekeep-local')
  assert.deepEqual(getItems(store), blob.items)
  assert.equal(curRev(store), 12)
})

test('本地 -> blob -> 远端 -> 本地 全链路密文不失真', () => {
  const local = memoryStorage()
  setAccount(local, makeAccount())
  setItems(local, makeItems())
  setRev(local, 6)
  const blob = buildCloudBlob(getAccount(local)!, getItems(local), curRev(local))
  const remote = parseCloudBlob(JSON.parse(JSON.stringify(blob))) // 模拟 JSON 过网络
  const fresh = memoryStorage()
  applyCloudBlob(fresh, remote)
  assert.deepEqual(getItems(fresh), getItems(local))
})

test('toRemoteSummary：不存在时给出空摘要', () => {
  const empty = toRemoteSummary(false, null, null)
  assert.equal(empty.exists, false)
  assert.equal(empty.itemCount, 0)
})

// --------------------------------------------------------------------------- //
// HTTP 客户端（注入 fetch）
// --------------------------------------------------------------------------- //

const BASE = 'https://api.test'
function opts(overrides: Partial<CloudClientOptions> = {}): CloudClientOptions {
  return { userSub: 'logto|alice', base: BASE, device: 'web-test', ...overrides }
}
function jsonResp(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}
function okRecord(blob: CloudVaultBlob, revision: number): Record<string, unknown> {
  return {
    value: blob, revision, updated_at: '2026-01-01T00:00:00Z',
    updated_by_device: 'web-test', etag: `W/"${revision}"`,
  }
}

test('fetchVault：404 -> null，且带 X-User-Sub / Bearer 头', async () => {
  let seenHeaders: Record<string, string> = {}
  const f = (async (_url: string, init?: RequestInit) => {
    seenHeaders = init?.headers as Record<string, string>
    return jsonResp(404, { error: 'NOT_FOUND' })
  }) as typeof fetch
  const r = await fetchVault(opts({ fetchImpl: f, getToken: async () => 'tok123' }))
  assert.equal(r, null)
  assert.equal(seenHeaders['X-User-Sub'], 'logto|alice')
  assert.equal(seenHeaders['Authorization'], 'Bearer tok123')
})

test('fetchVault：200 -> RemoteVault（value 经严格校验）', async () => {
  const blob = buildCloudBlob(makeAccount(), makeItems(), 5, 10)
  const f = (async (url: string) => {
    assert.equal(url, `${BASE}/v1/configs/safekeep/vault`)
    return jsonResp(200, okRecord(blob, 2))
  }) as typeof fetch
  const r = await fetchVault(opts({ fetchImpl: f }))
  assert.equal(r!.revision, 2)
  assert.equal(r!.blob.rev, 5)
  assert.deepEqual(r!.blob.items, blob.items)
})

test('fetchRevision：只回传 revision', async () => {
  const blob = buildCloudBlob(makeAccount(), makeItems(), 5, 10)
  const f = (async () => jsonResp(200, okRecord(blob, 7))) as typeof fetch
  assert.equal(await fetchRevision(opts({ fetchImpl: f })), 7)
})

test('409 -> CloudError(REVISION_CONFLICT) 携带 expected/actual', async () => {
  const f = (async () => jsonResp(409, {
    error: 'REVISION_CONFLICT', message: '冲突', detail: { expected: 1, actual: 4 },
  })) as typeof fetch
  const blob = buildCloudBlob(makeAccount(), makeItems(), 5, 10)
  await assert.rejects(
    () => putVault(opts({ fetchImpl: f }), blob, 1),
    (e: unknown) => {
      assert.ok(e instanceof CloudError)
      assert.equal(e.code, 'REVISION_CONFLICT')
      assert.deepEqual(e.detail, { expected: 1, actual: 4 })
      return true
    },
  )
})

test('putVault：body 为不透明 value + expected_revision + device，无明文', async () => {
  let sent: Record<string, unknown> = {}
  const blob = buildCloudBlob(makeAccount(), makeItems(), 8, 10)
  const f = (async (_url: string, init?: RequestInit) => {
    assert.equal(init?.method, 'PUT')
    sent = JSON.parse(String(init?.body)) as Record<string, unknown>
    return jsonResp(200, okRecord(blob, 1))
  }) as typeof fetch
  const r = await putVault(opts({ fetchImpl: f }), blob, 0)
  assert.equal(r.revision, 1)
  assert.equal(sent['expected_revision'], 0)
  assert.equal(sent['schema_version'], 1)
  assert.equal(sent['updated_by_device'], 'web-test')
  assert.deepEqual(sent['value'], blob)
  assert.ok(!JSON.stringify(sent).includes('vaultKey'))
})

test('未配置 base 时请求失败为 NOT_CONFIGURED（不发起网络）', async () => {
  const f = (async () => { throw new Error('should not be called') }) as typeof fetch
  await assert.rejects(
    () => fetchVault(opts({ base: '', fetchImpl: f })),
    (e: unknown) => e instanceof CloudError && e.code === 'NOT_CONFIGURED',
  )
})
