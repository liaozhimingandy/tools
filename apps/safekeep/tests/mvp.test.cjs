// 第一版 MVP 全链路回归测试
// 直接读取 index.html 中的真实内联脚本执行，避免测试实现与产品实现分叉。
// 覆盖：加密核心 KAT + 本地闭环（创建→恢复码→CRUD→备份→锁定→解锁→改主密码→清空）。
const fs = require('fs');
const path = require('path');
const { webcrypto } = require('node:crypto');
const assert = require('node:assert/strict');

global.crypto = webcrypto;
global.btoa = s => Buffer.from(s, 'binary').toString('base64');
global.atob = s => Buffer.from(s, 'base64').toString('binary');

/* ---------- 最小 DOM 模拟 ---------- */
const els = new Map();
function makeEl(id) {
  return {
    id, value: '', checked: false, disabled: false, type: '', className: '', style: {}, files: [],
    _text: '', _html: '',
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    addEventListener() {}, removeEventListener() {}, setAttribute() {},
    getAttribute(k) { return this['_attr_' + k] === undefined ? null : this['_attr_' + k]; },
    hasAttribute(k) { return this['_attr_' + k] !== undefined; },
    closest() { return null; }, querySelector() { return makeEl('sub'); },
    appendChild() {}, removeChild() {}, remove() {}, focus() {}, select() {}, click() {},
    get textContent() { return this._text; }, set textContent(v) { this._text = String(v); },
    get innerHTML() { return this._html; }, set innerHTML(v) { this._html = String(v); }
  };
}
function $(id) {
  if (!els.has(id)) els.set(id, makeEl(id));
  return els.get(id);
}
const screens = ['s-welcome', 's-recovery', 's-locked', 's-vault'].map(makeEl);
const sideBtns = ['all', 'fav', 'trash'].map(v => { const e = makeEl('view-' + v); e['_attr_data-view'] = v; return e; });
const side = makeEl('side');
function makeStorage() {
  const m = new Map();
  return {
    getItem: k => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
    removeItem: k => m.delete(k),
    clear: () => m.clear(),
    _dump: () => [...m.entries()].map(([k, v]) => k + '=' + v).join('\n')
  };
}
global.localStorage = makeStorage();
let clipContent = '';
// Node 22 的全局 navigator 是只读访问器，直接赋值不会生效，必须 defineProperty。
Object.defineProperty(globalThis, 'navigator', { configurable: true, writable: true, value: {
  clipboard: {
    writeText: async (t) => { clipContent = t; },
    readText: async () => clipContent
  }
} });
global.document = {
  hidden: false,
  getElementById: $,
  querySelector: sel => (sel === '.side' ? side : makeEl('q')),
  querySelectorAll: sel => (sel === '.screen' ? screens : sel.indexOf('[data-view]') >= 0 ? sideBtns : []),
  addEventListener() {}, execCommand() {},
  body: { appendChild() {}, removeChild() {} },
  createElement: () => makeEl('tmp')
};
global.window = { crypto: webcrypto, addEventListener() {}, open: () => null };
global.setInterval = () => 0;
global.clearInterval = () => {};
const realTimeout = global.setTimeout;
global.setTimeout = (fn, ms, ...args) => (ms > 200 ? 0 : realTimeout(fn, ms, ...args));

/* ---------- 注入测试导出（生产文件本身不暴露任何句柄） ---------- */
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(m, 'index.html 中应能找到内联脚本');
const src = m[1].replace('/* TEST_EXPORT_SLOT */', `
  globalThis.__api = { VC, S, $, LS, getAccount, getItems, curRev, createVault, confirmRecovery,
    unlock, lockVault, saveItem, deleteItem, restoreItem, toggleFav, openEditor, openChangePw,
    render, buildBackupText, applyBackup, bootLocked, getPrefs, newPlain, copyWithClear };
`);
assert.ok(src.includes('globalThis.__api'), '测试导出应注入成功');
new Function(src)();
const api = globalThis.__api;
assert.ok(api, '脚本应成功初始化');

const PW = 'correct horse battery staple 2026';
const TITLE = '中文站点·测试 GitHub';
const SECRET = 'Zh0ngWen-P@ssw0rd-2026';

function rawStorage() { return global.localStorage._dump(); }
async function addItem(over) {
  const p = Object.assign(api.newPlain(), { title: TITLE, fields: { username: 'tester@example.com', password: SECRET, totp: '' },
    urls: ['https://github.com'], note: '包含中文的备注', tags: ['工作', '开发'] }, over || {});
  await api.saveItem(p);
  return p;
}

(async () => {
  /* ===== 1. 加密核心 KAT ===== */
  const made = await api.VC.makeVault(PW);
  assert.equal(made.vk.length, 32, 'vaultKey 应为 32 字节');
  assert.ok(await api.VC.unwrap(PW, made.account, false), '主密码应解开 wrappedKey');
  assert.ok(await api.VC.unwrap(made.recoveryCode, made.account, true), '恢复码应解开同一把 vaultKey');
  assert.equal(api.VC.normCode(made.recoveryCode.toLowerCase().replace(/-/g, ' ')),
               api.VC.normCode(made.recoveryCode), '恢复码归一化应忽略大小写与分隔符');
  await assert.rejects(() => api.VC.unwrap('wrong-password', made.account, false), '错误主密码必须被 GCM 拒绝');
  await assert.rejects(() => api.VC.unwrap('WRONG-RECOVERY-CODE', made.account, true), '错误恢复码必须被拒绝');

  const plain = { title: TITLE, fields: { password: SECRET }, urls: ['https://github.com'], updatedAt: Date.now() };
  const c1 = await api.VC.encryptJSON(made.vk, plain);
  const c2 = await api.VC.encryptJSON(made.vk, plain);
  assert.notEqual(c1.iv, c2.iv, '每次加密必须重新随机 IV');
  assert.notEqual(c1.ct, c2.ct, '相同明文两次加密的密文必须不同');
  assert.deepEqual(await api.VC.decryptJSON(made.vk, c1), plain, '密文应可完整还原（含中文与元数据）');
  const blob = c1.ct + c1.iv + JSON.stringify(made.account);
  assert.ok(!blob.includes('GitHub') && !blob.includes(SECRET) && !blob.includes('中文'),
            '密文与账户记录中不得出现任何明文元数据');
  const tampered = { iv: c1.iv, ct: c1.ct.slice(0, -8) + 'AAAAAAAA' };
  await assert.rejects(() => api.VC.decryptJSON(made.vk, tampered), '篡改密文必须被 GCM 认证拒绝');

  const rw = await api.VC.rewrap(made.vk, 'a-brand-new-master-password');
  const acct2 = Object.assign({}, made.account, { salt: rw.salt, wrapped: rw.wrapped });
  assert.deepEqual(await api.VC.unwrap('a-brand-new-master-password', acct2, false), made.vk, '新主密码应解出同一 vaultKey');
  assert.deepEqual(await api.VC.decryptJSON(made.vk, c1), plain, '改主密码后旧条目密文仍可解（不重加密）');
  await assert.rejects(() => api.VC.unwrap(PW, acct2, false), '旧主密码应立即失效');

  const fresh = await api.VC.refreshRecovery(made.vk);
  const acct3 = Object.assign({}, made.account, { recovery: fresh.recovery });
  assert.ok(await api.VC.unwrap(fresh.code, acct3, true), '新恢复码应可用');
  await assert.rejects(() => api.VC.unwrap(made.recoveryCode, acct3, true), '旧恢复码应作废');

  const g = api.VC.genPassword({ length: 24, exclude: true });
  assert.equal(g.value.length, 24, '生成长度应准确');
  assert.ok(!/[1lI0OoS5Z2]/.test(g.value), '排除易混淆字符后不得再出现这些字符');
  assert.ok(g.entropy > 100, '24 位四类字符应有 >100 bit 熵');
  const g2 = api.VC.genPassword({ length: 24, exclude: true });
  assert.notEqual(g.value, g2.value, '两次生成不应相同');
  const phrase = api.VC.genPassword({ phrase: true, length: 6 });
  assert.ok(phrase.value.split('-').length >= 6, '短语模式应输出多个词');
  assert.ok(phrase.entropy < 60, '短语模式熵值应被如实标低，不虚标');

  assert.equal(api.VC.shouldLock(1000, 500, 600, false), false, '未达空闲阈值不锁定');
  assert.equal(api.VC.shouldLock(1200, 500, 600, false), true, '达到空闲阈值应锁定');
  assert.equal(api.VC.shouldLock(1000, 500, 600, true), true, '切后台应立即锁定');
  assert.equal(api.VC.shouldLock(99999, 0, 0, false), false, '关闭自动锁定时不锁定');

  const hp = api.VC.health([
    { title: 'a', fields: { password: 'short' }, updatedAt: Date.now() },
    { title: 'b', fields: { password: 'short' }, updatedAt: Date.now() },
    { title: 'c', fields: { password: 'AveryLongAndStrongPassword!2026' }, updatedAt: 1 }
  ]);
  assert.equal(hp.weak, 2, '应识别出 2 个弱密码');
  assert.equal(hp.reused, 2, '应识别出 2 条复用');
  assert.equal(hp.old, 1, '应识别出 1 条长期未更新');

  const backupText = api.VC.buildBackup(made.account, { x: { iv: 'a', ct: 'b' } }, 7);
  const parsed = api.VC.parseBackup(backupText);
  assert.equal(parsed.rev, 7, '备份应保留全局 rev');
  assert.throws(() => api.VC.parseBackup('{"app":"other"}'), /不是锦囊/, '应拒绝非锦囊备份');
  assert.throws(() => api.VC.parseBackup('not json'), /JSON/, '应拒绝损坏文件');

  /* ===== 2. 应用层：本地闭环 ===== */
  assert.equal(api.getAccount(), null, '全新环境不应存在账户');
  api.$('newPw').value = PW; api.$('newPw2').value = PW;
  await api.createVault();
  assert.ok(api.S.pending && api.S.pending.recoveryCode, '应生成恢复码');
  const REAL_CODE = api.S.pending.recoveryCode;
  assert.equal(api.getAccount(), null, '关键：确认抄写前绝不落盘，避免刷新留下死库');

  api.$('recoveryConfirm').value = 'WRONG';
  api.confirmRecovery();
  assert.equal(api.getAccount(), null, '恢复码输错不应落盘');
  api.$('recoveryConfirm').value = api.S.pending.recoveryCode.toLowerCase().replace(/-/g, ' ');
  api.confirmRecovery();
  assert.ok(api.getAccount(), '确认后账户应落盘');
  assert.ok(api.S.vk, '创建确认后应直接进入已解锁状态，用户无需再输一次主密码');

  const item = await addItem();
  assert.ok(api.getItems()[item.id], '条目密文应写入本地');
  assert.ok(!rawStorage().includes('GitHub') && !rawStorage().includes(SECRET) && !rawStorage().includes('中文站点'),
            '关键：localStorage 全量内容中不得出现任何条目明文或元数据');
  assert.equal(api.S.plain[item.id].title, TITLE, '内存中应持有可检索的明文');

  // 编辑器真实路径：新增 + 编辑
  api.openEditor(null);
  api.$('eType').value = 'note';
  api.$('eTitle').value = '编辑器新增条目';
  api.$('eUser').value = 'editor-user';
  api.$('ePass').value = 'editor-pass';
  api.$('eUrl').value = '';
  api.$('eNote').value = '来自编辑器';
  api.$('eTags').value = '笔记, 测试';
  api.$('eFav').checked = true;
  await api.$('eSave').onclick();
  const editorItem = Object.values(api.S.plain).find(p => p.title === '编辑器新增条目');
  assert.ok(editorItem, '通过编辑器应能真实新增条目');
  assert.equal(editorItem.favorite, true, '收藏标记应保存');
  assert.ok(editorItem.tags.includes('测试'), '标签解析应支持中文逗号与空格');

  // 搜索 / 标签 / 视图过滤
  api.S.filter = 'github'; api.render();
  assert.ok(api.$('itemList').innerHTML.includes(TITLE), '搜索应命中标题');
  assert.ok(!api.$('itemList').innerHTML.includes('编辑器新增条目'), '搜索应过滤掉不匹配项');
  api.S.filter = ''; api.S.tag = '工作'; api.render();
  assert.ok(api.$('itemList').innerHTML.includes(TITLE), '标签过滤应命中');
  api.S.tag = '';

  // 收藏 / 回收站 / 恢复 / 彻底删除
  await api.toggleFav(item.id);
  assert.equal(api.S.plain[item.id].favorite, true, '收藏状态应切换');
  await api.deleteItem(item.id, false);
  assert.equal(api.getItems()[item.id].deleted, true, '删除应写墓碑而非抹掉密文');
  assert.equal(api.S.plain[item.id]._deleted, true, '内存中应标记已删除');
  assert.ok(!rawStorage().includes(SECRET), '删除过程也不得把明文写进存储');
  await api.restoreItem(item.id);
  assert.equal(api.getItems()[item.id].deleted, false, '恢复应清除墓碑');
  await api.deleteItem(item.id, true);
  assert.equal(api.getItems()[item.id], undefined, '彻底删除应移除密文');

  // 备份 → 模拟换设备导入 → 用原主密码解锁
  const item2 = await addItem({ id: api.VC.uuid(), title: '备份验证条目' });
  const text = api.buildBackupText();
  assert.ok(text.includes('safekeep-backup') && !text.includes(SECRET), '备份文件必须是纯密文');
  Object.keys(api.LS).forEach(k => global.localStorage.removeItem(api.LS[k]));
  api.applyBackup(text, true);
  assert.equal(api.S.vk, null, '导入后应处于锁定态');
  assert.ok(api.getAccount(), '导入后账户应存在');
  const okUnlock = await api.unlock(PW, false);
  assert.equal(okUnlock, true, '用原主密码应能在新设备解开备份');
  assert.equal(api.S.plain[item2.id].title, '备份验证条目', '备份里的条目应完整恢复');
  assert.ok(!rawStorage().includes('备份验证条目'), '导入后依旧不能出现明文');

  // 剪贴板：锁定时清掉本应用复制的值，但绝不误清用户后来复制的内容
  await api.copyWithClear('ours-secret-value');
  assert.equal(clipContent, 'ours-secret-value', '复制应写入剪贴板');
  api.lockVault();
  await new Promise(r => realTimeout(r, 0));
  assert.equal(clipContent, '', '锁定必须清除仍属于本应用的剪贴板内容');
  assert.equal(await api.unlock(PW, false), true, '剪贴板测试后应能重新解锁');
  await api.copyWithClear('ours-second-value');
  clipContent = 'user-copied-other-content';
  api.lockVault();
  await new Promise(r => realTimeout(r, 0));
  assert.equal(clipContent, 'user-copied-other-content', '不得误清用户后来复制的内容');
  await api.unlock(PW, false);

  // 自动锁定：清内存、清 DOM，但密文仍在
  const cipherBefore = JSON.stringify(api.getItems());
  api.lockVault('测试锁定');
  assert.equal(api.S.vk, null, '锁定后内存不得再有 vaultKey');
  assert.equal(Object.keys(api.S.plain).length, 0, '锁定后不得残留明文条目');
  assert.equal(api.$('itemList').innerHTML.includes('已锁定'), true, '锁定后隐藏 DOM 中的明文列表应清空');
  assert.equal(JSON.stringify(api.getItems()), cipherBefore, '锁定不得破坏本地密文');

  // 错误密码 + 正确密码 + 恢复码
  assert.equal(await api.unlock('not-the-password', false), false, '错误主密码应解锁失败');
  assert.equal(api.S.vk, null, '失败后仍应保持锁定');
  assert.equal(await api.unlock(PW, false), true, '正确主密码应解锁成功');
  assert.equal(api.S.failCount, 0, '成功解锁应重置失败计数');
  api.lockVault();
  assert.equal(await api.unlock(REAL_CODE.toLowerCase().replace(/-/g, ' '), true), true, '真实恢复码（归一化后）应能解锁');
  assert.equal(api.S.plain[item2.id].title, '备份验证条目', '恢复码解锁后数据应完整');
  api.lockVault();

  // 改主密码：只重包裹密钥，条目密文不变
  assert.equal(await api.unlock(PW, false), true, '恢复码解锁后原主密码仍应有效');
  const before = JSON.stringify(api.getItems());
  api.openChangePw(false);
  api.$('cpPw').value = 'my-new-master-pass-2026'; api.$('cpPw2').value = 'my-new-master-pass-2026';
  await api.$('cpSave').onclick();
  assert.equal(JSON.stringify(api.getItems()), before, '改主密码不得重加密任何条目');
  api.lockVault();
  assert.equal(await api.unlock(PW, false), false, '旧主密码应失效');
  assert.equal(await api.unlock('my-new-master-pass-2026', false), true, '新主密码应可用');
  assert.equal(api.S.plain[item2.id].title, '备份验证条目', '改密后数据仍完整');

  assert.equal(api.VC.ITER, 600000, '应保留 PBKDF2 600k');
  assert.equal(typeof api.copyWithClear, 'function', '复制能力应可用');

  console.log('ALL_MVP_TESTS_PASSED');
  console.log('  crypto : wrap/unwrap, GCM integrity, IV uniqueness, metadata encryption, rewrap, recovery rotation, KDF params');
  console.log('  flow   : create -> recovery -> CRUD -> search/tag/fav -> trash -> restore -> backup -> import -> lock -> unlock -> change master pw');
  console.log('  assert : localStorage contains ciphertext only; lock clears memory + DOM but keeps ciphertext');
})().catch(e => { console.error('MVP_TEST_FAILED:', e.stack || e.message); process.exit(1); });
