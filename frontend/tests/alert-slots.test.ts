/**
 * UI 插槽静态守卫（node --test，无 DOM / 无浏览器）。
 *
 * 回归背景：TDesign Vue Next 的 `t-alert` 操作区插槽叫 `operation`，
 * 代码里误写成 Element Plus 习惯的 `#action`，Vue 会**静默丢弃**整个插槽内容，
 * 于是「确认继续？」只显示文字、确认/取消按钮一个都不渲染；触发按钮又被 v-else
 * 隐藏，用户点完云端恢复就再也无任何可点元素 —— 本地流程彻底断死。
 *
 * 这类缺陷不会报错、类型检查与业务单测也发现不了，只能靠模板静态断言兜住。
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = resolve(fileURLToPath(new URL('../src', import.meta.url)))

function vueFiles(dir: string): string[] {
  const out: string[] = []
  for (const name of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, name.name)
    if (name.isDirectory()) out.push(...vueFiles(p))
    else if (name.name.endsWith('.vue')) out.push(p)
  }
  return out
}

function read(rel: string): string {
  return readFileSync(join(SRC, rel), 'utf8')
}

/** 取出模板里所有 t-alert 块（含开闭标签），用于逐块检查。 */
function alertBlocks(text: string): string[] {
  return text.match(/<t-alert[\s\S]*?<\/t-alert>/g) ?? []
}

test('禁止使用 TDesign 不存在的 #action 插槽（会被静默丢弃）', () => {
  const offenders = vueFiles(SRC)
    .filter((f) => /<template\s+#action\b/.test(readFileSync(f, 'utf8')))
    .map((f) => f.replace(SRC, 'src'))
  assert.deepEqual(
    offenders,
    [],
    `这些文件用了 t-alert 不支持的 #action，按钮不会渲染：${offenders.join(', ')}`,
  )
})

test('所有「确认继续？」二次确认条都用 #operation 且带可执行按钮', () => {
  const files = ['views/SafeKeepView.vue', 'components/dialogs/AccountDialog.vue']
  let checked = 0
  for (const f of files) {
    for (const block of alertBlocks(read(f))) {
      if (!block.includes('确认继续？')) continue
      checked++
      assert.match(block, /<template\s+#operation>/, `${f} 的二次确认条缺少 #operation 插槽`)
      assert.match(block, /@click=/, `${f} 的二次确认按钮没有绑定点击事件`)
      assert.match(block, /取消</, `${f} 的二次确认条缺少「取消」出口`)
    }
  }
  assert.equal(checked, 3, '应覆盖解锁页云端恢复 + 账号弹窗强制上传/拉取三处二次确认')
})

test('解锁页云端恢复确认条：确认按钮调用 onCloudRestore(true)', () => {
  const blocks = alertBlocks(read('views/SafeKeepView.vue'))
    .filter((b) => b.includes('确认继续？') && b.includes('云端密文覆盖'))
  assert.equal(blocks.length, 1)
  assert.match(blocks[0]!, /@click="onCloudRestore\(true\)"/)
})

test('备份提醒的操作按钮也走 #operation，不能被丢弃', () => {
  const block = alertBlocks(read('views/SafeKeepView.vue')).find((b) => b.includes('立即导出备份'))
  assert.ok(block, '未找到备份提醒 alert')
  assert.match(block, /<template\s+#operation>/)
  assert.match(block, /立即导出备份/)
})
