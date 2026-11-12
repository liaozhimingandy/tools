# TypeScript 规范

> **何时读**：编写或审查 TypeScript 代码、调整 `tsconfig`、新增前端/Node 模块时。
> **前提**：[../../core/coding-principles.md](../../core/coding-principles.md)、
> [../../core/engineering-principles.md](../../core/engineering-principles.md)。
> JavaScript（无类型）项目见 [javascript.md](javascript.md)。

---

## 1. 类型检查配置

- 开启严格模式；不得用整仓 `// @ts-ignore`、`any` 或放宽 `tsconfig` 来让报错消失。
- `strict` 下仍存在的 `any` 必须来自第三方边界，并在边界处立即收敛为明确类型。
- 若仓库根 `tsconfig.json` 是 `{"files": [], "references": [...]}` 的 composite 结构，
  **必须显式指定子配置**做检查（例如 `vue-tsc --noEmit -p tsconfig.app.json`）；
  在根目录直接跑可能什么都不检查，产生"零错误"的假阴性。
- Vite/打包器中的路径别名（如 `@/`）必须同步配置到 `tsconfig` 的
  `baseUrl` + `paths`；只配打包器会让 `@/xxx` 解析失败并退化成 `any`，
  掩盖大量真实类型错误。
- 类型检查通过不等于构建通过：改动较大时必须**实际运行构建**。

## 2. 命名与模块

- 类型/接口/类用 `PascalCase`，变量/函数用 `camelCase`，常量用 `UPPER_SNAKE_CASE`
  （或遵循项目既有约定，不混用两套）。
- 优先命名导出（named export）；默认导出仅在项目既有约定或框架要求时使用。
- 一个文件一个主要职责；不用 `index.ts` 无节制地重新导出整个目录形成隐式公共 API。
- 避免循环依赖；出现时提取共享类型或反转依赖，不用动态 `import()` 掩盖。

## 3. 类型建模

- 用 `interface`/`type` 明确数据形状，禁止用 `Record<string, any>` 作为通用容器。
- 有限取值用字面量联合或 `enum`（优先字面量联合），不用裸字符串比较状态。
- 区分 `undefined`（未加载/未提供）、`null`（明确为空）与空值集合，不混用。
- 使用 `unknown` 处理来源不明的数据，经过类型守卫（`type guard`）收敛后再使用。
- 泛型只在确实存在多个类型实参时使用；不为单个调用点造泛型。

## 4. 异步与错误

- 统一使用 `async/await`；不在同一模块混用回调、`.then` 链与 `await`（既有代码除外）。
- `Promise` 必须被 `await`、返回或显式处理；禁止"发射后不管"的未处理 Promise。
- 并发用 `Promise.all` / `allSettled` 表达意图；需要顺序执行时不要意外并行。
- `catch` 中先按 `unknown` 处理再收窄类型；不假设 `err.message` 一定存在。
- 异常必须向能处理它的层级传播，不吞掉；见
  [../../core/engineering-principles.md](../../core/engineering-principles.md) §8。
- 所有网络请求设置超时与失败处理；不依赖框架默认无限等待。

## 5. 空值与边界

- 优先使用可选链 `?.` 与空值合并 `??`，不用 `||` 处理可能为 `0`/`""`/`false` 的值。
- 数组索引访问前检查边界；`non-null` 断言 `!` 必须附带为什么必然非空的理由。
- 外部输入（请求体、URL 参数、localStorage、第三方响应）在边界校验后再进入业务逻辑；
  运行时校验不能只靠编译期类型。

## 6. 安全

- 不使用 `eval`、`new Function`、`innerHTML` 承载不可信数据，见
  [../../core/security-principles.md](../../core/security-principles.md) §4。
- 不把 Token 放进 `localStorage` 之外的可枚举位置而不做说明；避免出现在 URL 与日志中。
- 服务端渲染/模板中的插值依赖框架默认转义；绕过转义的写法必须单独审查。
- 构造子进程调用时使用参数数组，不拼接 shell 命令，见
  [../../core/security-principles.md](../../core/security-principles.md) §7。

## 7. 与框架相关的落点

- Vue 组件与组合式 API 见 [../frontend/vue.md](../frontend/vue.md)；
  通用组件设计见 [../frontend/component.md](../frontend/component.md)。
- HTTP 接口契约见 [../backend/api.md](../backend/api.md)。

## 8. 测试与验证

- 断言覆盖成功、失败、边界三类路径；不只用快照测试代替行为断言。
- Mock 遵守 [../../core/testing-principles.md](../../core/testing-principles.md) §10。
- 提交前必须实际运行：类型检查（**指定正确的 tsconfig**）、lint、测试、构建；
  大范围格式化前后各跑一次类型检查，以隔离"格式化引入的问题"。

## 9. 提交前自检

1. 无新增 `any` / `@ts-ignore`（或逐条说明理由）。
2. 别名与 `tsconfig` 配置一致，导入不依赖隐式解析。
3. 无未处理 Promise、无循环依赖、无非空断言滥用。
4. 外部输入已在边界校验。
5. 类型检查、lint、测试、构建均已实际运行并记录结果。
