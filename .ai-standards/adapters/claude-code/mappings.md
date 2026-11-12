# Claude Code 映射关系

> 逐项说明公共规范源如何映射到 Claude Code 的原生文件。
> 状态与适配方式口径见 [`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)；官方依据见 [`references.md`](references.md)。

---

## 1. 映射总表

| 公共来源 | Claude Code 原生文件 / 目录 | 对应关系 | 需转换 | 可直接复用 | 已知限制 | 官方依据 |
| --- | --- | --- | --- | --- | --- | --- |
| `core/`（原则） | `CLAUDE.md` + `.claude/rules/*.md` + `.ai-standards/core/` | 红线入入口与叠加规则，其余按需读镜像 | 是（裁剪 + 索引 + 叠加规则） | 否 | 拼接无硬优先级 | `memory` [A] |
| `standards/`（技术） | 入口按需索引 + `.ai-standards/standards/` | 只给索引，不机械拆分 | 否 | 是（镜像） | 技术栈细则按需读 | `memory` [A] |
| `skills/`（5 个） | `.claude/skills/<name>/` | 1:1 复制目录 | **否** | **是（逐字节）** | 6 字段白名单；列表 1,536 字符截断 | `skills` [A] |
| `agents/`（4 角色） | `.claude/agents/*.md` | 正文 → system prompt，提取 `name`/`description` | 是（字段官方确认） | 正文可复用 | 工具字段由目标项目定 | `sub-agents` [A] |
| Hooks | 不生成 | 仅记录能力边界 | — | — | 需 `settings.json`，属用户资产 | `hooks` [A] |

---

## 2. 常驻指令映射（双通道）

Claude Code 有两条可并存通道，共同保证"入口被占用仍生效"：

| 通道 | 源文件 | 目标 | frontmatter | 加载时机 | 覆盖策略 |
| --- | --- | --- | --- | --- | --- |
| 入口 | `adapters/claude-code/CLAUDE.md` | `CLAUDE.md` | 无 | 启动，拼接进上下文 | guarded（用户占用则跳过） |
| 叠加规则 | `adapters/claude-code/rules/ai-engineering-standards.md` | `.claude/rules/ai-engineering-standards.md` | **无**（无 `paths`） | 启动，优先级同 `.claude/CLAUDE.md` | additive（唯一文件名，永不覆盖） |

**为何不给叠加规则写 `paths`**：官方规定 `paths` 是规则 frontmatter 中唯一被读取的字段，带 `paths` 会变成"仅当匹配文件被操作时加载"，与"通用红线常驻"的意图冲突。本仓库的 `.claude/rules/` 文件是**全项目通用**，故刻意不带 frontmatter，启动即加载。若未来要加技术栈级规则，应另建带 `paths` 的独立文件（见第 5 节）。

## 3. Skills 映射（直接复用）

| 公共 Skill 源 | 目标（POSIX） | 转换 | Frontmatter 处理 |
| --- | --- | --- | --- |
| `skills/project-analysis/` | `.claude/skills/project-analysis/` | 无（整目录复制） | 保持 6 标准字段 |
| `skills/requirements-analysis/` | `.claude/skills/requirements-analysis/` | 无 | 同上 |
| `skills/architecture-design/` | `.claude/skills/architecture-design/` | 无 | 同上 |
| `skills/software-development/` | `.claude/skills/software-development/` | 无 | 同上 |
| `skills/code-review/` | `.claude/skills/code-review/` | 无 | 同上 |

- **不得添加** `when_to_use`、`argument-hint`、`paths`、`hooks` 等扩展字段：这些在 claude.ai 上传 / Skills API / `package_skill.py` 打包时会导致硬错误（官方原文已确认）[A]。
- **引用路径**：`SKILL.md` 内对 `references/`、`assets/` 用相对一级路径，与 Claude Code"技能目录内一级引用"一致；不引用 `.ai-standards/`（那会让技能在独立打包时失效）。

## 4. Agent 角色映射（正文复用 + 官方字段）

公共 `agents/` 是**角色契约**（纯文本、工具无关），Claude Code 侧映射：

| 公共角色 | 目标文件 | `name` | `description` | 正文 | 工具字段 |
| --- | --- | --- | --- | --- | --- |
| `architect.md` | `.claude/agents/architect.md` | `architect` | 取自"定位"段 | 原文 → system prompt | 目标项目自定 |
| `developer.md` | `.claude/agents/developer.md` | `developer` | 同上 | 同上 | 同上 |
| `reviewer.md` | `.claude/agents/reviewer.md` | `reviewer` | 同上 | 同上 | 同上 |
| `tester.md` | `.claude/agents/tester.md` | `tester` | 同上 | 同上 | 同上 |

**转换规则**：

1. **正文逐字保留**为 system prompt，不改写角色职责（避免与公共源产生第二套定义）。
2. `name` / `description` 是官方**必填**字段；`name` 需唯一、不含 `:`，`description` 决定自动委派时机。
3. 可选 `tools`/`model`/`permissionMode`/`skills`/`mcpServers`/`hooks` 等**不写入公共源**，由目标项目按需要填入（模板中用注释提示）。
4. Claude Code 会递归扫描 `.claude/agents/`；同名时最近目录优先。
5. 本阶段只提供 [`templates/`](templates/) 里的映射模板，不生成安装产物。

## 5. 引用处理与更新同步

- **引用方式**：方案 ②（薄入口）+ 方案 ③（叠加规则通道）+ 方案 ④（镜像），见 [`../README.md` §4](../README.md)。`@path` import 虽是原生能力，但因"不减少上下文成本"而**不采用**。
- **技术栈级规则的未来扩展**：若要把 `standards/languages/python.md` 等映射为路径级规则，应新建带 `paths:` 的独立文件（如 `.claude/rules/python.instructions.md` 配 `paths: ["**/*.py"]`），保持"通用规则常驻、技术规则按需"。本阶段不做机械拆分，避免规则碎片化。
- **更新同步**：`core/standards/skills/agents/` 变更后按清单重算哈希；guarded 入口与 additive 规则分别处理，用户自有同名文件不覆盖。
- **不产生双源**：入口与叠加规则都只放红线与索引，完整正文唯一在镜像。

## 6. 相关文档

- 官方参考：[`references.md`](references.md) · 适配说明：[`README.md`](README.md) · 模板：[`templates/`](templates/) · 公共角色：[`../../agents/`](../../agents/)
