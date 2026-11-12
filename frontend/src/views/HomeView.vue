<script setup lang="ts">
/** 工具集门户：列出所有已接入的工具，未来新增工具=加一张卡片 + 一条路由。 */
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { LockOnIcon, ChevronRightIcon, CloudIcon, LogoutIcon } from 'tdesign-icons-vue-next'
import { cachedAuthState, currentSub, displayUser, signIn, signOut, type DisplayUser } from '@/services/auth/logto.ts'
import { logtoEnabled } from '@/config.ts'

interface ToolCard {
  to: string
  title: string
  en: string
  desc: string
  tags: string[]
}

const tools: ToolCard[] = [
  {
    to: '/safekeep',
    title: '锦囊',
    en: 'SafeKeep',
    desc: '本地零知识密码库。浏览器内 AES-256-GCM 加密，主密码与恢复码双钥匙解锁，纯密文本地存储与加密备份。',
    tags: ['零知识', '本地存储', 'Web Crypto'],
  },
]

// 登录入口只看 Logto 是否可用；后端 API 未配时仍可先登录、看到账号态。
const enabled = logtoEnabled()
const sub = ref<string | null>(cachedAuthState()?.sub ?? null)
const user = ref<DisplayUser | null>(null)
onMounted(async () => {
  if (!enabled) return
  const s = await currentSub()
  sub.value = s
  if (s) user.value = await displayUser()
})
async function login(): Promise<void> {
  try { await signIn() } catch { /* 跳转失败保持原状 */ }
}
async function logout(): Promise<void> {
  try { await signOut() } catch { /* 忽略 */ }
}
</script>

<template>
  <header class="topbar">
    <div class="brand">tools · <span class="text-brand">工具集</span></div>
    <div class="sp"></div>
    <!-- Logto 可用时显示登录入口；未配置时纯本地，不打扰 -->
    <template v-if="enabled">
      <t-tag v-if="sub" size="small" variant="light" theme="success">已登录</t-tag>
      <span v-if="sub" class="cd">{{ user?.name || user?.email || sub }}</span>
      <t-button v-if="sub" size="small" variant="text" @click="logout">
        <LogoutIcon /> 退出
      </t-button>
      <t-button v-else size="small" variant="outline" @click="login">
        <CloudIcon /> 登录以同步
      </t-button>
    </template>
    <t-tag size="small" variant="light" theme="primary">Vue 3 · FastAPI</t-tag>
  </header>

  <section class="portal-hero">
    <h1>我的工具集</h1>
   </section>

  <section class="tool-grid">
    <RouterLink v-for="t in tools" :key="t.to" :to="t.to" class="no-underline">
      <t-card hoverable class="tool-card">
        <div class="flex items-center gap-3 mb-2.5">
          <div class="w-11 h-11 rounded-xl bg-brand-soft text-brand flex items-center justify-center shrink-0">
            <LockOnIcon size="22px" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-base font-semibold text-ink leading-tight">{{ t.title }}</div>
            <div class="text-[11.5px] text-ink-3">{{ t.en }}</div>
          </div>
          <ChevronRightIcon class="text-ink-3" size="18px" />
        </div>
        <div class="text-[12.5px] text-ink-2 leading-relaxed">{{ t.desc }}</div>
        <div class="flex gap-1.5 flex-wrap mt-3.5">
          <t-tag v-for="tag in t.tags" :key="tag" size="small" variant="light">{{ tag }}</t-tag>
        </div>
      </t-card>
    </RouterLink>
  </section>
</template>

<style scoped>
.tool-card {
  border-radius: 14px;
}
.tool-card :deep(.t-card__body) {
  padding: 20px;
}
</style>
