# Vue 规范

> **何时读**：编写或审查 Vue 组件、组合式函数、路由与状态管理代码时。
> **前提**：[../../core/coding-principles.md](../../core/coding-principles.md)、
> [typescript.md](../languages/typescript.md)、[component.md](component.md)。
> **安全红线**：[../../core/security-principles.md](../../core/security-principles.md) §4（XSS）。

---

## 1. 版本与既有约定

- 以项目实际使用的 Vue 大版本与构建工具为准，不凭记忆使用另一套 API。
- 不擅自更换状态管理库、路由库、UI 框架或构建工具，见
  [../../core/ai-behavior.md](../../core/ai-behavior.md) §3.2。
- 组件风格（Options API / Composition API、`<script setup>` 与否）遵循项目既有约定；
  不在同一次改动中混用两套风格。
- 第三方包的根入口未必是 Vue 版实现：导入前查看包的 `package.json` 的 `exports`
  与 `dist/*.d.ts`，确认应使用的子路径，避免构建期缺少运行时导出而失败。

## 2. 组件结构

- 单文件组件保持 `<script>` / `<template>` / `<style>` 顺序与项目一致；
  超过约 200–300 行时按职责拆分子组件或组合式函数。
- 组件只负责渲染与交互编排；业务规则、数据请求放在可独立测试的
  composable / service 中。
- `props` 明确类型与默认值；不直接修改 `props`，通过事件把变更交给父级。
- 事件名稳定、语义清晰；不把多个不相关语义塞进一个 `emit`。
- 插槽内容的作用域写清；不为"以后可能用到"预留空插槽。

## 3. 响应式与状态

- 明确区分：`ref`/`reactive`（组件局部状态）、`computed`（派生值）、
  `watch`/`watchEffect`（副作用）。
- 能用 `computed` 表达的派生值不要放进 `watch` 里手动同步。
- 解构 `reactive` 会丢失响应性；使用 `toRefs` 或直接 `ref`。
- `watch` 必须处理清理（取消请求、清除定时器），并在不需要时停止。
- 全局状态只放真正跨组件共享的数据；不把表单草稿、临时 UI 状态放进全局 store。
- 不在模板中写复杂表达式；提取为 `computed` 或方法。

## 4. 生命周期与副作用

- 副作用在 `onMounted` 之后发起，在 `onUnmounted` 中清理：
  事件监听、定时器、订阅、WebSocket、Observer。
- 异步请求处理竞态：组件卸载或参数变化后，迟到的响应不得覆盖新状态。
- 不在 `setup` 顶层执行依赖 `window`/`document` 的代码（SSR 场景）；先判断环境。
- 路由参数变化触发的数据刷新要显式处理，不假设组件一定会被重新创建。

## 5. 渲染与性能

- `v-for` 必须提供稳定且唯一的 `:key`；不用数组下标作为可增删列表的 key。
- 不在同一元素上同时使用 `v-if` 与 `v-for`（按项目 lint 规则处理），
  先用计算属性过滤。
- 大列表使用虚拟滚动或分页；不在一次渲染中生成无界 DOM。
- 组件按需异步加载（`defineAsyncComponent` / 路由懒加载），
  但不为几行代码的小组件引入额外分包。
- 避免不必要的深层响应式：大体积只读数据用 `shallowRef` / `markRaw`（若项目版本支持）。

## 6. 安全

- **不使用 `v-html` 渲染不可信内容**；确有富文本需求必须先经服务端白名单净化，
  并在代码中注明净化位置，见
  [../../core/security-principles.md](../../core/security-principles.md) §4。
- 不在模板插值中拼接 URL 后直接绑定到 `href`/`src` 而未校验协议，防 `javascript:` 与 SSRF 面。
- 不把 Token 存到可被任意脚本读取的位置而不加说明；避免出现在 URL 与日志中。
- 前端权限隐藏只是体验优化，服务端必须独立做对象级授权，见
  [../../core/security-principles.md](../../core/security-principles.md) §13。

## 7. 类型与工具链

- 使用 `vue-tsc`（或项目既有命令）做类型检查；若根 `tsconfig.json` 是
  composite 引用结构，必须显式 `-p tsconfig.app.json`，否则可能零检查，见
  [typescript.md](../languages/typescript.md) §1。
- Vite 别名同步配置到 `tsconfig` 的 `baseUrl` + `paths`。
- 类型检查通过不等于构建通过：改动较大时实际运行构建，
  大范围格式化前后各跑一次类型检查以隔离变量。

## 8. 测试与验证

- 组件测试断言**行为与渲染结果**，不大量断言内部实现细节；
  Mock 遵守 [../../core/testing-principles.md](../../core/testing-principles.md) §10。
- 覆盖：正常渲染、空数据、加载中、失败态、边界值、用户交互后的状态变化。
- 提交前实际运行类型检查、lint、测试、构建，并记录结果。
