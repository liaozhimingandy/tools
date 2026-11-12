# 工具适配层（Adapters）

> 本文说明**公共规范 → 五种工具**的统一映射架构、公共规范的引用处理方式、以及版本兼容管理。
> 能力状态见 [`../docs/architecture/tool-compatibility.md`](../docs/architecture/tool-compatibility.md)；
> 安装目标格式与历史核实记录见 [`../docs/tool-adapters.md`](../docs/tool-adapters.md)。

---

## 1. 适配层定位

适配层是**薄翻译层**，不是第二套规范。唯一事实来源始终是公共规范：

```text
                     公共规范源（唯一权威，工具无关）
     core/ · standards/ · skills/ · agents/ · docs/
                           │
                           │  映射 / 转换 / 分发
     ┌──────────────┬──────┼──────┬──────────────┬───────────────┐
     ▼              ▼      ▼      ▼              ▼               ▼
 adapters/     adapters/  adapters/  adapters/  adapters/
 codex/        claude-code/ cursor/   copilot/   workbuddy/（project-only）
     │              │      │      │              │               │
     ▼              ▼      ▼      ▼              ▼               ▼
 AGENTS.md      CLAUDE.md  .cursor/  .github/     CODEBUDDY.md +
 .agents/       + .claude/ rules/    copilot-     .codebuddy/rules/
 skills/        rules/     .cursor/  instructions  .codebuddy/skills/
                .claude/   skills/   .github/*      （不写用户级目录）
                skills/
```

> **WorkBuddy 的特殊性**：其余四工具有 project + global 两种作用域；WorkBuddy 是
> project-only（`GlobalToolSpec.project_only=True`），`--scope global` 完全跳过，
> 不写 `~/.codebuddy/`。详见 [`workbuddy/README.md`](workbuddy/README.md)。

**四类工具机制互不混淆**（本仓库严格分开处理，不得混为一谈）：

| 机制 | 作用 | 加载方式 | 本仓库对应 |
| --- | --- | --- | --- |
| **Rules** | 常驻指令 / 红线 | 每次会话或匹配文件时进入上下文 | 入口 `AGENTS.md` / `CLAUDE.md` / `.mdc` / `copilot-instructions.md` |
| **Skills** | 按需工作流 | 被选中才加载 `SKILL.md`，资源再按需 | `skills/` 单源 → 各工具原生 Skills 目录 |
| **Agents** | 专门角色 | 被委派任务时以独立上下文运行 | `agents/` 角色契约 → 各工具 agent 配置 |
| **Hooks** | 生命周期脚本 | 特定事件触发、执行用户脚本 | 本阶段仅记录能力边界，**不生成** |

> 能读 Markdown 不等于支持 Skills；能读目录不等于会自动发现。判定口径见
> `../docs/architecture/tool-compatibility.md` §0.4。

**三条硬约束**：

1. 公共规范是唯一权威来源，`adapters/` 不得成为另一套独立规范。
2. 适配文件**不重新维护完整的规范正文**，只放"必须常驻的少量红线 + 按需加载索引 + 能力边界"。
3. 工具专属内容只处理**适配差异**（格式、路径、字段），不得改变公共规范含义。

公共规范更新后，如何定位受影响的适配文件：所有适配入口都含 `<!-- AI-ENGINEERING-STANDARDS:MANAGED ... -->` 归属标记，并经 `manifest.json` 记录来源与哈希；`check.py` 可比对哪些托管文件需要同步（该机制由 Phase 5 安装器落地，本阶段只定义契约）。

---

## 2. 统一映射清单

| 公共来源 | Codex | Claude Code | Cursor | Copilot | 适配方式 |
| --- | --- | --- | --- | --- | --- |
| `core/`（7 份原则 + README） | 入口 `AGENTS.md` 索引 + `.ai-standards/core/` 镜像 | 入口 `CLAUDE.md` + `.claude/rules/*.md` 索引 + 镜像 | `.cursor/rules/*.mdc`（`alwaysApply`）索引 + 镜像 | `.github/copilot-instructions.md` + `.github/instructions/*.instructions.md` 索引 + 镜像 | ④ 需适配：入口文件 + 完整镜像 |
| `standards/`（12 份技术规范） | 入口按需加载索引 | 入口按需加载索引 | 入口按需加载索引 | 入口按需加载索引 | ③/④ 索引引用，不逐条拆规则 |
| `skills/`（5 个 Skill） | `.agents/skills/` | `.claude/skills/` | `.cursor/skills/` | `.github/skills/` | ①/④ **内容直接复用**，仅复制目录 |
| `agents/`（4 个角色契约） | 映射说明（`config.toml [agents]`） | `.claude/agents/*.md` 映射模板 | `.cursor/agents/*.md` 映射模板 | `.github/agents/*.md` 映射模板 | ④ 需转换：正文复用，`name`/`description` 提取 |
| `docs/` | `.ai-standards/docs/` 镜像 | 同左 | 同左 | 同左 | ① 只读镜像 |

### 2.1 每个适配器的七项要素

按用户要求，逐一说明"公共来源 / 工具原生文件 / 对应关系 / 是否转换 / 是否可直接复用 / 已知限制 / 官方依据"：

| 适配器 | ① 公共来源 | ② 工具原生文件 | ③ 对应关系 | ④ 需转换 | ⑤ 可直接复用 | ⑥ 已知限制 | ⑦ 官方依据 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [`codex/`](codex/README.md) | `core/standards/skills/agents/` | `AGENTS.md`、`.agents/skills/` | 1 入口 + 5 Skills | 入口需薄化；Skills 不转换 | **Skills 内容逐字节复用** | `.codex/skills/` 兼容路径、`[agents]` 字段 `UNVERIFIED` | 见 `codex/references.md` |
| [`claude-code/`](claude-code/README.md) | 同上 | `CLAUDE.md`、`.claude/rules/`、`.claude/skills/` | 1 入口 + 1 叠加规则 + 5 Skills | 入口与叠加规则需薄化；Skills 不转换 | **Skills 内容逐字节复用** | 无硬优先级；cloud sessions 不读本机 skills | 见 `claude-code/references.md` |
| [`cursor/`](cursor/README.md) | 同上 | `.cursor/rules/*.mdc`、`.cursor/skills/` | 1 常驻规则 + 5 Skills | `.md`→`.mdc` + frontmatter；Skills 不转换 | **Skills 内容逐字节复用** | 仅 `.mdc` 被发现；`icon/color` 跨版本 `UNVERIFIED` | 见 `cursor/references.md` |
| [`copilot/`](copilot/README.md) | 同上 | `.github/copilot-instructions.md`、`.github/instructions/`、`.github/skills/` | 2 指令（仓库级+路径级）+ 5 Skills | 两份指令需薄化；Skills 不转换 | **Skills 内容逐字节复用** | 路径级指令 surface 依赖；无内联 import 证据 | 见 `copilot/references.md` |
| [`workbuddy/`](workbuddy/README.md) | 同上 | `CODEBUDDY.md`、`.codebuddy/rules/`、`.codebuddy/skills/` | 1 入口 + 1 叠加规则 + 5 Skills | 入口与叠加规则需薄化；Skills 不转换 | **Skills 内容逐字节复用** | project-only，不写用户级目录；桌面端目录名待验证；Agents/Commands 只给模板 | 见 `workbuddy/references.md` |

**结论**：五种工具在"常驻指令"与"Skills 发现路径"上**没有共同交集**，必须由适配层分别分发；而 **Skills 的 `SKILL.md` 内容可以完全统一**，因为都遵循 Agent Skills 开放规范。这正是"单源 + 多适配器"的价值。

---

## 3. 映射规则

| 公共来源 | 目标 | 适配方式 | 是否转换 | 依据 |
| --- | --- | --- | --- | --- |
| `core/` | 各工具规则入口 | 引用或组织（薄入口 + 镜像） | 是（裁剪为红线 + 索引） | §1 硬约束 2 |
| `standards/` | 技术规则 | 按需引用，不机械拆分 | 否（保留在镜像，入口给索引） | Cursor 官方建议"引用文件而非复制内容" |
| `skills/` | 各工具原生 Skills 目录 | **直接复制，逐字节一致** | 否 | 五工具均遵循开放规范，见 `tool-compatibility.md` §3 |
| `agents/` | 各工具自定义 Agent | 正文复用 + 字段提取 | 是（字段随工具而变） | `tool-compatibility.md` §4 |
| Hooks | 不生成 | 仅记录能力边界 | 否 | 用户要求；见 `tool-compatibility.md` §5 |

**不做的映射**（避免虚构配置）：

- 不把 `AGENTS.md` 说成所有工具都读（Claude Code 默认读 `CLAUDE.md`；
  WorkBuddy 兼容 `AGENTS.md` 但 `CODEBUDDY.md` 优先）。
- 不把 `.mdc` / `applyTo` / `paths` / `alwaysApply` 写进 `skills/` 或 `core/`。
- 不写 `config.toml` / `settings.json` / `hooks.json` / `cli-config.json` 等工具专有配置（属用户资产且随版本变化）。
- 不把 4 个角色契约当成可执行编排（见 `../agents/architect.md`）。

---

## 4. 公共规范的引用处理（重点）

用户要求：不能假设各工具都支持 `请读取 ../../core/README.md` 这类相对引用。必须按工具能力选方案。

| 方案 | 适用条件 | 本仓库是否采用 |
| --- | --- | --- |
| ① 直接引用公共文件 | 工具原生支持内联 import 且安装后路径稳定 | **否**：Claude Code 有 `@path`（最多 4 跳）、WorkBuddy 的 `CODEBUDDY.md` 有 `@path`（最多 5 层），但都不省上下文；其余工具无官方内联 import 证据 |
| ② 生成简洁的工具入口文件 | 所有工具都支持读取常驻入口 | **是**：五个入口只放红线 + 索引，避免超长 |
| ③ 生成工具专属规则副本 | 需要按路径/技术栈生效 | **部分**：Claude `.claude/rules/`、Copilot `.instructions.md`、Cursor `.mdc`、WorkBuddy `.codebuddy/rules/` 各有叠加通道；但**不复制全文** |
| ④ 安装阶段复制/链接完整镜像 | 需要保证内部相对链接安装后仍成立 | **是**：复制 `.ai-standards/` 完整只读镜像（非符号链接，理由见 §5） |

**为什么入口不写 `../../core/README.md` 这类链接**：安装后目标项目里规范本体在 `.ai-standards/core/`，而入口在项目根 `AGENTS.md` / `CLAUDE.md` 等。入口统一改用**指向镜像的明确路径**（如 `.ai-standards/core/README.md`），既不依赖工具的内联 import，也不依赖相对层级计算；AI 读懂路径后用自身工具读取。对不支持内联 import 的工具，这属于方案 ③"需手动引用"，索引已明确告诉 AI 去读哪些文件。

**如何避免两个权威版本**：镜像是**只读副本**，由安装器按清单生成，带 `manifest.json` 哈希；用户与 AI 被要求"只在公共源 `core/`/`standards/`/`skills/` 编辑"，镜像内容由 `--force` 重新同步。任何适配入口都**不**复制 `core/` 正文，因此不存在"入口一份、镜像一份"的双源问题。

---

## 5. 符号链接 vs 复制（跨平台评估）

用户要求：若采用符号链接，必须评估三平台与工具读取能力，不得默认可用。

| 维度 | 符号链接 | 安装期复制（本仓库采用） |
| --- | --- | --- |
| Windows | 需管理员权限或"开发者模式"，否则创建失败 | 无特殊权限 |
| Git 检出 | `core.symlinks=false` 或文件系统不支持时，被检出为**纯文本文件**（链接失效且含绝对路径） | 无此风险 |
| Linux / macOS | 原生支持 | 无特殊要求 |
| 工具是否跟随 | 仅 Codex 官方明确"支持软链接技能目录"；Claude 对指向工作区外的规则需批准；其余工具 `UNVERIFIED` | 所有工具都能读普通文件 |
| 可移植性 / 可验证性 | 差（哈希、清单、跨设备同步均复杂） | 好（逐文件 SHA-256 可比对） |

**决策（ADR-1）**：**不依赖符号链接**，Skills 与镜像统一"按工具官方路径复制"。代价是同一 `SKILL.md` 在安装后有多份磁盘副本，但每份都与公共源逐字节一致、由清单校验，不存在规则漂移。

---

## 6. 版本与兼容性

用户要求公共规范版本与工具适配版本**分别管理**，且不得假设所有工具版本能力相同。

### 6.1 两条独立版本线

| 版本线 | 标识 | 存储位置 | 变更触发 |
| --- | --- | --- | --- |
| 公共规范版本 | 语义化版本 `MAJOR.MINOR.PATCH` | [`../VERSION`](../VERSION)、[`../CHANGELOG.md`](../CHANGELOG.md) | 见 [`../docs/versioning.md`](../docs/versioning.md) |
| **工具适配版本** | **官方文档核实日期**（`2026-11-11`）+ 参考文档标题/URL | 各 `references.md` + [`../docs/architecture/tool-compatibility.md`](../docs/architecture/tool-compatibility.md) | 任一工具官方文档路径/字段变化时重新核实并更新日期 |

两条线**互不绑定**：公共规范升级不必然改动适配；工具官方文档变化也不必然改动公共规范。这样能把"规范改了"与"工具改了"两类变更分开定位。

### 6.2 不假设版本能力一致

1. **能力状态按工具分别判定**，见 `tool-compatibility.md`（如 Skills 五工具全支持，但文件内联 import 只有 Claude Code、WorkBuddy 明确支持且有跳数上限）。
2. **区分官方标准能力与工具版本特有能力**：Skills 的 6 字段白名单来自开放规范（标准能力）；`alwaysApply`/`applyTo`/`paths`/`icon` 等是工具扩展（版本特有），**只写在对应适配文件，绝不进公共源**。
3. **兼容范围**：本仓库声明的最低兼容是"各工具官方文档 `2026-11-11` 所描述的路径与字段"。`UNVERIFIED` 项不在兼容承诺内。版本特有行为（如 Copilot 路径级指令的 IDE 差异、Cursor `icon/color`）明确不依赖。
4. **配置变化时如何定位受影响适配文件**：每个适配文件头部归属标记含 `tool=` 与 `source=`，`manifest.json` 记录来源路径；按工具名即可筛出该工具全部托管文件，再按 `tool-compatibility.md` §6–§7 的官方依据逐项复核。

### 6.3 本阶段的兼容声明

- 适配层参考日期：**2026-11-11**；公共规范版本：**`1.0.0`**（未改动，版本是否升级留待审查裁决）。
- 本阶段**只新增说明、模板与能力矩阵**，未修改任何安装目标路径、未改动 `skills/` 内容、未改动 `targets.py`，因此公共规范版本无需变更。
- 官方配置一旦变化，优先修订 `references.md` 与 `tool-compatibility.md`，再评估是否触发适配入口改动与公共规范版本升级。

---

## 7. 目录结构

```text
adapters/
├── README.md                 # 本文：统一映射 + 引用处理 + 版本兼容
├── codex/
│   ├── README.md             # 适配说明
│   ├── mappings.md           # 映射关系（公共源 → 工具文件）
│   ├── references.md         # 官方参考（标题 + URL + 日期 + 状态）
│   ├── templates/            # 入口 / Agent 模板
│   └── AGENTS.md             # 现有入口（Phase 1 建立，本阶段不改动）
├── claude-code/
│   ├── README.md · mappings.md · references.md · templates/
│   ├── CLAUDE.md             # 现有入口
│   └── rules/ai-engineering-standards.md
├── cursor/
│   ├── README.md · mappings.md · references.md · templates/
│   └── rules/ai-engineering-standards.mdc
└── copilot/
    ├── README.md · mappings.md · references.md · templates/
    ├── copilot-instructions.md
    └── instructions.md
```

> 说明：`templates/` 提供"项目自有入口如何叠加公共规范"的模板，供目标项目参考；安装器只安装"受管理"的入口文件（guarded/additive），**不会用模板覆盖用户自有文件**。模板不含归属标记，因其是给人参考的示例而非安装产物。

---

## 8. 相关文档

- 能力矩阵（必读）：[`../docs/architecture/tool-compatibility.md`](../docs/architecture/tool-compatibility.md)
- 安装目标格式：[`../docs/tool-adapters.md`](../docs/tool-adapters.md)
- 架构三层模型：[`../docs/architecture.md`](../docs/architecture.md)
- 版本规则：[`../docs/versioning.md`](../docs/versioning.md)
- Agent Skills 规范：<https://agentskills.io/specification>
