/**
 * @vault/crypto —— 可移植加密核心（零依赖、零 DOM、零网络）
 *
 * 本文件由示例 index.html 的 VC 对象逐函数原样搬运，算法、常量与字节处理
 * 完全一致，仅补 TypeScript 类型与 ES module 导出。改动前请跑 tests/crypto.test.ts
 * 的已知答案向量（KAT），确保密文格式向后兼容。
 *
 * 仅依赖：crypto.getRandomValues、crypto.subtle、btoa/atob、TextEncoder/Decoder
 * 密文格式：{iv,ct} base64、AES-256-GCM、PBKDF2-SHA256 600k
 */
import type {
  Account,
  BackupDoc,
  GeneratedPassword,
  HealthResult,
  PasswordOptions,
  PlainItem,
  PlainItems,
  PendingVault,
  RecoveryBlock,
  SealedRecord,
  StoredItems,
} from './types.ts'

export const ITER = 600000

const ENC = new TextEncoder()
const DEC = new TextDecoder()

function rnd(n: number): Uint8Array {
  return globalThis.crypto.getRandomValues(new Uint8Array(n))
}
function now(): number {
  return Date.now()
}
function hex(u: Uint8Array): string {
  return Array.from(u, function (b) {
    return b.toString(16).padStart(2, '0')
  }).join('')
}
function b64(u: Uint8Array): string {
  let s = ''
  for (let i = 0; i < u.length; i++) s += String.fromCharCode(u[i]!)
  return globalThis.btoa(s)
}
function unb64(x: string): Uint8Array {
  const s = globalThis.atob(x)
  const u = new Uint8Array(s.length)
  for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i)
  return u
}
function uuid(): string {
  const b = rnd(16)
  b[6] = (b[6]! & 15) | 64
  b[8] = (b[8]! & 63) | 128
  const h = hex(b)
  return h.slice(0, 8) + '-' + h.slice(8, 12) + '-' + h.slice(12, 16) + '-' + h.slice(16, 20) + '-' + h.slice(20)
}

async function derive(secret: string, salt: Uint8Array): Promise<Uint8Array> {
  const km = await globalThis.crypto.subtle.importKey('raw', ENC.encode(secret), 'PBKDF2', false, ['deriveBits'])
  const bits = await globalThis.crypto.subtle.deriveBits(
    { name: 'PBKDF2', hash: 'SHA-256', salt: salt as BufferSource, iterations: ITER },
    km,
    256,
  )
  return new Uint8Array(bits)
}
async function importAes(keyBytes: Uint8Array): Promise<CryptoKey> {
  return globalThis.crypto.subtle.importKey('raw', keyBytes as BufferSource, 'AES-GCM', false, ['encrypt', 'decrypt'])
}
async function seal(keyBytes: Uint8Array, data: Uint8Array): Promise<SealedRecord> {
  const iv = rnd(12)
  const k = await importAes(keyBytes)
  const buf = await globalThis.crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv as BufferSource, tagLength: 128 }, k, data as BufferSource)
  return { iv: b64(iv), ct: b64(new Uint8Array(buf)) }
}
async function unseal(keyBytes: Uint8Array, rec: SealedRecord): Promise<Uint8Array> {
  const k = await importAes(keyBytes)
  const buf = await globalThis.crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: unb64(rec.iv) as BufferSource, tagLength: 128 },
    k,
    unb64(rec.ct) as BufferSource,
  )
  return new Uint8Array(buf)
}
async function encryptJSON(vk: Uint8Array, obj: unknown): Promise<SealedRecord> {
  return seal(vk, ENC.encode(JSON.stringify(obj)))
}
async function decryptJSON(vk: Uint8Array, rec: SealedRecord): Promise<unknown> {
  return JSON.parse(DEC.decode(await unseal(vk, rec))) as unknown
}

/** Crockford Base32：去掉易混淆的 I/L/O/U，用户抄写不易错 */
const CROCK = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
function genRecovery(): string {
  const b = rnd(20)
  let out = ''
  let acc = 0
  let bits = 0
  for (let i = 0; i < b.length; i++) {
    acc = (acc << 8) | b[i]!
    bits += 8
    while (bits >= 5) {
      bits -= 5
      out += CROCK[(acc >> bits) & 31]
    }
    acc &= (1 << bits) - 1
  }
  return out.match(/.{1,4}/g)!.join('-')
}
function normCode(s: string): string {
  return String(s || '')
    .toUpperCase()
    .replace(/O/g, '0')
    .replace(/[IL]/g, '1')
    .replace(/[^0-9A-Z]/g, '')
}

/** 创建保险库：vaultKey 随机生成，由主密码与恢复码各包裹一份，永不以明文落盘 */
async function makeVault(masterPassword: string): Promise<PendingVault> {
  const salt = rnd(16)
  const rSalt = rnd(16)
  const vk = rnd(32)
  const kek = await derive(masterPassword, salt)
  const wrapped = await seal(kek, vk)
  const code = genRecovery()
  const rkek = await derive(normCode(code), rSalt)
  const rwrapped = await seal(rkek, vk)
  const account: Account = {
    v: 1,
    app: 'safekeep-local',
    mode: 'local',
    createdAt: now(),
    salt: b64(salt),
    kdf: { alg: 'PBKDF2-SHA256', iterations: ITER },
    wrapped: wrapped,
    recovery: { salt: b64(rSalt), iv: rwrapped.iv, ct: rwrapped.ct } as RecoveryBlock,
    lastBackupAt: null,
  }
  return { account: account, recoveryCode: code, vk: vk }
}
async function unwrap(secret: string, account: Account, useRecovery: boolean): Promise<Uint8Array> {
  const salt = unb64(useRecovery ? account.recovery.salt : account.salt)
  const material = useRecovery ? normCode(secret) : secret
  const kek = await derive(material, salt)
  const rec: SealedRecord = useRecovery
    ? { iv: account.recovery.iv, ct: account.recovery.ct }
    : account.wrapped
  const vk = await unseal(kek, rec)
  if (vk.length !== 32) throw new Error('vaultKey 长度异常')
  return vk
}
/** 改主密码：只重新包裹同一把 vaultKey，所有条目密文原样不动 */
async function rewrap(vk: Uint8Array, newPassword: string): Promise<{ salt: string; wrapped: SealedRecord }> {
  const salt = rnd(16)
  const kek = await derive(newPassword, salt)
  return { salt: b64(salt), wrapped: await seal(kek, vk) }
}
async function refreshRecovery(vk: Uint8Array): Promise<{ code: string; recovery: RecoveryBlock }> {
  const code = genRecovery()
  const rSalt = rnd(16)
  const rkek = await derive(normCode(code), rSalt)
  const rwrapped = await seal(rkek, vk)
  return { code: code, recovery: { salt: b64(rSalt), iv: rwrapped.iv, ct: rwrapped.ct } }
}

const WORDS = (
  'amber anchor apple arbor atlas aurora autumn beacon berry birch bloom brass breeze brook cedar cherry cliff cloud coast coral cove dawn delta drift dune eagle ember fable falcon fern field flame flora frost garden glade harbor haze heron hill ivory jade juniper lagoon lantern leaf lunar maple meadow mist moss nebula north oak ocean olive orbit orchid pebble pine plume quartz rain raven reef river robin ruby sage shore silver slate snow solar spruce stone storm summit thorn tide timber valley velvet violet willow winter'
).split(' ')
/** 拒绝采样，避免取模偏置；返回真实熵值，不虚标强度 */
function genPassword(opts: PasswordOptions = {}): GeneratedPassword {
  if (opts.phrase) {
    const n = Math.max(3, Math.min(10, opts.length || 6))
    const buf = rnd(n * 2)
    const out: string[] = []
    for (let i = 0; i < n; i++) out.push(WORDS[buf[i]! % WORDS.length]!)
    const suffix = opts.digits ? (rnd(1)[0]! % 100).toString().padStart(2, '0') : ''
    return {
      value: out.join('-') + (suffix ? '-' + suffix : ''),
      entropy: Math.round(n * Math.log2(WORDS.length) + (suffix ? 6.6 : 0)),
      charset: WORDS.length,
    }
  }
  const len = Math.max(6, Math.min(64, opts.length || 20))
  const sets: string[] = []
  if (opts.upper !== false) sets.push('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
  if (opts.lower !== false) sets.push('abcdefghijklmnopqrstuvwxyz')
  if (opts.digits !== false) sets.push('0123456789')
  if (opts.symbols !== false) sets.push('!@#$%^&*()-_=+[]{};:,.?')
  let chars = sets.join('')
  if (opts.exclude) chars = chars.replace(/[1lI0OoS5Z2]/g, '')
  if (!chars.length) chars = 'abcdefghijklmnopqrstuvwxyz'
  if (chars.length > 256) chars = chars.slice(0, 256)
  const lim = Math.floor(256 / chars.length) * chars.length
  let str = ''
  let buf2 = rnd(len * 3)
  let bi = 0
  while (str.length < len) {
    if (bi >= buf2.length) {
      buf2 = rnd(len * 3)
      bi = 0
    }
    const b = buf2[bi++]!
    if (b >= lim) continue
    str += chars[b % chars.length]
  }
  return { value: str, entropy: Math.round(len * Math.log2(chars.length)), charset: chars.length }
}

/** 纯判据：绝对时间戳，不累计计时（后台定时器会被节流） */
function shouldLock(nowTs: number, lastActivityTs: number, idleMs: number, hidden: boolean): boolean {
  if (hidden) return true
  if (!idleMs) return false
  return nowTs - lastActivityTs >= idleMs
}

function health(list: PlainItem[]): HealthResult {
  const live = list.filter(function (p) {
    return !p._deleted
  })
  const withPw = live.filter(function (p) {
    return p.fields && p.fields.password
  })
  const weakItems = withPw.filter(function (p) {
    return String(p.fields.password).length < 12
  })
  const counts: Record<string, number> = {}
  withPw.forEach(function (p) {
    const k = p.fields.password!
    counts[k] = (counts[k] || 0) + 1
  })
  const reuseItems = withPw.filter(function (p) {
    return counts[p.fields.password!] > 1
  })
  const cutoff = now() - 180 * 86400000
  const oldItems = withPw.filter(function (p) {
    return (p.updatedAt || 0) < cutoff
  })
  const score = Math.max(0, 100 - weakItems.length * 8 - reuseItems.length * 6 - oldItems.length * 3)
  return {
    total: live.length,
    withPw: withPw.length,
    weak: weakItems.length,
    reused: reuseItems.length,
    old: oldItems.length,
    score: score,
    weakItems: weakItems,
    reuseItems: reuseItems,
    oldItems: oldItems,
  }
}

function buildBackup(account: Account, items: StoredItems, rev: number): string {
  const doc: BackupDoc = { app: 'safekeep-backup', v: 1, exportedAt: now(), account: account, rev: rev || 0, items: items }
  return JSON.stringify(doc, null, 2)
}
function parseBackup(text: string): BackupDoc {
  let d: Partial<BackupDoc>
  try {
    d = JSON.parse(text) as Partial<BackupDoc>
  } catch (e) {
    throw new Error('文件不是有效的 JSON')
  }
  if (!d || d.app !== 'safekeep-backup' || !d.account || d.account.app !== 'safekeep-local' || !d.items)
    throw new Error('不是锦囊的加密备份文件')
  if (!d.account.wrapped || !d.account.salt || !d.account.kdf || !d.account.recovery)
    throw new Error('备份结构损坏或版本不兼容')
  return d as BackupDoc
}

export {
  rnd,
  now,
  hex,
  b64,
  unb64,
  uuid,
  derive,
  seal,
  unseal,
  encryptJSON,
  decryptJSON,
  genRecovery,
  normCode,
  makeVault,
  unwrap,
  rewrap,
  refreshRecovery,
  genPassword,
  shouldLock,
  health,
  buildBackup,
  parseBackup,
}

/** 类型重导出，便于 service / 视图单一来源导入 */
export type { PlainItems }
