<script setup lang="ts">
/** 条目新增/编辑对话框。业务交给父级 save，本组件只管表单与校验。 */
import { reactive, ref, watch } from 'vue'
import { RefreshIcon, BrowseIcon } from 'tdesign-icons-vue-next'
import { newPlain, cloneItem, TYPE_NAME } from '@/services/safekeep/vault.ts'
import { genPassword } from '@/services/safekeep/crypto.ts'
import type { ItemType, PlainItem } from '@/services/safekeep/types.ts'

const props = defineProps<{ target: PlainItem | null; prefill?: string }>()
const emit = defineEmits<{ close: []; save: [item: PlainItem]; toast: [msg: string] }>()
const visible = ref(true)

/**
 * form 是 reactive() 返回的 Proxy。保存时必须用 cloneItem（JSON 深拷贝）脱离 Proxy
 * 再 emit——绝不能用 structuredClone，它无法克隆 Proxy，会抛 DataCloneError，
 * 导致 submit 同步抛错、save 事件发不出去（表现为「点保存没反应」）。
 */
const form = reactive<PlainItem>(props.target ? cloneItem(props.target) : newPlain())
if (!props.target && props.prefill) {
  form.fields.password = props.prefill
}
const showPass = ref(!props.target && !!props.prefill)
const typeKeys = Object.keys(TYPE_NAME) as ItemType[]
// 预先把类型名解析成 string[]：避免模板里 Record<ItemType,string> 索引命中泛型组件的 TNode 推断缺陷
const typeOptions = typeKeys.map((t) => ({ value: t, label: TYPE_NAME[t] }))

// TDesign t-input 是泛型组件（T = modelValue 类型）。网址/标签是「数组字段投影成字符串」，
// 若用 :value + 内联类型化 @change，会让 T 推断成 string|undefined 并级联出错误的类型报错。
// 用独立 string ref 承载输入、watch 同步回 form，T 稳定推断为 string。
const urlText = ref(form.urls[0] || '')
const tagsText = ref(form.tags.join(', '))
const noteText = ref(form.note)
const typeValue = ref<ItemType>(form.type)
const favoriteValue = ref(form.favorite)
watch(urlText, (v) => { form.urls = v.trim() ? [v] : [] })
watch(tagsText, (v) => { form.tags = v.split(/[,，]/).map((t) => t.trim()).filter(Boolean) })
watch(noteText, (v) => { form.note = v })
watch(typeValue, (v) => { form.type = v })
watch(favoriteValue, (v) => { form.favorite = v })

function generate(): void {
  form.fields.password = genPassword({ length: 20, exclude: true }).value
  showPass.value = true
  emit('toast', '已生成 20 位高熵密码')
}
function submit(): void {
  form.title = form.title.trim() || '未命名'
  form.urls = [String(form.urls[0] || '').trim()].filter(Boolean)
  form.updatedAt = Date.now()
  emit('save', cloneItem(form))
}
</script>

<template>
  <t-dialog
    v-model:visible="visible"
    :header="target ? '编辑条目' : '新增条目'"
    width="560px"
    :footer="false"
    @close="emit('close')"
  >
    <p class="dlg-desc">保存时整条记录（含类型、网址、标签、时间）会一起加密，本地存储里看不到任何明文。</p>

    <label class="field-label">标题 / 站点</label>
    <t-input v-model="form.title" placeholder="例如：GitHub" class="mb-3" />

    <label class="field-label">账号</label>
    <t-input v-model="form.fields.username" class="mb-3" />

    <div class="flex items-center justify-between">
      <label class="field-label mb-0">密码</label>
      <div class="flex gap-1">
        <t-button size="small" variant="text" theme="primary" @click="generate">
          <template #icon><RefreshIcon /></template>生成
        </t-button>
        <t-button size="small" variant="text" @click="showPass = !showPass">
          <template #icon><BrowseIcon /></template>{{ showPass ? '隐藏' : '显示' }}
        </t-button>
      </div>
    </div>
    <t-input v-model="form.fields.password" :type="showPass ? 'text' : 'password'" autocomplete="off" class="mb-3" />

    <label class="field-label">网址</label>
    <t-input v-model="urlText" placeholder="https://" class="mb-3" />

    <label class="field-label">备注</label>
    <t-textarea v-model="noteText" :autosize="{ minRows: 2, maxRows: 5 }" class="mb-3" />

    <label class="field-label">标签（逗号分隔）</label>
    <t-input v-model="tagsText" class="mb-3" />

    <div class="grid grid-cols-2 gap-3">
      <div>
        <label class="field-label">类型</label>
        <t-select v-model="typeValue">
          <t-option v-for="opt in typeOptions" :key="opt.value" :value="opt.value" :label="opt.label" />
        </t-select>
      </div>
      <div>
        <label class="field-label">收藏</label>
        <div class="flex items-center gap-2 h-8">
          <t-checkbox v-model="favoriteValue" /> <span class="text-[12px] text-ink-3">置顶显示</span>
        </div>
      </div>
    </div>

    <div class="flex gap-2 mt-6">
      <t-button theme="primary" class="flex-1" @click="submit">加密保存</t-button>
      <t-button theme="default" variant="outline" class="flex-1" @click="emit('close')">取消</t-button>
    </div>
  </t-dialog>
</template>
