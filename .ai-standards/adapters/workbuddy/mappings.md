# 腾讯 WorkBuddy 映射关系

> 逐项说明公共规范源如何映射到 WorkBuddy 的项目级原生文件。
> 状态与适配方式口径见 [`../../docs/architecture/tool-compatibility.md`](../../docs/architecture/tool-compatibility.md)；官方依据见 [`references.md`](references.md)。

---

## 1. 映射总表

| 公共来源 | WorkBuddy 原生文件 / 目录 | 对应关系 | 需转换 | 可直接复用 | 已知限制 | 官方依据 |
| --- | --- | --- | --- | --- | --- | --- |
| `core/`（原则） | `CODEBUDDY.md` + `.codebuddy/rules/*.md` + `.ai-standards/core/` | 红线入入口与叠加规则，其余按需读镜像 | 是（裁剪 + 索引 + 叠加规则） | 否 | 上下文注入，无硬优先级 | `memory` [A] |
| `standards/`（技术） | 入口按需索引 + `.ai-standards/standards/` | 只给索引，不机械拆分 | 否 | 是（镜像） | 技术栈细则按需读 | `memory` [A] |
| `skills/`（5 个） | `.codebuddy/skills/<name>/` | 1:1 复制目录 | **否** | **是（逐字节）** | 不写工具专有 frontmatter 字段 | `skills` [A] |
| `agents/`（4 角色） | `.codebuddy/agents/*.md`（仅模板） | 正文 → system prompt，提取 `name`/`description` | 是（字段官方确认） | 正文可复用 | 工具字段由目标项目定；本阶段不生成 | `sub-agents` [A] |
| Commands | 不生成 | 5 个 Skill 已覆盖工作流 | — | — | 避免与 Skill 双源 | `slash-commands` [A] |
| 用户级全局规则 | 不生成 | `project_only=True` + `entry=None` | — | — | 任务书禁止写用户级目录 | `codebuddy-dir` [A] |

---

## 2. 常驻指令映射（双通道）

WorkBuddy 有两条可并存的项目级通道，共同保证"入口被占用仍生效"：

| 通道 | 源文件 | 目标 | frontmatter | 加载时机 | 覆盖策略 |
| --- | --- | --- | --- | --- | --- |
| 入口 | `adapters/workbuddy/CODEBUDDY.md` | `CODEBUDDY.md` | 无 | 启动，递归加载主记忆文件 | guarded（用户占用则跳过） |
| 叠加规则 | `adapters/workbuddy/rules/ai-engineering-standards.md` | `.codebuddy/rules/ai-engineering-standards.md` | **无**（默认常驻） | 启动，优先级同 `.codebuddy/CODEBUDDY.md` | additive（唯一文件名，永不覆盖） |

**为何不给叠加规则写 frontmatter**：官方规定默认 `alwaysApply: true`（ALWAYS 常驻）；`alwaysApply: false` + `paths` 会变成"仅当匹配文件被操作时触发"，与"通用红线常驻"的意图冲突。本仓库的 `.codebuddy/rules/` 文件是**全项目通用**，故刻意不带 frontmatter，启动即加载。若未来要加技术栈级规则，应另建带 `paths` 的独立文件（见第 5 节）。

**为何入口用 `CODEBUDDY.md` 而非 `.codebuddy/CODEBUDDY.md`**：官方明确两处等效且都与 `AGENTS.md` 兼容，根目录 `CODEBUDDY.md` 更易被用户和工具发现，且与"项目记忆入口"语义最贴合；系统自动优先使用 `CODEBUDDY.md`。

---

## 3. Skills 映射（直接复用）

| 公共 Skill 源 | 目标（POSIX） | 转换 | Frontmatter 处理 |
| --- | --- | --- | --- |
| `skills/project-analysis/` | `.codebuddy/skills/project-analysis/` | 无（整目录复制） | 保持开放规范字段 |
| `skills/requirements-analysis/` | `.codebuddy/skills/requirements-analysis/` | 无 | 同上 |
| `skills/architecture-design/` | `.codebuddy/skills/architecture-design/` | 无 | 同上 |
| `skills/software-development/` | `.codebuddy/skills/software-development/` | 无 | 同上 |
| `skills/code-review/` | `.codebuddy/skills/code-review/` | 无 | 同上 |

- **不得添加**工具专有字段：本仓库公共 Skill 只用 `name`/`description`/`license`/`metadata` 等开放规范字段，不写某工具独有的配置项，以保持"单源 + 多适配器"（依据 [`../README.md`](../README.md) §5 与 `validator` 的工具字段隔离红线）。
- **引用路径**：`SKILL.md` 内对 `references/`、`assets/` 用相对一级路径，与官方"技能目录内一级引用"一致；不引用 `.ai-standards/`（那会让技能在独立分发时失效）。
- **发现**：项目级 `.codebuddy/skills/<name>/SKILL.md`，`/<skill-name>` 显式或 `description` 隐式触发。

---

## 4. Agent 角色映射（正文复用 + 官方字段，仅模板）

公共 `agents/` 是**角色契约**（纯文本、工具无关），WorkBuddy 侧映射：

| 公共角色 | 目标文件（若启用） | `name` | `description` | 正文 | 工具字段 |
| --- | --- | --- | --- | --- | --- |
| `architect.md` | `.codebuddy/agents/architect.md` | `architect` | 取自"定位"段 | 原文 → system prompt | 目标项目自定 |
| `developer.md` | `.codebuddy/agents/developer.md` | `developer` | 同上 | 同上 | 同上 |
| `reviewer.md` | `.codebuddy/agents/reviewer.md` | `reviewer` | 同上 | 同上 | 同上 |
| `tester.md` | `.codebuddy/agents/tester.md` | `tester` | 同上 | 同上 | 同上 |

**转换规则**：

1. **正文逐字保留**为 system prompt，不改写角色职责（避免与公共源产生第二套定义）。
2. `name` / `description` 是官方**必填**字段；`name` 需唯一、不含 `:`。
3. 可选 `tools` / `model` 等**不写入公共源**，由目标项目按需要填入（模板中用注释提示）。
4. 项目级 `.codebuddy/agents/` 优先于用户级 `~/.codebuddy/agents/`，同名时项目级覆盖。
5. 本阶段**只提供** [`templates/agent-mapping.template.md`](templates/agent-mapping.template.md) 映射模板，**不生成**可安装的 agent 文件；相关发现能力标为"未生成 / 需人工启用后验证"。

---

## 5. 引用处理与更新同步

- **引用方式**：方案 ②（薄入口）+ 方案 ③（叠加规则通道）+ 方案 ④（镜像），见 [`../README.md`](../README.md)。`@path` import 虽是原生能力（≤5 层），但因"会把导入内容并入上下文"而**不采用**拉全量规范。
- **技术栈级规则的未来扩展**：若要把 `standards/languages/python.md` 等映射为条件规则，应新建带 `paths: ["**/*.py"]` 与 `alwaysApply: false` 的**独立**文件（如 `.codebuddy/rules/python.md`），保持"通用规则常驻、技术规则按需"。本阶段不做机械拆分，避免规则碎片化。
- **更新同步**：`core/standards/skills/agents/` 变更后按清单重算哈希；guarded 入口与 additive 规则分别处理，用户自有同名文件不覆盖。
- **不产生双源**：入口与叠加规则都只放红线与索引，完整正文唯一在镜像。

---

## 6. 相关文档

- 官方参考：[`references.md`](references.md) · 适配说明：[`README.md`](README.md) · 模板：[`templates/`](templates/) · 公共角色：[`../../agents/`](../../agents/)
