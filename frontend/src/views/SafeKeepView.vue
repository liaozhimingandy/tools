<script setup lang="ts">
/** 锦囊 SafeKeep 主视图。状态与副作用由 useSafeKeep 编排，本组件只做渲染与事件转发。 */
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import {
  LockOnIcon, SearchIcon, AddIcon, RefreshIcon, CloudIcon, SettingIcon, FileIcon,
  SecuredIcon, KeyIcon, RollbackIcon,
} from 'tdesign-icons-vue-next'
import { useSafeKeep } from '@/composables/useSafeKeep.ts'
import { TYPE_NAME } from '@/services/safekeep/vault.ts'
import { getItems, curRev, browserStorage as browser } from '@/services/safekeep/storage.ts'
import ItemEditorDialog from '@/components/dialogs/ItemEditorDialog.vue'
import SettingsDialog from '@/components/dialogs/SettingsDialog.vue'
import ChangePwDialog from '@/components/dialogs/ChangePwDialog.vue'
import NewRecoveryDialog from '@/components/dialogs/NewRecoveryDialog.vue'
import GeneratorDialog from '@/components/dialogs/GeneratorDialog.vue'
import HealthDialog from '@/components/dialogs/HealthDialog.vue'
import BackupDialog from '@/components/dialogs/BackupDialog.vue'
import AccountDialog from '@/components/dialogs/AccountDialog.vue'
import StorageDialog from '@/components/dialogs/StorageDialog.vue'
import type { PlainItem } from '@/services/safekeep/types.ts'

const sk = useSafeKeep()

// 表单局部状态
const newPw = ref('')
const newPw2 = ref('')
const recoveryConfirm = ref('')
const recoverPw = ref('')
const recoverCode = ref('')
const lockedByCode = ref(false)
const pwStrength = computed(() => Math.min(100, newPw.value.length * 5 + (/[A-Z]/.test(newPw.value) ? 10 : 0) + (/\d/.test(newPw.value) ? 10 : 0) + (/[^A-Za-z0-9]/.test(newPw.value) ? 10 : 0)))
const pwHint = computed(() => newPw.value.length < 10 ? '至少 10 位，建议用一句长口令' : pwStrength.value < 60 ? '偏弱，建议加长或加入更多字符类型' : '长度不错，记得用恢复码兜底')
const pwBarColor = computed(() => pwStrength.value < 45 ? 'var(--color-warn)' : pwStrength.value < 75 ? '#b26a00' : 'var(--color-brand)')

function fmtTime(ts: number | null | undefined): string {
  return ts ? new Date(ts).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '从未'
}
function doUnlock(recovery: boolean): void {
  void sk.unlock(recovery ? recoverCode.value : recoverPw.value, recovery)
  if (!recovery) recoverPw.value = ''
}
function download(name: string, text: string): void {
  const blob = new Blob([text], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
function onExport(): void {
  const text = sk.exportBackupText()
  const d = new Date()
  const stamp = d.getFullYear() + String(d.getMonth() + 1).padStart(2, '0') + String(d.getDate()).padStart(2, '0')
  download('锦囊备份-' + stamp + '.json', text)
  sk.dialog.value = null
  sk.toast('加密备份已导出，请离线妥善保存')
}
function onImport(text: string, force: boolean): void {
  try {
    sk.importBackupText(text, force)
  } catch (e) {
    if ((e as Error).message !== 'CONFIRM_OVERWRITE') sk.toast('导入失败：' + (e as Error).message)
    else throw e
  }
}
function onEditorSave(item: PlainItem): void {
  void sk.save(item).then(() => (sk.dialog.value = null))
}
function onCopy(text: string): void {
  void sk.copyWithClear(text)
}
function onUsePassword(value: string): void {
  sk.newEntry(value) // 预填生成器密码，走同一条"新增"路径
}
function onWipe(): void {
  sk.dialog.value = null
  sk.wipe()
}
function revealToggle(id: string): void {
  sk.revealed[id] = !sk.revealed[id]
}
/** 存储自检：只读快照。computed 保证模板多次引用只算一次。 */
const storageFacts = computed(() => {
  const items = getItems(browser())
  const keys = Object.keys(items)
  return {
    raw: sk.storageRaw(),
    count: keys.length,
    rev: curRev(browser()),
    recent: keys.slice(-6).reverse().map((id) => {
      const r = items[id]!
      return { id, rev: r.rev, deleted: r.deleted, iv: r.iv, ct: r.ct }
    }),
  }
})

// 锁定后清空恢复码输入，避免残留在内存
watch(() => sk.screen.value, (s) => {
  if (s === 'locked' && lockedByCode.value) recoverCode.value = ''
})
</script>

<template>
  <div>
    <!-- 顶栏 -->
    <header class="topbar">
      <div class="brand"><RouterLink to="/">tools</RouterLink> · 锦<span class="text-brand">囊</span></div>
      <t-tag size="small" variant="light" :theme="sk.cloud.canSync.value ? 'success' : 'default'">
        {{ sk.cloud.statusText.value }}
      </t-tag>
      <div class="sp"></div>
      <span class="cd">{{ sk.countdown.value }}</span>
      <t-tag size="small" :variant="sk.unlocked.value ? 'light' : 'outline'" :theme="sk.unlocked.value ? 'primary' : 'default'">{{ sk.statusText.value }}</t-tag>
      <t-button v-if="sk.unlocked.value" size="small" variant="text" @click="sk.lock('已手动锁定')">锁定</t-button>
    </header>

    <div class="app">
      <!-- 欢迎 / 创建 -->
      <section v-if="sk.screen.value === 'welcome'" class="auth-card">
        <div class="auth-icon"><LockOnIcon size="26px" /></div>
        <h1>创建本地保险库</h1>
        <p class="auth-desc">免注册、免登录。所有条目在这台设备上加密后写入浏览器本地存储，不会上传到任何服务器。</p>
        <label class="field-label">主密码（解锁的唯一钥匙）</label>
        <t-input v-model="newPw" type="password" autocomplete="new-password" placeholder="至少 10 位，建议用一句长口令" />
        <div class="strength"><i :style="{ width: pwStrength + '%', background: pwBarColor }"></i></div>
        <p class="hint">{{ pwHint }}</p>
        <label class="field-label">确认主密码</label>
        <t-input v-model="newPw2" type="password" autocomplete="new-password" placeholder="再次输入主密码" />
        <t-alert theme="warning" class="my-4">
          <template #message>下一步会给你一组<b>恢复码</b>，请抄写在纸上。它和主密码是两把独立的钥匙，任何一把都能解开保险库。</template>
        </t-alert>
        <div class="flex gap-2">
          <t-button theme="primary" class="flex-1" @click="sk.create(newPw, newPw2)">创建保险库</t-button>
          <t-button theme="default" variant="outline" class="flex-1" @click="sk.dialog.value = 'backup'">从备份恢复</t-button>
        </div>
        <p class="hint">本版本为本地 MVP：数据只保存在当前浏览器。清理浏览器数据、换设备或换浏览器都会丢失，请定期用「备份与恢复」导出加密备份文件。</p>
      </section>

      <!-- 恢复码确认 -->
      <section v-else-if="sk.screen.value === 'recovery'" class="auth-card">
        <div class="auth-icon"><KeyIcon size="26px" /></div>
        <h1>抄写恢复码</h1>
        <p class="auth-desc">这是忘记主密码时唯一的后路。它只显示这一次，请现在抄到纸上并妥善保管。</p>
        <div class="recovery">{{ sk.pendingRecoveryCode.value }}</div>
        <t-alert id="recoveryNote" theme="warning" class="my-4">
          <template #message>尚未写入磁盘：确认抄写之前刷新页面，不会留下一个解不开的空库。</template>
        </t-alert>
        <label class="field-label">输入恢复码以确认（忽略连字符，O 按 0、I/L 按 1 处理）</label>
        <t-input v-model="recoveryConfirm" class="code-input" placeholder="粘贴或输入恢复码" autocomplete="off" :spellcheck="false" @enter="sk.confirmRecovery(recoveryConfirm)" />
        <div class="flex mt-5">
          <t-button theme="primary" block @click="sk.confirmRecovery(recoveryConfirm)">我已抄写，启用保险库</t-button>
        </div>
      </section>

      <!-- 锁定 / 解锁 -->
      <section v-else-if="sk.screen.value === 'locked'" class="auth-card">
        <div class="auth-icon"><LockOnIcon size="26px" /></div>
        <h1>解锁保险库</h1>
        <p class="auth-desc">数据仍以密文形式保存在本机，输入主密码后才会解密。</p>
        <template v-if="!lockedByCode">
          <label class="field-label">主密码</label>
          <t-input v-model="recoverPw" type="password" autocomplete="current-password" @enter="doUnlock(false)" />
          <div class="flex mt-5">
            <t-button theme="primary" block @click="doUnlock(false)">解锁</t-button>
          </div>
          <p class="hint"><a href="#" @click.prevent="lockedByCode = true">忘记主密码？用恢复码解锁</a></p>
        </template>
        <template v-else>
          <label class="field-label">恢复码</label>
          <t-input v-model="recoverCode" class="code-input" placeholder="输入恢复码" autocomplete="off" :spellcheck="false" @enter="doUnlock(true)" />
          <div class="flex gap-2 mt-5">
            <t-button theme="primary" class="flex-1" @click="doUnlock(true)">用恢复码解锁</t-button>
            <t-button theme="default" variant="outline" class="flex-1" @click="lockedByCode = false">返回</t-button>
          </div>
        </template>
        <t-alert v-if="sk.failHint.value" theme="error" class="my-4">
          <template #message>{{ sk.failHint.value }}</template>
        </t-alert>
        <p class="hint">连续输错会增加等待时间。本地模式没有服务端限流，真正抵御离线爆破靠的是主密码强度与 PBKDF2 600k 迭代。</p>
        <t-divider class="my-4" />
        <t-button variant="text" block @click="sk.dialog.value = 'backup'">从加密备份文件恢复</t-button>
      </section>

      <!-- 主界面 -->
      <section v-else>
        <t-alert v-if="sk.needBackup.value" theme="warning" class="mb-4" :closable="false">
          <template #message>
            {{ sk.account.value?.lastBackupAt ? '距上次导出备份已超过 7 天（' + fmtTime(sk.account.value.lastBackupAt) + '）。本地存储可能被浏览器清理，请导出一份加密备份。' : '还没有导出过备份。本版本数据只存在这台设备，建议现在导出一份加密备份文件。' }}
          </template>
          <template #action>
            <t-button size="small" theme="warning" @click="sk.dialog.value = 'backup'">立即导出备份</t-button>
          </template>
        </t-alert>

        <div class="vault-layout">
          <aside class="side">
            <div class="side-title">条目</div>
            <button :class="{ on: sk.view.value === 'all' }" @click="sk.view.value = 'all'; sk.tag.value = ''">全部条目 <i>{{ sk.counts.value.all }}</i></button>
            <button :class="{ on: sk.view.value === 'fav' }" @click="sk.view.value = 'fav'; sk.tag.value = ''">收藏 <i>{{ sk.counts.value.fav }}</i></button>
            <button :class="{ on: sk.view.value === 'trash' }" @click="sk.view.value = 'trash'; sk.tag.value = ''">回收站 <i>{{ sk.counts.value.trash }}</i></button>
            <t-divider />
            <div class="side-title">类型</div>
            <button v-for="t in sk.typeNav.value" :key="t.type" :class="{ on: sk.view.value === 'type:' + t.type }" @click="sk.view.value = 'type:' + t.type; sk.tag.value = ''">{{ t.name }} <i>{{ t.count }}</i></button>
            <t-divider />
            <div class="side-title">标签</div>
            <template v-if="sk.tagNav.value.length">
              <button v-for="t in sk.tagNav.value" :key="t.tag" :class="{ on: sk.tag.value === t.tag }" @click="sk.tag.value = sk.tag.value === t.tag ? '' : t.tag; sk.view.value = 'all'">{{ t.tag }} <i>{{ t.count }}</i></button>
            </template>
            <p v-else class="side-empty">还没有标签</p>
            <t-divider />
            <div class="side-title">工具与数据</div>
            <button @click="sk.dialog.value = 'generator'"><RefreshIcon /> 密码生成器</button>
            <button @click="sk.dialog.value = 'health'"><SecuredIcon /> 安全体检</button>
            <button @click="sk.dialog.value = 'backup'"><FileIcon /> 备份与恢复</button>
            <button @click="sk.dialog.value = 'settings'"><SettingIcon /> 设置</button>
            <button @click="sk.dialog.value = 'account'"><CloudIcon /> 账号与云端同步</button>
            <button @click="sk.dialog.value = 'storage'"><SearchIcon /> 本地存储自检</button>
          </aside>

          <main class="main">
            <div class="toolbar">
              <t-input v-model="sk.filter.value" placeholder="搜索标题、账号、网址、标签…" autocomplete="off" clearable>
                <template #prefix-icon><SearchIcon /></template>
              </t-input>
              <t-button theme="primary" @click="sk.newEntry()"><template #icon><AddIcon /></template>新增条目</t-button>
            </div>
            <div class="chips">
              <t-tag :theme="sk.tag.value === '' ? 'primary' : 'default'" :variant="sk.tag.value === '' ? 'light' : 'outline'" class="chip" @click="sk.tag.value = ''">全部标签</t-tag>
              <t-tag v-for="t in sk.tagNav.value" :key="t.tag" :theme="sk.tag.value === t.tag ? 'primary' : 'default'" :variant="sk.tag.value === t.tag ? 'light' : 'outline'" class="chip" @click="sk.tag.value = t.tag">{{ t.tag }}</t-tag>
            </div>
            <div v-if="!sk.visibleItems.value.length" class="empty">{{ sk.allItems.value.length ? '没有匹配的条目' : '保险库还是空的，点「新增条目」存第一条密码' }}</div>
            <div v-for="p in sk.visibleItems.value" :key="p.id" class="item" :class="{ deleted: p._deleted }">
              <div class="item-head">
                <t-tag size="small" variant="light" theme="primary">{{ TYPE_NAME[p.type] || p.type }}</t-tag>
                <b>{{ p.title }}</b>
                <button class="star" title="收藏" @click="sk.toggleFav(p.id)">{{ p.favorite ? '★' : '☆' }}</button>
              </div>
              <div v-if="p.fields.username" class="row"><span class="k">账号</span><span class="v">{{ p.fields.username }}</span><span class="acts"><t-button size="small" variant="text" @click="onCopy(p.fields.username!)">复制</t-button></span></div>
              <div v-if="p.fields.password" class="row">
                <span class="k">密码</span><span class="v">{{ sk.revealed[p.id] ? p.fields.password : '••••••••••••' }}</span>
                <span class="acts">
                  <t-button size="small" variant="text" @click="revealToggle(p.id)">{{ sk.revealed[p.id] ? '隐藏' : '显示' }}</t-button>
                  <t-button size="small" variant="text" @click="onCopy(p.fields.password!)">复制</t-button>
                </span>
              </div>
              <div v-if="p.urls && p.urls[0]" class="row"><span class="k">网址</span><span class="v">{{ p.urls[0] }}</span></div>
              <div v-if="p.note" class="row"><span class="k">备注</span><span class="v">{{ p.note }}</span></div>
              <div v-if="p.tags && p.tags.length" class="tags"><t-tag v-for="t in p.tags" :key="t" size="small" variant="light">{{ t }}</t-tag></div>
              <div class="item-foot">
                <template v-if="p._deleted">
                  <t-button size="small" variant="outline" @click="sk.restore(p.id)"><template #icon><RollbackIcon /></template>恢复</t-button>
                  <t-button size="small" theme="danger" variant="outline" @click="sk.remove(p.id, true)"><template #icon><DeleteIcon /></template>彻底删除</t-button>
                </template>
                <template v-else>
                  <t-button size="small" variant="outline" @click="sk.editEntry(p.id)"><template #icon><Edit1Icon /></template>编辑</t-button>
                  <t-button size="small" theme="danger" variant="outline" @click="sk.remove(p.id, false)"><template #icon><DeleteIcon /></template>删除</t-button>
                </template>
                <span class="ts">{{ new Date(p.updatedAt || 0).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }}</span>
              </div>
            </div>
          </main>
        </div>
      </section>
    </div>

    <!-- 对话框 -->
    <ItemEditorDialog v-if="sk.dialog.value === 'editor'" :target="sk.editorTarget.value" :prefill="sk.prefillPassword.value" @close="sk.dialog.value = null" @save="onEditorSave" @toast="sk.toast" />
    <SettingsDialog v-else-if="sk.dialog.value === 'settings'" :prefs="sk.prefs" :account="sk.account.value" @close="sk.dialog.value = null" @save="sk.savePrefs" @change-pw="sk.dialog.value = 'changePw'" @new-recovery="sk.dialog.value = 'newRecovery'" @wipe="onWipe" />
    <ChangePwDialog v-else-if="sk.dialog.value === 'changePw'" :force="sk.isForcedChangePw()" @close="sk.dialog.value = null" @save="sk.changePassword" @toast="sk.toast" />
    <NewRecoveryDialog v-else-if="sk.dialog.value === 'newRecovery'" :generate="sk.makeNewRecovery" @close="sk.dialog.value = null" @commit="sk.commitNewRecovery" @toast="sk.toast" />
    <GeneratorDialog v-else-if="sk.dialog.value === 'generator'" @close="sk.dialog.value = null" @copy="onCopy" @use="onUsePassword" />
    <HealthDialog v-else-if="sk.dialog.value === 'health'" :items="sk.allItems.value" @close="sk.dialog.value = null" />
    <BackupDialog v-else-if="sk.dialog.value === 'backup'" :last-backup-at="sk.account.value?.lastBackupAt ?? null" :item-count="storageFacts.count" @close="sk.dialog.value = null" @export="onExport" @import="onImport" @toast="sk.toast" />
    <AccountDialog
      v-else-if="sk.dialog.value === 'account'"
      :cloud="sk.cloud"
      @close="sk.dialog.value = null"
      @toast="sk.toast"
      @need-unlock="(m: string) => sk.toast(m)"
    />
    <StorageDialog v-else-if="sk.dialog.value === 'storage'" :raw="storageFacts.raw" :item-count="storageFacts.count" :rev="storageFacts.rev" :recent-cipher="storageFacts.recent" @close="sk.dialog.value = null" />

    <!-- 反馈层 -->
    <div v-if="sk.busy.value" class="busy"><t-loading size="24px" text="正在加密 / 解密…" /></div>
    <div class="toast" :class="{ on: !!sk.toastText.value }">{{ sk.toastText.value }}</div>
  </div>
</template>

<style scoped>
.auth-card { max-width: 460px; margin: 44px auto; background: var(--color-surface); border: 1px solid var(--color-line); border-radius: 14px; padding: 28px; }
.auth-icon { width: 48px; height: 48px; border-radius: 12px; background: var(--color-brand-soft); color: var(--color-brand); display: flex; align-items: center; justify-content: center; margin-bottom: 14px; }
.auth-card h1 { font-size: 21px; margin: 0 0 6px; font-weight: 600; }
.auth-desc { color: var(--color-ink-2); font-size: 13px; margin: 0 0 18px; line-height: 1.6; }
.strength { height: 5px; border-radius: 3px; background: var(--color-line); overflow: hidden; margin-top: 8px; }
.strength i { display: block; height: 100%; width: 0; transition: width 0.2s; }
/* 恢复码输入：TDesign 的 inputClass 实测未作用到 inner input，改用 :deep 兜底等宽字体 */
.code-input :deep(.t-input__inner) { font-family: var(--font-mono); letter-spacing: 0.04em; }

.vault-layout { display: grid; grid-template-columns: 210px minmax(0, 1fr); gap: 20px; }
@media (max-width: 760px) { .vault-layout { grid-template-columns: 1fr; } .side { display: flex; flex-wrap: wrap; gap: 6px; position: static; } .side :deep(.t-divider), .side .side-title { display: none; } .side button { padding: 5px 9px; font-size: 12px; width: auto; } }
.side { background: var(--color-surface); border: 1px solid var(--color-line); border-radius: 12px; padding: 12px; align-self: start; position: sticky; top: 74px; }
.side button { display: flex; width: 100%; border: 0; background: transparent; text-align: left; padding: 7px 9px; border-radius: 7px; color: var(--color-ink-2); font-size: 12.5px; align-items: center; gap: 6px; transition: background 0.15s, color 0.15s; }
.side button:hover { background: var(--color-brand-softer); }
.side button.on { background: var(--color-brand-soft); color: var(--color-brand); font-weight: 600; }
.side button i { font-style: normal; margin-left: auto; font-size: 11px; opacity: 0.7; }
.side :deep(.t-divider) { margin: 10px 2px; }
.side-empty { font-size: 12px; color: var(--color-ink-3); padding: 0 6px; }
.main { min-width: 0; }
.toolbar { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
.toolbar :deep(.t-input) { flex: 1; min-width: 160px; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
.chip { cursor: pointer; }
.item { border: 1px solid var(--color-line); border-radius: 10px; padding: 13px 14px; margin-bottom: 10px; background: var(--color-surface); }
.item.deleted { opacity: 0.62; background: var(--color-canvas); }
.item-head { display: flex; align-items: center; gap: 8px; margin-bottom: 9px; }
.item-head b { font-size: 14px; font-weight: 600; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.star { border: 0; background: none; color: #e0a91b; font-size: 16px; padding: 0 2px; line-height: 1; }
.row { display: flex; gap: 8px; align-items: center; font-size: 12.5px; margin: 5px 0; min-height: 28px; }
.row .k { width: 44px; color: var(--color-ink-3); flex: none; }
.row .v { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: var(--font-mono); font-size: 12px; }
.row .acts { display: flex; gap: 2px; flex: none; }
.item-foot { display: flex; gap: 6px; margin-top: 10px; padding-top: 9px; border-top: 1px solid var(--color-line); align-items: center; }
.item-foot .ts { font-size: 11px; color: var(--color-ink-3); margin-left: auto; }
.tags { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 8px; }
</style>
