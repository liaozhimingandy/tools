# JavaScript 规范

> **何时读**：编写或审查**无类型标注**的 JavaScript（含 `.js` / `.jsx` / `.mjs` / `.cjs`）代码时。
> TypeScript 项目见 [typescript.md](typescript.md)。
> **前提**：[../../core/coding-principles.md](../../core/coding-principles.md)。

---

## 1. 模块与语法

- 遵循项目既有的模块体系（ESM 或 CommonJS），不在同一模块混用 `import` 与 `require`。
- 使用 `const` / `let`，不使用 `var`；变量声明靠近首次使用处。
- 文件名与项目既有风格一致（`.js` / `.mjs` / `.cjs` 的语义差异必须遵守，
  不通过改后缀来"修"模块加载问题）。
- 不使用 `eval`、`with`、隐式全局；严格模式由项目配置统一保证。

## 2. 无类型环境下的形状约束

没有编译期类型，形状必须在**边界**显式校验：

- 函数入口对关键参数做类型与取值校验，校验失败返回明确错误，不静默兜底。
- 用 JSDoc（`@param` / `@returns` / `@typedef`）描述公开函数的数据形状；
  若项目开启了 `checkJs`，注释即契约，必须随代码同步更新。
- 用 `Object.freeze` 或不可变写法保护配置与常量对象。
- 有限取值集中定义为常量对象（`Object.freeze({ ... })`），不散落字符串字面量。

## 3. 相等、空值与隐式转换

- 使用 `===` / `!==`；需要允许 `null`/`undefined` 时显式写出判断。
- 区分 `undefined`、`null`、`0`、`""`、`false`；不用 `||` 提供默认值而误伤有效假值，
  使用 `??`。
- 避免依赖隐式类型转换做业务判断；解析外部输入时显式转换并校验结果
  （`Number.isFinite` 等）。
- 数组方法回调中注意 `this` 绑定与稀疏数组；不依赖 `sort()` 的默认字符串排序做数值排序。

## 4. 异步与错误

- 统一 `async/await`；所有 Promise 必须被 `await`、返回或显式处理，
  禁止未处理的 rejection。
- `catch` 的参数按未知类型处理；读取 `message` 前先判断类型。
- 不吞掉异常；错误向能处理的层级传播，见
  [../../core/engineering-principles.md](../../core/engineering-principles.md) §8。
- 并发用 `Promise.all` / `allSettled`；需要串行时显式串行，避免意外并行写入。

## 5. 安全

- 不使用 `innerHTML`、`document.write`、`eval`、`new Function` 承载不可信数据，见
  [../../core/security-principles.md](../../core/security-principles.md) §4。
- 原型污染：合并外部对象时过滤 `__proto__` / `constructor` / `prototype` 键；
  优先用 `Object.create(null)` 或 `Map` 承载键值数据。
- 不要在客户端做唯一的安全判定；服务端必须独立校验，见
  [../../core/security-principles.md](../../core/security-principles.md) §13。
- Node 侧调用子进程使用参数数组，不用 `shell: true`，见
  [../../core/security-principles.md](../../core/security-principles.md) §7。

## 6. 环境与兼容

- 明确目标运行时（浏览器 / Node 版本），不使用目标环境不支持的 API。
- 浏览器代码不假设全局对象存在（SSR、Web Worker 等场景）；访问 `window`/`document`
  前做环境判断。
- 不在模块顶层执行 I/O 或读取环境变量作为隐式初始化；初始化显式化、可测试。

## 7. 测试与验证

- 因缺少编译期检查，边界与异常测试更重要：见
  [../../core/testing-principles.md](../../core/testing-principles.md) §6、§7。
- 至少对公开函数覆盖：正常输入、缺失/非法输入、空集合、失败回调。
- 提交前实际运行 lint、测试与构建；不把"没报错"当作"已验证"。

## 8. 提交前自检

1. 无 `var`、无未处理 Promise、无隐式全局。
2. 关键边界有显式输入校验与 JSDoc。
3. 有限取值集中定义，未散落魔法字符串。
4. 无危险的 DOM / 原型操作，无客户端独有安全判定。
5. lint、测试、构建均已实际运行并记录结果。
