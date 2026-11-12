# AI Engineering Standards

> 跨 AI 编程工具、跨编程语言、跨技术栈、跨软件项目的统一 AI 工程规范体系。

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](VERSION)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Spec](https://img.shields.io/badge/Agent%20Skills-open%20standard-green.svg)](https://agentskills.io/specification)

这不是一份"写给 AI 看的建议清单"，而是一套**可安装、可加载、可执行、可验证**的标准库：
唯一的规范源文件被安装器复制到各 AI 工具官方约定的目录，由适配器文件按需引用，
再由标准库自带的验证脚本检查结构与安装结果是否正确。

---

## 1. 项目定位

| 维度 | 说明 |
| --- | --- |
| 工具无关 | `core/`、`standards/`、`skills/`、`agents/` 不含任何工具专有配置 |
| 项目无关 | 通用规则不绑定任何业务项目；项目专属规则由使用方在项目内另行添加 |
| 标准化 | Skills 遵循 [Agent Skills 开放规范](https://agentskills.io/specification) |
| 按需加载 | 适配器只放"必须常驻"的少量规则，详细规范放在 `.ai-standards/` 供按需查阅 |
| 可执行 | 重要规则都有对应的自动化检查（`validate.py` / `check.py`） |
| 可验证 | 安装结果写入带 SHA-256 的清单，可逐文件校验完整性 |
| 可扩展 | 新增语言、框架、Skill、工具适配器只需扩展数据，不改架构 |
| 零技术依赖 | 安装与验证脚本仅用 Python 3.10+ 标准库 |
| 可移植 | 路径全部使用相对 POSIX 风格，Windows / Linux / macOS 均可运行 |

---

## 2. 为什么需要这套规范

同一个团队里，Codex 写出的代码风格、Claude Code 的审查口径、Cursor 的组件拆分习惯、
Copilot 的异常处理方式往往各不相同。把规则分别写进 `AGENTS.md`、`CLAUDE.md`、
`.cursor/rules/`、`copilot-instructions.md` 会带来三个问题：

1. **规则漂移**：四份文件由不同人维护，几周后内容互相矛盾。
2. **上下文浪费**：把全部规范塞进入口文件，每次对话都要付出完整 token 成本。
3. **无法验证**：没有任何手段能证明"规范真的装上了、装对了、没被改坏"。

本仓库用三层结构解决：

```
规范源（唯一事实来源）  ──安装器──▶  目标项目的工具约定目录
      core/ standards/ skills/ agents/        .agents/skills/ .claude/skills/
                                              .cursor/skills/ .github/skills/
                                              .codebuddy/skills/（腾讯 WorkBuddy）
                                              AGENTS.md / CLAUDE.md / *.mdc / *.instructions.md
                                              CODEBUDDY.md + .codebuddy/rules/*.md
                                              .ai-standards/（规范本体，带归属标记与清单）
```

规则只写一次；工具差异被隔离在 `adapters/`；安装与验证由 `tooling/` 保证。

---

## 3. 架构说明

三层，职责单一，依赖方向单向（适配器 → 规范源，安装器 → 适配器 + 规范源）：

```
┌──────────────────────── 规范源层（工具无关、项目无关）────────────────────────┐
│  core/         通用工程 / 架构 / 编码 / 安全 / 测试 / AI 行为 / 文档 原则      │
│  standards/    按 languages / backend / frontend / devops 分组的技术规范      │
│  skills/       Agent Skills 唯一源文件（SKILL.md + references/ + assets/）    │
│  agents/       角色定义（architect / developer / reviewer / tester）          │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ 被引用 / 被复制
┌───────────────────────────────▼─────────────────────────────────────────────┐
│  工具适配层 adapters/（薄，只做"翻译"，不复制规则正文）                       │
│  codex/AGENTS.md · claude-code/CLAUDE.md · cursor/rules/*.mdc                │
│  copilot/copilot-instructions.md + instructions.md                            │
│  workbuddy/CODEBUDDY.md + rules/*.md（仅 project，不写用户级目录）            │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ install.py
┌───────────────────────────────▼─────────────────────────────────────────────┐
│  安装与验证层 tooling/                                                       │
│  scripts/    install.py（CLI）· validate.py（规范验证）· check.py（一致性）    │
│  installer/  manager（编排）· resolver（计划）· filesystem（原子写/回滚）     │
│              manifest（归属记录）· backup（--force 备份）                     │
│  validators/ skill / markdown / reference / adapter / consistency + common    │
│  config/     targets.json（安装目标映射的可校验导出）                          │
│  templates/ · tests/（6 个测试文件）                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

安装逻辑（`installer/`）与验证逻辑（`validators/`）严格分离：前者负责安全的
计划→事务写入→回滚→清单，后者只做只读检查；两者通过 `targets.py` 这一唯一
路径事实来源与共享常量解耦，互不 import 对方的核心模块。

完整设计决策、归属策略与不覆盖规则见 [docs/architecture.md](docs/architecture.md)，
五种工具的能力差异与官方依据见 [docs/tool-adapters.md](docs/tool-adapters.md)。

---

## 4. 目录结构

```text
ai-engineering-standards/
├── README.md · CHANGELOG.md · VERSION · LICENSE · CONTRIBUTING.md
├── core/                       # 7 份通用原则（工具无关）
│   ├── engineering-principles.md      ├── architecture-principles.md
│   ├── coding-principles.md           ├── security-principles.md
│   ├── testing-principles.md          ├── ai-behavior.md
│   └── documentation-principles.md
├── standards/                  # 12 份技术规范
│   ├── languages/   python.md typescript.md javascript.md
│   ├── backend/     api.md database.md authentication.md
│   ├── frontend/    vue.md component.md ui.md
│   └── devops/      docker.md git.md ci-cd.md
├── skills/                     # Agent Skills 唯一源（每个目录一个 SKILL.md）
│   ├── project-analysis/       ├── requirements-analysis/
│   ├── architecture-design/    ├── software-development/
│   └── code-review/
├── agents/                     # architect / developer / reviewer / tester
├── adapters/                   # 工具适配层（薄）
│   ├── codex/AGENTS.md
│   ├── claude-code/CLAUDE.md + rules/
│   ├── cursor/rules/*.mdc
│   ├── copilot/copilot-instructions.md + instructions.md
│   └── workbuddy/CODEBUDDY.md + rules/（仅 project · project-only）
├── tooling/
│   ├── README.md · pyproject.toml（零依赖元数据）
│   ├── scripts/     install · validate · check · quality_gate ·
│   │                release_check · build_release_artifact（命令入口）
│   ├── installer/   manager · resolver · filesystem · manifest · backup
│   ├── validators/  common · targets · skill / markdown / reference /
│   │                adapter / consistency · quality_rules · version_validator
│   ├── config/      targets.json（安装目标映射的可校验导出）
│   ├── templates/   新 Skill / 新规范模板
│   └── tests/       test_tooling · test_installer · test_manifest ·
│                    test_skill_validator · test_reference_validator ·
│                    test_adapter_validator · test_consistency ·
│                    test_quality_gate · test_release_check ·
│                    test_release_artifact · test_version_validator ·
│                    test_regression · test_upgrade_compatibility ·
│                    test_workbuddy_adapter
├── .github/workflows/         ci.yml（三平台矩阵）· release.yml（Tag 发版）
├── examples/         fastapi-vue/ · python-application/（真实接入示例）
└── docs/             architecture/ · installation · skills-guide
                      standards-guide · versioning · tool-adapters
                      · acceptance-report（1.0.0 验收快照）
                      · quality/（质量门禁 · 回归测试 · 升级兼容性）
                      · release/（版本管理 · 发布流程 · 检查清单）
```

> **相对原始需求的目录调整**（原因已记录，见 `docs/architecture.md` §6）：
> `adapters/cursor/rules/` 内放 `.mdc` 而非空目录（Cursor 官方要求 `.mdc` + frontmatter）；
> `adapters/copilot/` 拆为仓库级与路径级两份（官方是两种不同文件）；
> `adapters/claude-code/rules/` 增加一份可叠加的规则文件（避免覆盖用户已有 `CLAUDE.md`）；
> `adapters/workbuddy/` 是 project-only 适配器（任务书禁止写用户级目录，故无 `global/`）。
> 各适配器为何拆成不同文件，见 [docs/tool-adapters.md](docs/tool-adapters.md)。

---

## 5. 支持的 AI 工具

| 工具 | 适配器（入口指令） | Skills 安装目录 | 官方依据 | 能力边界 |
| --- | --- | --- | --- | --- |
| OpenAI Codex | `AGENTS.md` | `.agents/skills/<name>/` | [AGENTS.md 指南](https://developers.openai.com/codex/guides/agents-md)、[Skills](https://developers.openai.com/codex/skills/) | 支持 Skills 显式/隐式调用；`AGENTS.md` 全局在 `~/.codex/AGENTS.md` |
| Claude Code | `CLAUDE.md` + `.claude/rules/*.md` | `.claude/skills/<name>/` | [Skills](https://code.claude.com/docs/en/skills)、[Memory](https://code.claude.com/docs/en/memory) | 支持 Skills、`/skill-name`；`.claude/rules/` 无 frontmatter 的规则启动时加载 |
| Cursor | `.cursor/rules/*.mdc` | `.cursor/skills/<name>/` | [Rules](https://cursor.com/docs/rules)、[Agent Skills](https://cursor.com/docs/context/skills) | 支持 Skills；Project Rules 必须是 `.mdc`；`.md` 会被忽略 |
| GitHub Copilot | `.github/copilot-instructions.md` + `.github/instructions/*.instructions.md` | `.github/skills/<name>/` | [Custom instructions support](https://docs.github.com/en/copilot/reference/custom-instructions-support)、[Agent skills](https://docs.github.com/en/copilot/concepts/customizations/agent-skills) | 支持 Skills；路径级指令的生效范围随 Copilot 产品不同而不同 |
| 腾讯 WorkBuddy | `CODEBUDDY.md` + `.codebuddy/rules/*.md` | `.codebuddy/skills/<name>/` | [.codebuddy 目录](https://www.workbuddy.cn/docs/cli/codebuddy-dir)、[记忆/规则](https://www.workbuddy.cn/docs/cli/memory)、[Skills](https://www.workbuddy.cn/docs/cli/skills) | 仅 project 作用域（project-only），**不写用户级目录**；`CODEBUDDY.md` 与 `AGENTS.md` 兼容且优先；`--scope global` 完全跳过 |

工具能力差异、`applyTo` / `alwaysApply` / `paths` / `enabled` 等字段的可用性，
以及**待验证**条目，见 [docs/tool-adapters.md](docs/tool-adapters.md)。
本仓库**不会**把某个工具独有的字段写成通用配置。

---

## 6. 安装方法

**环境要求**：Python 3.10+（3.10 / 3.11 / 3.12 / 3.13 均可），**无第三方依赖**，
Windows / Linux / macOS 均可运行；不需要虚拟环境、不需要网络、不需要管理员权限、不使用符号链接。

```bash
# 进入本仓库根目录
cd ai-engineering-standards

# 先自检仓库本身（--strict 把明确的 WARNING 升级为 ERROR）
python tooling/scripts/validate.py --strict

# ── 项目级安装（默认 scope=project）────────────────────────────
python tooling/scripts/install.py --tool codex   --target /path/to/your-project
python tooling/scripts/install.py --tool claude  --target /path/to/your-project
python tooling/scripts/install.py --tool cursor  --target /path/to/your-project
python tooling/scripts/install.py --tool copilot --target /path/to/your-project
python tooling/scripts/install.py --tool workbuddy --scope project --target /path/to/your-project
python tooling/scripts/install.py --all          --target /path/to/your-project

# 预览：只看计划 / 只列目标绝对路径，均不写任何文件
python tooling/scripts/install.py --all --dry-run --target /path/to/your-project
python tooling/scripts/install.py --all --list   --target /path/to/your-project

# 用户级全局安装（对该用户所有项目生效，写入 home 的官方用户级目录）
python tooling/scripts/install.py --all --scope global
# 隔离测试/CI：用 --home 指向逻辑 home，绝不改动真实用户目录
python tooling/scripts/install.py --all --scope global --home /tmp/fakehome

# 更新到新版本（仅覆盖本仓库管理的文件；打印差异、覆盖前自动备份）
python tooling/scripts/install.py --all --force --target /path/to/your-project

# 验证安装结果（project / global）
python tooling/scripts/check.py --target /path/to/your-project
python tooling/scripts/check.py --scope global --target ~
```

别名：`--tool claude` = `--tool claude-code`，`--tool workbuddy` = `--tool codebuddy`
= `--tool tencent-workbuddy`。各平台（Windows / Linux / macOS）的具体命令示例见
[docs/installation.md](docs/installation.md)。

**默认不覆盖用户已有文件**：若 `AGENTS.md` / `CLAUDE.md` / `.github/copilot-instructions.md`
/ `CODEBUDDY.md` 已存在且不是本仓库生成的，安装器会跳过并给出 WARNING（即使 `--force`
也不覆盖），同时仍然安装可叠加的规则文件与 Skills。归属判定**不只看文件名**：以
`manifest.json` 登记 + SHA-256 比对为准，用户改过的托管文件默认跳过、报冲突，
`--force` 时才覆盖且**先备份**。详见 `docs/installation.md` §8 / §12。

**global 作用域的诚实边界**：规范体系统一放在 `~/.ai-engineering-standards/bundle/`，
其余工具共享一份；Skills 按各自官方用户级目录安装。Cursor 的 User Rules 官方**无磁盘
可写路径**，故**不生成**全局入口（不编造配置）；Copilot 全局入口仅 CLI 读取，标 `PARTIAL`。
**WorkBuddy 是 project-only**：任务书禁止写用户级目录，`--scope global` 时完全跳过，
不创建 `~/.codebuddy/`。详见安装后生成的 `~/.ai-engineering-standards/GLOBAL-INTEGRATION.md`。

### 安全机制（摘要）

| 机制 | 行为 |
| --- | --- |
| 默认禁止覆盖 | 用户自有文件永不覆盖；`--force` 也无效 |
| 用户修改检测 | 托管文件哈希与清单不符即判定被改，默认跳过并报冲突 |
| 强制更新 | `--force` 覆盖前自动备份到 `<管理目录>/backups/<时间戳>/`，记录时间与目标 |
| 路径安全 | 所有写入经规范化并校验在受控根内；拒绝 `../` 穿越、绝对路径逃逸、符号链接 |
| 原子写入 | 单文件用「同目录临时文件 + `os.replace`」，失败保留原文件 |
| 事务回滚 | 多文件安装出错时回滚本次创建/修改，**绝不留下虚假成功清单** |
| 归属记录 | `manifest.json` 只含相对路径与哈希，不含绝对路径或敏感信息 |

---

## 7. 如何使用 Skills

Skills 遵循 [Agent Skills 开放规范](https://agentskills.io/specification)，
安装后由工具自动按需发现：启动时只加载 `name` + `description`，
任务匹配时才把 `SKILL.md` 正文放入上下文，参考资料仅在需要时读取。

| Skill | 何时触发 | 产出 |
| --- | --- | --- |
| `project-analysis` | 接手陌生项目、需要先摸清结构 | 项目分析报告（只读，不改代码） |
| `requirements-analysis` | 开发前需要把模糊需求变成可执行规格 | 结构化需求文档 + 待确认清单 |
| `architecture-design` | 需要新增模块、调整边界或做技术选型 | 架构设计文档 + 设计决策记录 |
| `software-development` | 已有明确需求和验收标准，开始实施 | 最小修改 + 测试 + 实施报告 |
| `code-review` | 提交前 / PR 审查 | 按严重程度排序的真实问题清单 |

- Claude Code：`/project-analysis` 等，或直接描述任务让其自动匹配。
- Codex：`/skills` 查看，输入 `$project-analysis` 显式调用，或由 `description` 隐式触发。
- Cursor：Agent 对话中输入 `/` 搜索技能名；也可由 Agent 按上下文自动选择。
- GitHub Copilot：由 Agent 按 `description` 自动发现、按需加载。

创建新 Skill、Frontmatter 规则、篇幅控制与验证步骤见
[docs/skills-guide.md](docs/skills-guide.md)。

---

## 8. 如何为项目增加专属规则

**不要修改安装器生成的文件**——它们会在下次更新时被覆盖。项目专属规则放在：

| 工具 | 建议位置 | 原因 |
| --- | --- | --- |
| Codex | 项目根 `AGENTS.md` 中 `@`-引用之外的自有段落，或子目录 `AGENTS.md` | Codex 按目录层级合并，越靠近工作目录优先级越高 |
| Claude Code | `CLAUDE.local.md`（加入 `.gitignore`）或 `.claude/rules/your-rule.md` | 与共享规则并列加载，不冲突 |
| Cursor | `.cursor/rules/your-rule.mdc`（自定义文件名） | 规则按文件名并存 |
| Copilot | `.github/instructions/your-rule.instructions.md`（带 `applyTo`） | 路径级指令可与其他指令叠加 |

本项目对应的完整接入示例见 `examples/fastapi-vue/` 与 `examples/python-application/`。
原则：**通用规则来自本仓库，项目规则留在项目里，两者不互相覆盖。**

---

## 9. 如何编写新 Skill

最小步骤（详见 [docs/skills-guide.md](docs/skills-guide.md)）：

```bash
mkdir -p skills/my-skill
cp tooling/templates/SKILL.md.template skills/my-skill/SKILL.md
# 编辑 name / description / 正文
python tooling/scripts/validate.py        # 必须通过，无 ERROR
python tooling/scripts/install.py --all --force   # 分发到各工具
python tooling/scripts/check.py --target <your-project>
```

硬性约束：`name` 必须与目录名一致，只允许小写字母/数字/连字符、最长 64 字符；
`description` 1–1024 字符且必须同时说明"做什么"和"何时用"；
`SKILL.md` 不超过 500 行；详细资料放 `references/`，脚本放 `scripts/`，模板放 `assets/`；
文件引用一律使用相对技能根目录的一级路径。

---

## 10. 如何更新规范

```bash
# 1. 修改 core/ standards/ skills/ 中的源文件（唯一改动点）
# 2. 提升版本并写 CHANGELOG
# 3. 自检
python tooling/scripts/validate.py
# 4. 分发到已安装的项目（--force 只更新本仓库管理的文件）
python tooling/scripts/install.py --all --force --target /path/to/your-project
# 5. 验证
python tooling/scripts/check.py --target /path/to/your-project
```

版本号规则、兼容性承诺与废弃流程见 [docs/versioning.md](docs/versioning.md)。
安装器会在 `.ai-standards/manifest.json` 中记录版本与每个文件的 SHA-256，
因此"当前项目装的是哪个版本、哪个文件被改过"始终可查。

---

## 11. 如何贡献规范

见 [CONTRIBUTING.md](CONTRIBUTING.md)。要点：

- 一条规则只在一个文件里定义，其他文件用链接引用，禁止复制粘贴。
- 新增规范必须能被 `validate.py` 检查；能自动化的规则优先写成检查项。
- 修改 `core/ai-behavior.md` 或 `core/security-principles.md` 属于高风险变更，需要说明影响面。
- 提交前必须跑通 `validate.py` 和 `tooling/tests/test_tooling.py`。

---

## 12. 常见问题

**Q：会不会覆盖我项目里已有的 `AGENTS.md` / `CLAUDE.md`？**
不会。安装器把文件分成"仓库提供的 / 用户自有的 / 已安装的规范文件"三类，
只对第三类且带归属标记的文件执行更新。检测到用户文件时输出 WARNING 并跳过，
同时安装可叠加的规则文件，保证规范仍然生效。

**Q：为什么同一份 SKILL.md 在多个目录各有一份？**
因为五个工具的官方发现路径不同。源只有 `skills/` 一份，安装器复制分发；
`manifest.json` 记录每个副本的哈希，`check.py` 保证它们与源一致。

**Q：`--dry-run` 会写文件吗？**
不会。它只打印计划动作（含将要写入的路径与冲突提示），不创建目录、不写清单。

**Q：验证脚本报 WARNING 需要修吗？**
ERROR 必须修复（脚本退出码 1）；WARNING 是建议修复（例如描述缺少触发词）；INFO 仅提示。

**Q：用了 PyYAML 吗？**
没有。为了避免第三方依赖，Frontmatter 由 `tooling/validators/common.py` 中一个受约束的
YAML 子集解析器处理，只支持本仓库实际使用的标量、单行映射与短字符串。

**Q：可以在 Windows 上运行吗？**
可以。所有安装目标都定义为相对 POSIX 路径，由 `pathlib` 统一转换；
不使用符号链接（Windows 创建符号链接需要额外权限），不使用 shell 命令。
CI 在 Windows / Linux / macOS 三平台 × Python 3.10 / 3.12 矩阵上运行，见 `.github/workflows/ci.yml`。

**Q：全局安装会改到哪些目录？会覆盖我的配置吗？**
不会覆盖。`--scope global` 只写其余四工具官方用户级目录与该用户 home 下的
`~/.ai-engineering-standards/`；已存在的全局入口（如 `~/.claude/CLAUDE.md`）若非本工具管理，
一律跳过。**WorkBuddy 例外**：它是 project-only，`--scope global` 时完全跳过，
不写 `~/.codebuddy/`。测试/CI 请用 `--home` 指向隔离目录，避免改动真实 home。

**Q：腾讯 WorkBuddy 怎么装？会写我的全局配置吗？**
`python tooling/scripts/install.py --tool workbuddy --scope project --target ../my-project`。
只在目标项目写 `CODEBUDDY.md` + `.codebuddy/rules/` + `.codebuddy/skills/`，
不写用户级 `~/.codebuddy/`。真实客户端运行时是否加载需人工核对，详见
[adapters/workbuddy/README.md](adapters/workbuddy/README.md)。

**Q：`--force` 会删文件吗？**
不会删任何文件，只会覆盖本仓库管理且内容有变化的文件，覆盖前先备份。
本安装器不提供自动卸载（避免误删用户资产）；卸载步骤见 `docs/installation.md` §12。

**Q：`validate.py`、`check.py` 各自检查什么？**
`validate.py` 检查**仓库自身**是否符合规范（结构、Skills、core 六段、引用、适配器、
config 与代码一致性；`--strict` 升级部分 WARNING）；`check.py` 默认检查**某次安装结果**
（清单、逐文件哈希、版本、生成文件新鲜度），加 `--all/--skills/--adapters` 则检查
**仓库内公共规范与适配器的一致性**，并区分"正常/缺失/过期/不一致/无法验证/需人工"六类。
两者都**不判定语义冲突**，该项一律标人工评审。

**Q：如何验证工具的真实加载？**
本仓库的自动化只做静态配置与哈希检查，不能替代在真实 AI 客户端里的运行验证；
该部分明确列为"需人工验证"，见 `docs/acceptance-report.md`。

---

## 快速验收（本仓库自身）

```bash
python tooling/scripts/validate.py --strict      # 规范验证（0 ERROR）
python tooling/scripts/check.py --all            # 一致性检查（六类报告）
python -m unittest discover -s tooling/tests -v  # 全部自动化测试
python tooling/scripts/install.py --all --dry-run# 安装计划（零写入）
```

License: MIT，见 [LICENSE](LICENSE)。
