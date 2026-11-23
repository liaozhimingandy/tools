<script setup lang="ts">
/**
 * 应用中心管理后台 /admin/apps。
 * 四个 Tab：应用列表（CRUD/发布下架/排序）、分类管理、首页展示、访问记录。
 * 页面不做权限判断——后端每个管理接口都有管理员校验，前端只呈现 403 提示。
 */
import { computed, onMounted, reactive, ref } from 'vue'
import {
  SearchIcon, AddIcon, EditIcon, DeleteIcon,
  StarIcon, ChevronUpIcon, ChevronDownIcon,
} from 'tdesign-icons-vue-next'
import { MessagePlugin, DialogPlugin } from 'tdesign-vue-next'
import PortalHeader from '@/components/PortalHeader.vue'
import CopyRight from '@/components/CopyRight.vue'
import { adminApi, type AppForm } from '@/services/portal/adminApi.ts'
import type { PortalApp, PortalCategory } from '@/services/portal/api.ts'
import { PortalApiError } from '@/services/portal/api.ts'

const apps = ref<PortalApp[]>([])
const categories = ref<PortalCategory[]>([])
const loading = ref(false)
const activeTab = ref('apps')
const keyword = ref('')
const typeFilter = ref('')
const statusFilter = ref('')
const err = ref('')

// 编辑抽屉
const drawerVisible = ref(false)
const editingId = ref<string | null>(null)
const form = ref<AppForm>({
  code: '', name: '', subtitle: '', description: '', detail: '',
  icon_url: '', cover_url: '', launch_url: '', app_type: 'application',
  open_mode: 'new_tab', status: 'draft', visibility: 'public',
  auth_required: false, is_featured: false, show_on_home: false, is_new: false,
  sort_order: 0, categories: [],
})

const filteredApps = computed(() => apps.value.filter((a) => {
  const q = keyword.value.trim().toLowerCase()
  if (q && !`${a.name} ${a.code} ${a.subtitle}`.toLowerCase().includes(q)) return false
  if (typeFilter.value && a.app_type !== typeFilter.value) return false
  if (statusFilter.value && a.status !== statusFilter.value) return false
  return true
}))

const statusTheme = (s: string) => s === 'published' ? 'success' : s === 'draft' ? 'warning' : 'danger'

async function load(): Promise<void> {
  loading.value = true
  err.value = ''
  try {
    const [appRes, catRes] = await Promise.all([adminApi.listApps(), adminApi.listCategories()])
    apps.value = appRes.items
    categories.value = catRes.items
  } catch (e) {
    err.value = e instanceof PortalApiError
      ? (e.status === 403 ? '当前账号没有管理员权限（需在后端配置 PORTAL_ADMIN_SUBS）' : e.message)
      : '加载管理数据失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)

function openCreate(): void {
  editingId.value = null
  Object.assign(form.value, {
    code: '', name: '', subtitle: '', description: '', detail: '',
    icon_url: '', cover_url: '', launch_url: '', app_type: 'application',
    open_mode: 'new_tab', status: 'draft', visibility: 'public',
    auth_required: false, is_featured: false, show_on_home: false, is_new: false,
    sort_order: 0, categories: [],
  })
  drawerVisible.value = true
}

function openEdit(app: PortalApp): void {
  editingId.value = app.id
  Object.assign(form.value, {
    code: app.code, name: app.name, subtitle: app.subtitle,
    description: app.description, detail: app.detail,
    icon_url: app.icon_url, cover_url: app.cover_url, launch_url: app.launch_url,
    app_type: app.app_type, open_mode: app.open_mode, status: app.status,
    visibility: app.visibility, auth_required: app.auth_required,
    is_featured: app.is_featured, show_on_home: app.show_on_home,
    is_new: app.is_new, sort_order: app.sort_order,
    categories: [...app.categories],
  })
  drawerVisible.value = true
}

async function save(): Promise<void> {
  if (!form.value.name?.trim()) { await MessagePlugin.warning('请填写应用名称'); return }
  try {
    if (editingId.value) await adminApi.updateApp(editingId.value, form.value)
    else await adminApi.createApp(form.value)
    drawerVisible.value = false
    await MessagePlugin.success('已保存')
    await load()
  } catch (e) {
    await MessagePlugin.error(e instanceof PortalApiError ? e.message : '保存失败')
  }
}

function confirmDelete(app: PortalApp): void {
  const dlg = DialogPlugin.confirm({
    header: '确认删除',
    body: `确定删除「${app.name}」吗？该应用的收藏与访问记录将一并删除，不可恢复。`,
    confirmBtn: { theme: 'danger', content: '删除' },
    onConfirm: async () => {
      try {
        await adminApi.deleteApp(app.id)
        await MessagePlugin.success('已删除')
        await load()
      } catch (e) {
        await MessagePlugin.error(e instanceof PortalApiError ? e.message : '删除失败')
      }
      dlg.hide()
    },
  })
}

async function changeStatus(app: PortalApp, action: 'publish' | 'disable'): Promise<void> {
  try {
    await (action === 'publish' ? adminApi.publish(app.id) : adminApi.disable(app.id))
    await MessagePlugin.success(action === 'publish' ? '已发布' : '已停用')
    await load()
  } catch (e) {
    await MessagePlugin.error(e instanceof PortalApiError ? e.message : '操作失败')
  }
}

async function move(app: PortalApp, delta: number): Promise<void> {
  await adminApi.updateApp(app.id, { sort_order: app.sort_order + delta })
  await load()
}

async function toggleHome(app: PortalApp, key: 'show_on_home' | 'is_featured'): Promise<void> {
  await adminApi.updateApp(app.id, { [key]: !app[key] })
  await load()
}

// 分类管理
const catForm = reactive({ code: '', name: '', description: '', sort_order: 0 })
async function addCategory(): Promise<void> {
  if (!catForm.code || !catForm.name) { await MessagePlugin.warning('请填写编码和名称'); return }
  try {
    await adminApi.createCategory(catForm)
    catForm.code = ''; catForm.name = ''; catForm.description = ''
    await MessagePlugin.success('分类已新增')
    await load()
  } catch (e) {
    await MessagePlugin.error(e instanceof PortalApiError ? e.message : '新增失败')
  }
}
async function deleteCategory(cat: PortalCategory): Promise<void> {
  const dlg = DialogPlugin.confirm({
    header: '确认删除分类',
    body: `删除「${cat.name}」后，关联应用会保留但不再属于该分类。确认继续？`,
    onConfirm: async () => {
      try {
        await adminApi.deleteCategory(cat.id)
        await MessagePlugin.success('已删除')
        await load()
      } catch (e) {
        await MessagePlugin.error(e instanceof PortalApiError ? e.message : '删除失败')
      }
      dlg.hide()
    },
  })
}
async function toggleCategory(cat: PortalCategory): Promise<void> {
  await adminApi.updateCategory(cat.id, { status: cat.status === 'enabled' ? 'disabled' : 'enabled' })
  await load()
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString()
}
const TYPE_LABEL: Record<string, string> = { application: '应用', tool: '工具', game: '游戏', service: '服务' }
const STATUS_LABEL: Record<string, string> = { draft: '草稿', published: '已发布', disabled: '已停用' }
</script>

<template>
  <PortalHeader />

  <main class="mx-auto max-w-7xl px-4 pb-16">
    <div class="flex items-center justify-between flex-wrap gap-3 mb-4">
      <div>
        <h1 class="text-[24px] font-bold">应用中心管理</h1>
        <p class="text-[13px] text-ink-3 mt-1">可视化维护应用目录，无需修改前端代码</p>
      </div>
      <t-button theme="primary" @click="openCreate"><AddIcon /> 新增应用</t-button>
    </div>

    <t-alert v-if="err" theme="warning" class="mb-4"><template #message>{{ err }}</template></t-alert>

    <t-tabs v-model="activeTab">
      <!-- 应用列表 -->
      <t-tab-panel value="apps" label="应用列表">
        <div class="flex flex-wrap gap-3 mt-4 mb-3">
          <t-input v-model="keyword" class="w-[240px]" placeholder="搜索名称/编码" clearable>
            <template #prefix-icon><SearchIcon /></template>
          </t-input>
          <t-select v-model="typeFilter" placeholder="类型" clearable class="w-[140px]">
            <t-option value="application" label="应用" />
            <t-option value="tool" label="工具" />
            <t-option value="game" label="游戏" />
            <t-option value="service" label="服务" />
          </t-select>
          <t-select v-model="statusFilter" placeholder="状态" clearable class="w-[140px]">
            <t-option value="draft" label="草稿" />
            <t-option value="published" label="已发布" />
            <t-option value="disabled" label="已停用" />
          </t-select>
        </div>

        <t-table
          :data="filteredApps"
          :columns="[
            { colKey: 'name', title: '应用', width: 190 },
            { colKey: 'code', title: '编码', width: 140 },
            { colKey: 'app_type', title: '类型', width: 90 },
            { colKey: 'categories', title: '分类', width: 160 },
            { colKey: 'status', title: '状态', width: 110 },
            { colKey: 'visibility', title: '展示范围', width: 100 },
            { colKey: 'sort_order', title: '排序', width: 110 },
            { colKey: 'show_on_home', title: '首页', width: 80 },
            { colKey: 'updated_at', title: '更新时间', width: 170 },
            { colKey: 'op', title: '操作', width: 260, fixed: 'right' },
          ]"
          :loading="loading"
          row-key="id"
          bordered
          stripe
          size="small"
          :pagination="{ pageSize: 20, showJumper: false }"
        >
          <template #name="{ row }">
            <div class="flex items-center gap-2">
              <span class="font-medium">{{ row.name }}</span>
              <t-tag v-if="row.is_new" size="small" theme="success" variant="light">新</t-tag>
            </div>
          </template>
          <template #app_type="{ row }">
            {{ TYPE_LABEL[row.app_type] }}
          </template>
          <template #categories="{ row }">
            <div class="flex flex-wrap gap-1">
              <t-tag v-for="c in row.categories" :key="c" size="small" variant="light">{{ c }}</t-tag>
            </div>
          </template>
          <template #status="{ row }">
            <t-tag size="small" :theme="statusTheme(row.status)" variant="light">
              {{ STATUS_LABEL[row.status] }}
            </t-tag>
          </template>
          <template #visibility="{ row }">
            {{ row.visibility === 'public' ? '公开' : '私有' }}
          </template>
          <template #sort_order="{ row }">
            <div class="flex items-center gap-1">
              <t-button size="small" variant="text" @click="move(row, 1)" title="提前"><ChevronUpIcon /></t-button>
              <span class="w-6 text-center">{{ row.sort_order }}</span>
              <t-button size="small" variant="text" @click="move(row, -1)" title="延后"><ChevronDownIcon /></t-button>
            </div>
          </template>
          <template #show_on_home="{ row }">
            <t-button size="small" variant="text" :theme="row.show_on_home ? 'primary' : 'default'" @click="toggleHome(row, 'show_on_home')">
              <StarIcon :style="{ fill: row.show_on_home ? 'currentColor' : 'none' }" />
            </t-button>
          </template>
          <template #updated_at="{ row }">{{ formatTime(row.updated_at) }}</template>
          <template #op="{ row }">
            <div class="flex flex-wrap items-center gap-1">
              <t-button size="small" variant="text" @click="openEdit(row)"><EditIcon /> 编辑</t-button>
              <t-button v-if="row.status !== 'published'" size="small" variant="text" theme="success" @click="changeStatus(row, 'publish')">发布</t-button>
              <t-button v-if="row.status === 'published'" size="small" variant="text" theme="warning" @click="changeStatus(row, 'disable')">下架</t-button>
              <t-button size="small" variant="text" theme="danger" @click="confirmDelete(row)"><DeleteIcon /></t-button>
            </div>
          </template>
        </t-table>
      </t-tab-panel>

      <!-- 分类管理 -->
      <t-tab-panel value="categories" label="分类管理">
        <div class="mt-4">
          <t-card class="mb-4">
            <div class="flex flex-wrap items-end gap-3">
              <t-form-item label="编码"><t-input v-model="catForm.code" placeholder="如 ai" class="w-[160px]" /></t-form-item>
              <t-form-item label="名称"><t-input v-model="catForm.name" placeholder="如 AI 工具" class="w-[180px]" /></t-form-item>
              <t-form-item label="排序"><t-input-number v-model="catForm.sort_order" class="w-[120px]" /></t-form-item>
              <t-button theme="primary" @click="addCategory"><AddIcon /> 新增分类</t-button>
            </div>
          </t-card>
          <t-table
            :data="categories"
            :columns="[
              { colKey: 'code', title: '编码', width: 160 },
              { colKey: 'name', title: '名称', width: 180 },
              { colKey: 'description', title: '描述' },
              { colKey: 'sort_order', title: '排序', width: 90 },
              { colKey: 'status', title: '状态', width: 100 },
              { colKey: 'op', title: '操作', width: 200, fixed: 'right' },
            ]"
            row-key="id" bordered stripe size="small"
          >
            <template #status="{ row }">
              <t-tag size="small" :theme="row.status === 'enabled' ? 'success' : 'default'" variant="light">
                {{ row.status === 'enabled' ? '启用' : '停用' }}
              </t-tag>
            </template>
            <template #op="{ row }">
              <t-button size="small" variant="text" @click="toggleCategory(row)">
                {{ row.status === 'enabled' ? '停用' : '启用' }}
              </t-button>
              <t-button size="small" variant="text" theme="danger" @click="deleteCategory(row)"><DeleteIcon /></t-button>
            </template>
          </t-table>
        </div>
      </t-tab-panel>

      <!-- 首页展示管理 -->
      <t-tab-panel value="homepage" label="首页展示">
        <div class="mt-4">
          <p class="text-[13px] text-ink-3 mb-3">点击星标切换「首页推荐」，用箭头调整排序；保存后立即生效，无需重新构建前端。</p>
          <t-table
            :data="apps"
            :columns="[
              { colKey: 'name', title: '应用', width: 220 },
              { colKey: 'is_featured', title: '推荐', width: 100 },
              { colKey: 'show_on_home', title: '首页展示', width: 110 },
              { colKey: 'sort_order', title: '排序', width: 140 },
            ]"
            row-key="id" bordered stripe size="small"
          >
            <template #is_featured="{ row }">
              <t-button size="small" variant="text" :theme="row.is_featured ? 'primary' : 'default'" @click="toggleHome(row, 'is_featured')">
                <StarIcon :style="{ fill: row.is_featured ? 'currentColor' : 'none' }" />
              </t-button>
            </template>
            <template #show_on_home="{ row }">
              <t-switch :value="row.show_on_home" @change="() => toggleHome(row, 'show_on_home')" />
            </template>
            <template #sort_order="{ row }">
              <div class="flex items-center gap-2">
                <span>{{ row.sort_order }}</span>
                <t-button size="small" variant="text" @click="move(row, 10)">+10</t-button>
                <t-button size="small" variant="text" @click="move(row, -10)">-10</t-button>
              </div>
            </template>
          </t-table>
        </div>
      </t-tab-panel>
    </t-tabs>

    <!-- 编辑抽屉 -->
    <t-drawer
      v-model:visible="drawerVisible"
      :header="editingId ? '编辑应用' : '新增应用'"
      size="min(620px, 94vw)"
      :footer="false"
    >
      <div class="space-y-4">
        <div class="text-[13px] font-semibold text-ink-2">基本信息</div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <t-form-item label="应用名称" required><t-input v-model="form.name" placeholder="如 AlphaQuant" /></t-form-item>
          <t-form-item label="应用编码" required><t-input v-model="form.code" placeholder="如 ALPHA_QUANT" :disabled="!!editingId" /></t-form-item>
        </div>
        <t-form-item label="副标题"><t-input v-model="form.subtitle" /></t-form-item>
        <t-form-item label="简介"><t-textarea v-model="form.description" :autosize="{ minRows: 2, maxRows: 4 }" /></t-form-item>
        <t-form-item label="详细介绍"><t-textarea v-model="form.detail" :autosize="{ minRows: 3, maxRows: 6 }" /></t-form-item>
        <t-form-item label="应用类型">
          <t-select v-model="form.app_type">
            <t-option value="application" label="应用" /><t-option value="tool" label="工具" />
            <t-option value="game" label="游戏" /><t-option value="service" label="服务" />
          </t-select>
        </t-form-item>

        <t-divider />
        <div class="text-[13px] font-semibold text-ink-2">展示信息</div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <t-form-item label="图标 URL"><t-input v-model="form.icon_url" placeholder="https://..." /></t-form-item>
          <t-form-item label="封面 URL"><t-input v-model="form.cover_url" placeholder="https://..." /></t-form-item>
        </div>
        <t-form-item label="所属分类">
          <t-select v-model="form.categories" multiple placeholder="可多选">
            <t-option v-for="c in categories" :key="c.id" :value="c.code" :label="c.name" />
          </t-select>
        </t-form-item>
        <div class="flex flex-wrap gap-5">
          <t-checkbox v-model="form.is_featured">首页推荐</t-checkbox>
          <t-checkbox v-model="form.show_on_home">首页展示</t-checkbox>
          <t-checkbox v-model="form.is_new">新品标识</t-checkbox>
        </div>

        <t-divider />
        <div class="text-[13px] font-semibold text-ink-2">访问配置</div>
        <t-form-item label="访问地址"><t-input v-model="form.launch_url" placeholder="https://...（留空表示未部署）" /></t-form-item>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <t-form-item label="打开方式">
            <t-select v-model="form.open_mode">
              <t-option value="new_tab" label="新标签页" /><t-option value="same_tab" label="当前页面" />
            </t-select>
          </t-form-item>
          <t-form-item label="展示范围">
            <t-select v-model="form.visibility">
              <t-option value="public" label="公开" /><t-option value="private" label="私有" />
            </t-select>
          </t-form-item>
        </div>
        <t-checkbox v-model="form.auth_required">需要登录才能访问</t-checkbox>

        <t-divider />
        <div class="text-[13px] font-semibold text-ink-2">发布设置</div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <t-form-item label="状态">
            <t-select v-model="form.status">
              <t-option value="draft" label="草稿" /><t-option value="published" label="发布" /><t-option value="disabled" label="暂停服务" />
            </t-select>
          </t-form-item>
          <t-form-item label="排序权重"><t-input-number v-model="form.sort_order" class="w-full" /></t-form-item>
        </div>

        <!-- 实时预览 -->
        <t-divider />
        <div class="text-[13px] font-semibold text-ink-2 mb-2">卡片预览</div>
        <div class="rounded-lg border border-line p-3 bg-canvas">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-brand-soft text-brand flex items-center justify-center font-bold shrink-0">
              {{ (form.name || 'A').charAt(0).toUpperCase() }}
            </div>
            <div class="min-w-0">
              <div class="font-semibold truncate">{{ form.name || '应用名称' }}</div>
              <div class="text-[12px] text-ink-3 truncate">{{ form.subtitle || '副标题' }}</div>
            </div>
          </div>
          <p class="text-[12.5px] text-ink-2 mt-2">{{ form.description || '应用简介' }}</p>
        </div>

        <div class="flex justify-end gap-2 pt-3">
          <t-button variant="outline" @click="drawerVisible = false">取消</t-button>
          <t-button theme="primary" @click="save">保存</t-button>
        </div>
      </div>
    </t-drawer>
  </main>

  <CopyRight />
</template>

<style scoped>
</style>