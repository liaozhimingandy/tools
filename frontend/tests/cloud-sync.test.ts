/**
 * 云端同步纯逻辑测试：聚焦「内容签名」判重（修复「上传相同内容版本号也+1」）。
 * 运行：node --test tests/cloud-sync.test.ts
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { blobContentSig, buildCloudBlob } from '../src/services/cloud/sync.ts'
import type { CloudVaultBlob } from '../src/services/cloud/types.ts'

function makeBlob(savedAt: number): CloudVaultBlob {
  return buildCloudBlob(
    { app: 'safekeep-local', wrapped: 'W1', salt: 'S1', kdf: { n: 1 }, recovery: { wrapped: 'R1', salt: 'S2', kdf: { n: 1 } } } as never,
    { a: { iv: 'iv-a', ct: 'ct-a' } } as never,
    5,
    savedAt,
  )
}

test('内容签名：相同内容恒定且确定性', () => {
  const b1 = makeBlob(1000)
  const b2 = makeBlob(1000)
  const s1 = blobContentSig(b1)
  const s2 = blobContentSig(b2)
  assert.equal(s1, s2, '相同内容签名必须一致')
  assert.match(s1, /^[0-9a-f]{8}$/, '签名应为 8 位十六进制')
})

test('内容签名：仅 savedAt 不同应被视为相同内容', () => {
  const b1 = makeBlob(1000)
  const b2 = makeBlob(999999) // 只有时间戳不同
  assert.equal(blobContentSig(b1), blobContentSig(b2), '排除 savedAt 后签名应一致')
})

test('内容签名：account / items / rev 任一变化都应得到不同签名', () => {
  const base = makeBlob(1000)

  const accChanged = { ...base, account: { ...base.account, wrapped: 'W2' } } as CloudVaultBlob
  assert.notEqual(blobContentSig(base), blobContentSig(accChanged), 'account 变化应改变签名')

  const itemsChanged = { ...base, items: { ...base.items, b: { iv: 'iv-b', ct: 'ct-b' } } } as CloudVaultBlob
  assert.notEqual(blobContentSig(base), blobContentSig(itemsChanged), 'items 变化应改变签名')

  const revChanged = { ...base, rev: 6 } as CloudVaultBlob
  assert.notEqual(blobContentSig(base), blobContentSig(revChanged), 'rev 变化应改变签名')
})
