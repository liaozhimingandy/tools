# Cursor 映射关系

> 逐项说明公共规范源如何映射到 Cursor 的原生文件。
> 状态与适配方式口径见 [`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)；官方依据见 [`references.md`](references.md)。

---

## 1. 映射总表

| 公共来源 | Cursor 原生文件 / 目录 | 对应关系 | 需转换 | 可直接复用 | 已知限制 | 官方依据 |
| --- | --- | --- | --- | --- | --- | --- |
| `core/`（原则） | `.cursor/rules/*.mdc` + `.ai-standards/core/` | 红线入常驻 `.mdc`，其余按需读镜像 | 是（裁剪 + frontmatter + 索引） | 否 | 必须 `.mdc`，无 frontmatter 不被发现 | `rules` [A] |
| `standards/`（技术） | 入口按需索引 + `.ai-standards/standards/` | 只给索引，不机械拆分 | 否 | 是（镜像） | 技术栈级规则可用 `globs` 另建 | `rules` [A] |
| `skills/`（5 个） | `.cursor/skills/<name>/` | 1:1 复制目录 | **否** | **是（逐字节）** | 只写 6 标准字段 | `skills` [A] |
| `agents/`（4 角色） | `.cursor/agents/*.md` | 正文 → prompt，提取 `name`/`description` | 是（字段官方确认） | 正文可复用 | 工具字段由目标项目定 | `subagents` [A] |
| Hooks | 不生成 | 仅记录能力边界 | — | — | 需 `.cursor/hooks.json`，属用户资产 | `hooks` [A] |

---

## 2. 常驻规则映射（`.mdc` 转换）

这是 Cursor 与其余三工具最大的**格式转换点**：

| 项 | 公共源 | Cursor 目标 | 转换说明 |
| --- | --- | --- | --- |
| 文件格式 | `adapters/cursor/rules/ai-engineering-standards.mdc`（已是 `.mdc`） | `.cursor/rules/ai-engineering-standards.mdc` | 已是官方格式，直接复制 |
| frontmatter | `description` + `alwaysApply: true` | 官方三字段中的两个 | `alwaysApply: true` 保证常驻；不设 `globs`（对所有任务适用） |
| 正文 | 红线摘要 + 按需索引 | 原样 | 不复制规范正文；镜像路径用反引号（`@file` 不内联） |
| 归属标记 | HTML 注释 | 保留 | 安装器据此判断托管/用户文件 |

**frontmatter 字段决策**（官方 [A]）：

| 字段 | 是否写 | 原因 |
| --- | --- | --- |
| `alwaysApply` | 写 `true` | 通用红线需每次会话常驻 |
| `description` | 写 | Agent 判断相关性用；`alwaysApply: true` 时虽被忽略，但保留语义清晰 |
| `globs` | 不写 | 本规则不限定文件；技术栈级规则应另建独立 `.mdc` |
| `icon` / `color` | 不写 | Cursor 扩展字段，跨版本 `UNVERIFIED`，且破坏工具无关 |

## 3. Skills 映射（直接复用）

| 公共 Skill 源 | 目标（POSIX） | 转换 | Frontmatter 处理 |
| --- | --- | --- | --- |
| `skills/project-analysis/` | `.cursor/skills/project-analysis/` | 无（整目录复制） | 保持 6 标准字段 |
| `skills/requirements-analysis/` | `.cursor/skills/requirements-analysis/` | 无 | 同上 |
| `skills/architecture-design/` | `.cursor/skills/architecture-design/` | 无 | 同上 |
| `skills/software-development/` | `.cursor/skills/software-development/` | 无 | 同上 |
| `skills/code-review/` | `.cursor/skills/code-review/` | 无 | 同上 |

- 选 `.cursor/skills/`（而非 `.agents/skills/`）：两者都是官方项目级路径，选前者可明确"这份由 Cursor 适配器管理"，避免与其它工具的 `.agents/skills/` 副本混淆。
- **不写** `paths`/`disable-model-invocation`/`icon`/`color` 等扩展字段。Cursor 对嵌套 `.cursor/skills/` 会自动限定作用域，无需 `paths`。
- **引用路径**：`SKILL.md` 内相对一级引用 `references/`、`assets/`，与 Cursor"相对技能根"要求一致。

## 4. Agent 角色映射（正文复用 + 官方字段）

| 公共角色 | 目标文件 | `name` | `description` | 正文 | 扩展字段 |
| --- | --- | --- | --- | --- | --- |
| `architect.md` | `.cursor/agents/architect.md` | `architect` | 取自"定位"段 | → prompt，逐字保留 | 目标项目自定 |
| `developer.md` | `.cursor/agents/developer.md` | 同上 | 同上 | 同上 | 同上 |
| `reviewer.md` | `.cursor/agents/reviewer.md` | 同上 | 同上 | 同上 | 同上 |
| `tester.md` | `.cursor/agents/tester.md` | 同上 | 同上 | 同上 | 同上 |

**转换规则**：

1. 正文逐字作为 subagent prompt，不改写角色职责。
2. `name`/`description` 官方标为"可选"，但**建议都写**：`description` 决定 Agent 何时委派，`name` 用于识别（缺省从文件名派生）。
3. `model`（默认 `inherit`）、`readonly`（默认 `false`）、`is_background`（默认 `false`）等**不写入公共源**，由目标项目按需设置（如 reviewer 可设 `readonly: true`）。
4. `.cursor/agents/` 是项目级；冲突时 `.cursor/` 优先于 `.claude/` / `.codex/`。
5. **四类机制互不混淆**：Rules（常驻指令）、Skills（按需工作流）、Subagents（独立上下文被委派）、Hooks（生命周期脚本）分别处理。
6. 本阶段只提供映射模板，不生成安装产物。

## 5. 引用处理与更新同步

- **引用方式**：方案 ②（薄 `.mdc`）+ 方案 ③（需手动引用镜像路径）+ 方案 ④（镜像），见 [`../README.md` §4](../README.md)。`@file` 不内联，故用反引号写明 `.ai-standards/` 路径让 Agent 自行读取。
- **技术栈级规则扩展位**：把 `standards/languages/python.md` 映射为路径规则时，另建 `.cursor/rules/python.mdc`，frontmatter 用 `globs: "**/*.py"` + `alwaysApply: false`，正文只放索引；本阶段不做机械拆分。
- **更新同步**：按清单重算哈希，唯一文件名的 additive 规则永不覆盖用户规则。
- **不产生双源**：`.mdc` 只放红线与索引，完整正文唯一在镜像。

## 6. 相关文档

- 官方参考：[`references.md`](references.md) · 适配说明：[`README.md`](README.md) · 模板：[`templates/`](templates/) · 公共角色：[`../../agents/`](../../agents/)
