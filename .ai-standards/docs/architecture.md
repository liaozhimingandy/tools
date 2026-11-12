# 架构说明

> 本文解释**规范源、工具适配器、安装器**三者之间的关系，以及为什么不采用"每个工具各写一份规则"的方案。
> 版本：1.0.0 · 适用范围：本仓库全部内容

---

## 1. 问题与目标

AI 编程工具读取指令的方式各不相同：有的读 `AGENTS.md`，有的读 `CLAUDE.md`，
有的要求 `.mdc` + frontmatter，有的要求 `.instructions.md` + `applyTo`。
如果直接为每个工具各写一份完整规范，会产生：

- **规则漂移**：同一条规则在四份文件里表述逐渐不一致，甚至互相矛盾；
- **上下文膨胀**：入口文件必须常驻上下文，规范越多越贵；
- **无法验收**：没有机器可读的证据证明"装上了、装对了、没被改坏"。

因此本仓库把"内容"与"工具"彻底分开，并把"验证"做成一等公民。

设计目标按优先级排序：**可验证 > 可移植 > 不破坏用户配置 > 按需加载 > 可扩展 > 简单**。
"架构完整"不在此列——任何不直接服务于以上目标的机制都不引入。

---

## 2. 三层模型

```
                          ┌──────────────────────────────────────┐
                          │           规范源层 (Source)           │
                          │  core/  standards/  skills/  agents/ │
                          │  · 工具无关、项目无关                 │
                          │  · 唯一事实来源，只在这里编辑         │
                          └──────────────┬───────────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │ 引用（按需加载）          │ 复制（安装）              │ 引用
              ▼                          ▼                          ▼
   ┌────────────────────┐    ┌────────────────────┐    ┌────────────────────┐
   │   工具适配层        │    │     安装与验证层    │    │    目标项目        │
   │   adapters/<tool>/  │───▶│  tooling/scripts/   │───▶│  .ai-standards/    │
   │   · 薄，含归属标记  │    │  install.py         │    │  + 工具约定目录     │
   │   · 只放常驻规则    │    │  validate/check.py  │    │  + manifest.json   │
   └────────────────────┘    └────────────────────┘    └────────────────────┘
```

**依赖方向是单向的**：适配器引用规范源，安装器读取适配器和规范源，
规范源永远不知道自己会被哪个工具使用。这是"工具无关"能成立的结构性保证。

### 2.1 规范源层

| 目录 | 职责 | 不许做什么 |
| --- | --- | --- |
| `core/` | 定义 7 类通用原则（工程 / 架构 / 编码 / 安全 / 测试 / AI 行为 / 文档） | 不得写某个框架的专属细节，不得写工具名作为条件 |
| `standards/` | 按 `languages / backend / frontend / devops` 分组的可落地技术规范 | 不得重复 `core/` 的原则，只能引用并具体化 |
| `skills/` | Agent Skills 的**唯一源文件**，遵循开放规范 | 不得包含工具专有 frontmatter 字段 |
| `agents/` | 四种角色的职责边界与协作接口（纯文本，不是可执行 Agent 编排） | 不得定义编排引擎、状态机或调度逻辑 |

第一版刻意**不做** Agent 编排系统：`agents/` 只是角色契约，供人和 AI 阅读，
不引入运行时。这是"第一版以稳定、可理解、易扩展为目标"的直接体现。

### 2.2 工具适配层

适配器是**薄翻译层**，不是规范的副本。每个适配器文件包含：

1. 归属标记（HTML 注释，安装器据此判断文件是谁写的）；
2. 少量必须常驻的红线规则（10~20 条，来自 `core/ai-behavior.md` 与 `core/security-principles.md`）；
3. 一个"规范索引"，指向安装到 `.ai-standards/` 的详细规范，要求 AI 按需读取；
4. 该工具的能力边界说明（哪些事做不到，不要假装做得到）。

适配器**不复制** `core/` / `standards/` 正文，也不写工具专有的配置项到通用位置。
例如 `applyTo` 只出现在 Copilot 的 `.instructions.md`，`alwaysApply` 只出现在
Cursor 的 `.mdc`，Claude Code 的 `paths` 只出现在 `.claude/rules/`。

### 2.3 安装与验证层

| 组件 | 单一职责 |
| --- | --- |
| `tooling/validators/targets.py` | 定义五种工具的安装目标路径矩阵（唯一的路径事实来源；含 WorkBuddy 的 `project_only` 标志） |
| `tooling/validators/common.py` | Frontmatter 解析、Markdown 检查、Skill 规范校验、适配器格式校验、分级报告 |
| `tooling/scripts/install.py` | 从源复制到目标、保护用户文件、记录版本与哈希、安装后完整性校验 |
| `tooling/scripts/validate.py` | 检查**本仓库**结构与内容是否合规 |
| `tooling/scripts/check.py` | 检查**目标项目**的安装结果是否与清单一致 |
| `tooling/tests/test_tooling.py` | 自动化验收：dry-run、五种工具、保护、更新、跨平台路径、完整性 |
| `tooling/tests/test_workbuddy_adapter.py` | WorkBuddy 适配器专项：官方路径映射、project-only 隔离、 Skills 单源一致、用户文件保护 |

`install.py` 与 `check.py` 共享 `targets.py`，避免"安装到 A、检查却在找 B"这类漂移。

---

## 3. 安装后的目标项目布局

以 `--all` 为例（`<target>` 为目标项目根目录）：

```text
<target>/
├── AGENTS.md                                   # Codex（仅当不存在或本仓库管理）
├── CLAUDE.md                                   # Claude Code（同上）
├── .claude/
│   ├── rules/ai-engineering-standards.md       # Claude Code（可叠加，永不覆盖他人文件）
│   └── skills/<skill-name>/SKILL.md            # Claude Code Skills
├── .cursor/
│   ├── rules/ai-engineering-standards.mdc      # Cursor Project Rule
│   └── skills/<skill-name>/SKILL.md            # Cursor Skills
├── .github/
│   ├── copilot-instructions.md                 # Copilot 仓库级（仅当不存在或本仓库管理）
│   ├── instructions/
│   │   └── ai-engineering-standards.instructions.md   # Copilot 路径级（可叠加）
│   └── skills/<skill-name>/SKILL.md            # Copilot Agent Skills
├── .agents/skills/<skill-name>/SKILL.md        # Codex Skills（官方 REPO 作用域）
└── .ai-standards/                              # ★ 本仓库独占目录：规范本体的只读镜像
    ├── manifest.json                           # 生成：版本 + 每个文件 SHA-256 + 来源 + 归属
    ├── README.md · CHANGELOG.md · VERSION · LICENSE · CONTRIBUTING.md
    ├── core/ · standards/ · agents/ · adapters/ · docs/
    ├── skills/                                 # 仅作引用镜像，不被任何工具当作技能发现目录
    └── tooling/templates/
```

`.ai-standards/` 是**归属隔离区**，也是**规范仓库的完整只读镜像**：
安装器把源仓库中除脚本与测试以外的全部内容按原目录结构复制进来。

这样做的理由是**链接完整性**：`core/` 中的规范会链接 `../standards/...`、
`../skills/...`、`../docs/...`，`docs/` 会链接 `../core/...` 与
`../tooling/templates/...`。若只复制部分目录，这些内部链接在安装后就会失效，
AI 会去读取不存在的文件——这恰恰违反 `core/ai-behavior.md` §2.2。
保持镜像结构后，所有相对链接在安装前后都指向同一份内容。

镜像中的 `skills/` **不会被任何工具当作技能发现目录**（五种工具只扫描
`.agents/skills/`、`.claude/skills/`、`.cursor/skills/`、`.github/skills/`、
`.codebuddy/skills/`），因此不会造成重复加载。安装器只在 `.ai-standards/` 内增删自己管理的文件，
绝不扫描或清理目标项目的其他目录。

---

## 4. 文件归属与不覆盖策略

这是整个设计中风险最高的部分，因此规则被写得非常机械、可被测试验证：

安装器把目标路径上的文件分成三类：

| 类别 | 判定依据 | 行为 |
| --- | --- | --- |
| **仓库提供的文件** | 源文件存在于 `skills/`、`adapters/`、`core/`、`standards/`、`agents/` | 只作为复制来源，绝不修改 |
| **用户自有文件** | 目标文件已存在，且不含归属标记，或不在 `manifest.json` 中 | **永不覆盖、永不删除、永不追加**；输出 WARNING，给出手工合并建议 |
| **已安装的规范文件** | 含归属标记 **且** 在 `manifest.json` 中登记，哈希与清单一致 | 可更新；`--force` 时先打印 unified diff 再覆盖 |

具体约束：

1. `--force` **只**作用于第三类文件；对第二类文件即使 `--force` 也拒绝，并返回明确错误。
2. 入口文件（`AGENTS.md` / `CLAUDE.md` / `.github/copilot-instructions.md`）若被用户占用，
   安装器跳过它们，但仍安装**可叠加**的规则文件，保证规范不因冲突而完全失效：
   `.claude/rules/`、` .cursor/rules/`、` .github/instructions/` 使用带项目前缀的唯一文件名，
   天然不会与用户规则同名。
3. `SKILL.md` 保持与源逐字节一致（不放归属标记），其归属改由 `manifest.json` 记录；
   其余适配器文件顶部带 `<!-- AI-ENGINEERING-STANDARDS:MANAGED ... -->` 标记。
4. 安装器**不删除**任何文件。源中被移除的旧文件只在报告中给 WARNING，由人决定是否清理。
5. `manifest.json` 最后写入；写入前对每个已复制文件做一次 SHA-256 复核，
   复核失败即报错并退出（不留下"看起来装好了"的假象）。

---

## 5. 按需加载的实现

Agent Skills 开放规范定义了三段式渐进披露：

1. **发现**：启动时只加载全部 Skill 的 `name` + `description`（约 100 tokens/个）；
2. **激活**：任务匹配时把该 `SKILL.md` 正文读入上下文（建议 < 5000 tokens / < 500 行）；
3. **执行**：`references/`、`scripts/`、`assets/` 只在正文明确引用时才加载。

本仓库额外做了一层：适配器里只有红线规则 + 索引，详细原则留在 `.ai-standards/`，
由 AI 在遇到具体任务时按索引读取。因此"规范全量"从不进入常驻上下文。

所有 `SKILL.md` 控制在 500 行以内，长资料拆到 `references/`，且引用保持一级深度，
避免深层引用链带来的上下文与失效风险。

---

## 6. 相对原始需求的目录调整（含原因）

官方规范核实后，对最初设想的目录做了三处最小调整，均记录在案：

| 原设想 | 调整后 | 原因（官方依据） |
| --- | --- | --- |
| `adapters/cursor/rules/`（空目录） | `adapters/cursor/rules/ai-engineering-standards.mdc` | Cursor 官方：Project Rules 必须放在 `.cursor/rules/` 且扩展名为 `.mdc`，需 `description`/`globs`/`alwaysApply` frontmatter；放在该目录的 `.md` 会被忽略。空目录没有意义 |
| `adapters/copilot/instructions.md`（单文件） | `copilot-instructions.md` + `instructions.md` 两份 | GitHub 官方明确区分**仓库级** `.github/copilot-instructions.md` 与**路径级** `.github/instructions/*.instructions.md`（需 `applyTo`），两者格式与生效范围不同，不能合并成一份 |
| `adapters/claude-code/CLAUDE.md`（单文件） | 增加 `adapters/claude-code/rules/ai-engineering-standards.md` | Claude Code 官方支持 `.claude/rules/*.md` 与 `CLAUDE.md` 并列加载。由于入口 `CLAUDE.md` 极易被用户占用，提供一份可叠加规则可保证"不覆盖用户配置"与"规范仍然生效"同时成立 |

另外新增了 `tooling/tests/`（自动化验收要求）与 `docs/tool-adapters.md`（记录官方依据、
能力差异与待验证项）。除此之外未增加任何框架、配置文件格式或运行时组件。

官方核实结果、来源链接与"待验证"标记集中在 [tool-adapters.md](tool-adapters.md)。

**Phase 4 增补**：四种工具的能力判定（项目/全局规则、Skills、自定义 Agent、Hooks、
文件引用、自动发现、子目录规则、MCP、规则优先级）与官方依据，集中见
[能力对照表](architecture/tool-compatibility.md)；统一映射架构、公共规范引用处理、
符号链接评估与版本兼容管理见 [`adapters/README.md`](../adapters/README.md)。
`adapters/` 各工具目录补齐 `README.md` / `mappings.md` / `references.md` / `templates/` 四件套。

**Phase 6 增补**：新增腾讯 WorkBuddy 作为第 5 个工具适配器 `adapters/workbuddy/`，
同样四件套 + 入口 `CODEBUDDY.md` + 叠加规则 `rules/` + 两份映射模板。它是唯一的
**project-only** 工具：任务书禁止写用户级目录，故无 `global/`，`--scope global` 时
由 `GlobalToolSpec.project_only` 通用标志 + 安装器/校验器守卫完全跳过。Skills 仍从
`skills/` 单源逐字节复制到 `.codebuddy/skills/`，公共规范镜像仍共享一份。
Agents / Commands 按决策只给模板或不生成，避免重复实现与双源。能力判定见
[能力对照表 §8](architecture/tool-compatibility.md#8-workbuddyphase-6-新增)，
安装边界见 [installation.md §4.6](installation.md#46-腾讯-workbuddy-项目级安装project-only)。
此阶段**未改安装器/验证器架构**，只做注册表数据扩展 + 通用 project-only 守卫。

---

## 7. 关键设计决策（ADR 摘要）

| # | 决策 | 理由 | 放弃的替代方案 |
| --- | --- | --- | --- |
| ADR-1 | Skills 单源、按工具分别复制 | 各工具官方发现路径不同，无法共用同一目录；复制比符号链接更可移植 | 符号链接（Windows 需管理员/开发者模式，Git 可能检出成纯文本） |
| ADR-2 | 只用 Python 标准库 | 零依赖、跨平台、可直接 `python install.py` | PyYAML（引入第三方包）、Node 脚本（并非所有项目都有 Node） |
| ADR-3 | Frontmatter 用受约束的 YAML 子集解析 | 本仓库实际只使用标量/单行映射/短字符串，解析器可短小且可测 | 完整 YAML 实现（复杂度与依赖都不划算） |
| ADR-4 | 入口适配器 guarded、附加规则 additive | 用户入口文件是高价值资产，绝不能被安装器改动 | 自动追加文本块（会污染用户文件、幂等性差） |
| ADR-5 | `manifest.json` 记录版本与哈希 | 让"可验证"落地：版本可查、篡改可检、更新可比对 | 仅写版本号文件（无法发现文件被改坏） |
| ADR-6 | `validate.py` 与 `check.py` 分离 | 仓库自检与安装结果检查是两件事，失败时的处置不同 | 一个脚本做两件事（职责不清、CI 难用） |
| ADR-7 | 第一版不做 Agent 编排 | 编排系统会带来状态、调度与调试成本，且不影响规范落地 | 多 Agent 工作流引擎 |
| ADR-8 | WorkBuddy 为 project-only，global 作用域由通用标志跳过 | 任务书禁止写用户级目录；`GlobalToolSpec.project_only` 是通用能力，安装器/校验器统一守卫，不硬编码工具名 | 为单工具写死 `if tool == "workbuddy"` 分支（破坏注册表驱动架构） |
| ADR-9 | 项目指令（`CODEBUDDY.md`）与项目级代码规则（`.codebuddy/rules/`）分离，不生成用户级全局规则 | 任务书明令二者不可混为一谈、不可写全局规则；双通道兼顾"入口被占用仍生效"与"不覆盖用户配置" | 把全部规范塞进单个全局 `CODEBUDDY.md`（污染用户全局、无法保护自配置） |

---

## 8. 可扩展点

| 想扩展什么 | 改哪里 | 是否需要改架构 |
| --- | --- | --- |
| 新增语言 / 框架规范 | `standards/<group>/<name>.md` + 在适配器索引里加一行 | 否 |
| 新增 Skill | `skills/<name>/SKILL.md`（模板在 `tooling/templates/`） | 否 |
| 新增工具适配器 | `adapters/<tool>/` + `tooling/validators/targets.py` 增加一个条目 | 否（只需扩展数据） |
| 新增自动检查项 | `tooling/validators/common.py` 增加一个校验函数并在两个脚本中注册 | 否 |
| 新增安装作用域（用户级） | `targets.py` 增加 user-scope 路径 | 需评估，但不需要改模型 |

扩展的唯一硬约束：**新增内容不得让规范源反过来依赖适配器或安装器**。

---

## 9. 验收入口

```bash
python tooling/scripts/validate.py                       # 仓库自检
python -m unittest discover -s tooling/tests -v          # 自动化测试
python tooling/scripts/install.py --all --dry-run        # 安装计划
python tooling/scripts/check.py --target <installed>     # 安装结果自检
```

详见 [installation.md](installation.md)、[skills-guide.md](skills-guide.md)、
[standards-guide.md](standards-guide.md)、[versioning.md](versioning.md)、
[acceptance-report.md](acceptance-report.md)（1.0.0 验收快照）。
