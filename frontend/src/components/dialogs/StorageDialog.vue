<script setup lang="ts">
/** 本地存储自检：直接读原始存储，验证"存的是密文不是明文"。 */
import { ref } from 'vue'
import { CheckCircleIcon, ErrorCircleIcon, SearchIcon } from 'tdesign-icons-vue-next'
import { LS } from '@/services/safekeep/storage.ts'

const props = defineProps<{
  raw: string
  itemCount: number
  rev: number
  recentCipher: Array<{ id: string; rev: number; deleted: boolean; iv: string; ct: string }>
}>()
const emit = defineEmits<{ close: [] }>()
const visible = ref(true)
const query = ref('')
const result = ref<{ hit: boolean } | null>(null)

function verify(): void {
  const q = query.value.trim()
  if (!q) {
    result.value = null
    return
  }
  result.value = { hit: props.raw.toLowerCase().includes(q.toLowerCase()) }
}
</script>

<template>
  <t-dialog
    v-model:visible="visible"
    header="本地存储自检"
    width="620px"
    :footer="false"
    @close="emit('close')"
  >
    <p class="dlg-desc">直接读取浏览器 localStorage 的原始内容，验证「本地存储密码」存的是密文而不是明文。</p>
    <div class="kv"><span>账户记录</span><span>{{ LS.a }}</span></div>
    <div class="kv"><span>条目密文</span><span>{{ LS.i }} · {{ itemCount }} 条</span></div>
    <div class="kv"><span>全局 rev</span><span>{{ rev }}</span></div>

    <div class="flex gap-1.5 my-3">
      <t-input v-model="query" placeholder="输入一个已保存的站点名或账号" @enter="verify" />
      <t-button theme="primary" @click="verify"><template #icon><SearchIcon /></template>查找明文</t-button>
    </div>
    <t-alert v-if="result" :theme="result.hit ? 'error' : 'success'" class="mb-3">
      <template #message>
        <ErrorCircleIcon v-if="result.hit" class="mr-1" />
        <CheckCircleIcon v-else class="mr-1" />
        {{ result.hit ? '意外：在本地存储里找到了明文，说明加密边界有漏洞' : '未找到（符合预期）：本地只存包裹密钥与 AES-GCM 密文' }}
      </template>
    </t-alert>

    <div class="side-title mt-4">最近写入的密文记录</div>
    <div v-if="!recentCipher.length" class="empty">本地还没有条目密文</div>
    <div v-for="r in recentCipher" :key="r.id" class="cipher">
      <div><span class="ck">id </span>{{ r.id.slice(0, 18) }}…　<span class="ck">rev </span>{{ r.rev }}　<span class="ck">deleted </span>{{ r.deleted }}</div>
      <div><span class="ck">iv </span>{{ r.iv }}</div>
      <div><span class="ck">ct </span><span class="ct">{{ String(r.ct).slice(0, 72) }}…</span></div>
    </div>

    <div class="flex mt-5">
      <t-button theme="default" variant="outline" block @click="emit('close')">关闭</t-button>
    </div>
  </t-dialog>
</template>
