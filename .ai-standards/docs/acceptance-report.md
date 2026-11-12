# 1.0.0 验收报告

> 验收日期：**2026-11-11** · 环境：Windows / Python 3.14.2 · 规范版本：1.0.0
> 本文是**本次构建的验收快照**，用于追溯。当前状态请重新运行
> `tooling/scripts/validate.py` 与 `tooling/tests/test_tooling.py`，
> 不要把这个快照当作实时结论。

---

## 1. 完整仓库目录树

```text
ai-engineering-standards/
├── README.md · CHANGELOG.md · VERSION · LICENSE · CONTRIBUTING.md
├── core/                       7 份通用原则
│   ├── engineering-principles.md   ├── architecture-principles.md
│   ├── coding-principles.md        ├── security-principles.md
│   ├── testing-principles.md       ├── ai-behavior.md
│   └── documentation-principles.md
├── standards/                  12 份技术规范
│   ├── languages/  python.md typescript.md javascript.md
│   ├── backend/    api.md database.md authentication.md
│   ├── frontend/   vue.md component.md ui.md
│   └── devops/     docker.md git.md ci-cd.md
├── skills/                     5 个 Agent Skills（唯一源）
│   ├── project-analysis/       SKILL.md + assets/ + references/
│   ├── requirements-analysis/  SKILL.md + assets/ + references/
│   ├── architecture-design/    SKILL.md + assets/ + references/
│   ├── software-development/   SKILL.md + assets/ + references/
│   └── code-review/            SKILL.md + assets/ + references/
├── agents/                     architect.md developer.md reviewer.md tester.md
├── adapters/                   6 个适配器文件
│   ├── codex/AGENTS.md
│   ├── claude-code/CLAUDE.md + rules/ai-engineering-standards.md
│   ├── cursor/rules/ai-engineering-standards.mdc
│   └── copilot/copilot-instructions.md + instructions.md
├── tooling/
│   ├── scripts/     install.py · validate.py · check.py
│   ├── validators/  __init__.py · targets.py · common.py
│   ├── templates/   SKILL.md.template · STANDARD.md.template
│   └── tests/       test_tooling.py
├── examples/
│   ├── fastapi-vue/          README.md + 4 份项目专属规则示例
│   └── python-application/   README.md + 1 份项目专属规则示例
└── docs/                       architecture · installation · skills-guide
                                standards-guide · versioning · tool-adapters
                                · acceptance-report
```

统计：**75 个文件，约 408 KiB**；其中 58 个 Markdown 文件全部有实质内容，
无空文件、无占位文件、无内容完全相同的重复文件。

---

## 2. 各核心规范文件的职责

| 文件 | 唯一职责 | 主要可检查点 |
| --- | --- | --- |
| `engineering-principles.md` | 单一职责、高内聚低耦合、DRY/KISS/YAGNI、最小必要修改、复用优先、避免过度设计、模块边界、异常处理、日志、配置、安全边界、文档维护、向后兼容 | 每条规则附"可检查项"，供 `code-review` 逐条核对 |
| `architecture-principles.md` | 现状理解、依赖方向、模块职责与数据归属、接口契约、方案评估、扩展成本、安全性能、数据流、决策记录 | 方案比较 8 维度、依赖无环、唯一写入方 |
| `coding-principles.md` | 命名、函数、类型、错误处理写法、注释、输入校验、并发与时间、可测试性 | 10 条提交前代码级自检 |
| `security-principles.md` | 认证授权分离、最小权限、SQL 注入、XSS、CSRF、SSRF、命令注入、敏感配置、密码 Token、日志脱敏、上传、依赖、API 权限、多租户隔离（14 项全覆盖） | 每节"可检查项"、越权与跨租户用例 |
| `testing-principles.md` | 单元 / 集成 / API / E2E 分层、边界、异常、回归、测试数据、Mock 边界、覆盖率与质量 | 回归"先失败"、Mock 不绕过真实行为 |
| `ai-behavior.md` | **唯一**约束 AI 自身行为：先理解不假设、7 类需授权操作、不得伪造测试、不得谎报完成、高风险先澄清、DB 变更必备 6 项、完成后 4 项汇报 | 每条规则编号，适配器只摘录红线 |
| `documentation-principles.md` | 单一信息源、与代码同批次变更、结构、命令可执行、事实与设计分离、版本记录、面向 AI 的额外要求 | 8 条自检清单 |

优先级：`ai-behavior` > `security-principles` > 其他 `core/` > `standards/` >
`agents/` / `skills/`。已在 [standards-guide.md](standards-guide.md) §5 中显式声明，
且 `security-principles.md` 头部已修正为"除 ai-behavior 外"，避免自相矛盾。

---

## 3. 五个 Skills 的功能

| Skill | 权限 | 9 步 / 10 维工作流 | 关键输出 |
| --- | --- | --- | --- |
| `project-analysis` | 只读 | 目录 → 入口文档 → 依赖技术栈 → 模块边界 → 数据流 → 数据库 → 测试 → 技术债务 → 报告 | 10 章项目分析报告 + 待确认清单 |
| `requirements-analysis` | 只读 | 理解 → 区分明确/假设 → 边界 → 异常 → 影响面 → 验收标准 → 待确认 → 文档 | 10 章结构化需求文档 |
| `architecture-design` | 只读 | 现状 → 问题 → 职责 → 方案 → 依赖 → 扩展维护 → 安全性能 → 数据流 → 文档 → 决策记录 | 8 部分设计文档 + ADR |
| `software-development` | 可写 | 规范 → 需求 → 现有实现 → 最小计划 → 编码 → 测试 → 质量检查 → 修复 → 回归 → 报告 | 代码 + 测试 + 实施报告（4 项必填） |
| `code-review` | 只读 | 业务 / 架构 / 安全 / 数据库事务 / 并发 / 性能 / 错误处理 / 兼容性 / 测试 / 复杂度 | 六字段问题清单 + 合入结论 |

全部通过 Agent Skills 规范校验：`name` 与目录名一致、仅 6 个标准 Frontmatter 字段、
`description` 143–149 字符且含明确触发词、正文 120–133 行（< 500 行）、
9 个必需章节齐全、引用全部是技能目录内一级路径。详细资料放在
`references/`，模板放在 `assets/`，实现渐进披露。
每个 Skill 内联了所需红线，可独立理解与执行，不依赖外部文件。

---

## 4. 四种工具的适配方案

| 工具 | 入口指令（guarded） | 可叠加通道（永不冲突） | Skills 安装目录 |
| --- | --- | --- | --- |
| Codex | `AGENTS.md` | 无（改为提示用户在自有文件中加引用） | `.agents/skills/` |
| Claude Code | `CLAUDE.md` | `.claude/rules/ai-engineering-standards.md` | `.claude/skills/` |
| Cursor | 无 | `.cursor/rules/ai-engineering-standards.mdc`（`alwaysApply: true`） | `.cursor/skills/` |
| Copilot | `.github/copilot-instructions.md` | `.github/instructions/ai-engineering-standards.instructions.md`（`applyTo: "**"`） | `.github/skills/` |

- 所有路径/字段均来自官方文档核实（2026-11-11），来源等级、能力差异矩阵与
  6 项「待验证」条目集中在 [tool-adapters.md](tool-adapters.md)。
- 没有写入任何工具专有配置项到通用位置；`applyTo` 只在 Copilot 路径级文件，
  `alwaysApply` 只在 Cursor `.mdc`，Claude 规则文件无 frontmatter。
- 入口文件被用户占用时跳过并给 WARNING，可叠加通道仍安装，规范不会失效。
- `.ai-standards/` 是规范仓库的完整只读镜像，保证约 100 条内部相对链接
  在安装后仍可解析；其中 `skills/` 不被任何工具当作技能发现目录。

---

## 5. 安装器使用说明

```bash
python tooling/scripts/install.py --tool codex   --target <project>
python tooling/scripts/install.py --tool claude  --target <project>
python tooling/scripts/install.py --tool cursor  --target <project>
python tooling/scripts/install.py --tool copilot --target <project>
python tooling/scripts/install.py --all          --target <project>
python tooling/scripts/install.py --tool codex --dry-run
python tooling/scripts/install.py --all --force
```

`--tool` 可重复；`claude-code` 是 `claude` 的别名；`--version` 打印版本。
实现要点：仅标准库、逐字节复制（`write_bytes`，避免换行符转换）、
`pathlib` 跨平台路径、不创建符号链接、不删除任何文件；
文件分三类（仓库提供 / 用户自有 / 已安装托管），只对第三类且带归属标记或在
`manifest.json` 中登记的文件执行更新；`--force` 更新前打印 unified diff；
安装后逐文件 SHA-256 复核，失败即报错退出；清单记录版本、工具、来源与哈希。
各平台命令示例见 [installation.md](installation.md)。

---

## 6. 验证工具使用说明

| 命令 | 职责 |
| --- | --- |
| `python tooling/scripts/validate.py` | 仓库自检：目录、58 个 Markdown 实质内容、Skill Frontmatter 与官方规范一致性、name 与目录名一致、无效内部引用、重复文件、安装目标路径合法性、适配器格式、README 12 章、standards 是否引用 core |
| `python tooling/scripts/check.py --target <project>` | 安装结果自检：manifest schema/版本、逐文件 SHA-256、已装工具的 Skills 与适配器格式、归属标记、镜像内部链接、用户文件是否被误覆盖 |
| `python -m unittest discover -s tooling/tests -v` | 23 项自动化验收测试 |

分级：`ERROR` 必须修复（退出码 1）、`WARNING` 建议修复、`INFO` 提示。
两个脚本共用 `tooling/validators/targets.py`（唯一路径事实来源）与
`common.py`（分级报告、受约束 YAML 子集解析、Skill/适配器校验）。

---

## 7. 自动化测试结果（实际执行）

```
validate.py      : 0 ERROR / 0 WARNING / 4 INFO；检查 58 Markdown、5 Skill、6 适配器
unittest         : Ran 23 tests in 50.4s — OK（exit 0）
install --all --dry-run : CREATE=139；未写入任何文件（exit 0）
真实安装 codex + copilot → check.py : 0 ERROR / 0 WARNING / 1 INFO（exit 0）
manifest         : version=1.0.0, tools=['codex','copilot'], files=99
```

23 项测试覆盖：仓库自检、路径静态校验、工具别名、dry-run 零写入、
dry-run 路径可移植性（无 `..`/反斜杠/盘符）、四种工具分别安装 + 各自 `check.py`、
`--all`、已有用户文件保护（含 `--force` 也不覆盖）、`--force` 差异输出与修复、
manifest 版本与 135 个文件哈希、篡改检测、增量安装保留前一工具、
含空格的目标路径、镜像内部链接（断言检查了 >20 条链接，非空跑）、
未安装目录的明确报错、非法 Skill 校验、Frontmatter 解析、路径合法性单元测试。

单独测试过的安装目录生成：`.agents/skills/`（Codex）、`.claude/skills/`（Claude Code）、
`.cursor/skills/`（Cursor）、`.github/skills/`（Copilot）——共 4 种，超过要求的 2 种。

**发现并修复的真实缺陷**：
1. `check.py` 曾把"用户自有、已被安装器跳过"的入口适配器当作托管适配器校验，
   误报 9 个 ERROR；已改为按 `manifest.files` 判定归属，用户文件只输出 INFO。
2. SKILL.md 初版曾引用 `../../core/...`，安装到工具目录后链接会失效；
   已改为"红线内联 + 纯文本路径提示"，并在 `validate.py` 中把这类引用判为 ERROR。
3. 规范本体只复制部分目录会导致内部相对链接失效；已改为 `.ai-standards/`
   完整只读镜像，并由 `check.py` 检查镜像内链接。
4. `security-principles.md` 的优先级表述与 `ai-behavior.md` 冲突；已修正。

---

## 8. 已知限制

| # | 限制 | 影响与处置 |
| --- | --- | --- |
| 1 | 未集成官方 `skills-ref` 校验器 | 它是需单独安装的外部工具，与零依赖约束冲突。自建校验覆盖规范中明确列出的约束，但**不宣称与其结果完全等价**（待验证） |
| 2 | 未实现用户级（home 目录）安装作用域 | 第一版只做项目级 `--target`；全局配置属用户资产，风险更高，留待后续评估 |
| 3 | Codex 的 `.codex/skills/` 兼容路径与 `name`/`description` 单独长度上限未获官方直接确认 | 只依赖官方明确给出的 `.agents/skills/`；描述控制在 150 字符内以适配初始列表预算（待验证） |
| 4 | Copilot 路径级 `.instructions.md` 在各 IDE 版本的实际读取行为、`excludeAgent` 跨环境行为未确认 | 同时提供仓库级 + 路径级两份，且不设置 `excludeAgent`（待验证） |
| 5 | `developers.openai.com` 部分页面直接抓取返回 `Forbidden` | 结论由官方站点检索索引与官方中文镜像交叉确认，来源等级已在 `tool-adapters.md` 逐条标注 |
| 6 | 安装器不自动卸载、不自动删除源中已移除的旧文件 | 只报 WARNING，避免误删用户资产；手工步骤见 `installation.md` §11 |
| 7 | `.ai-standards/skills/` 是引用镜像，四个工具目录另有 4 份 Skill 副本 | 目标项目存在 5 份相同内容，属"单源 + 多适配器"的必要代价；清单记录每份哈希 |
| 8 | 未验证 AI 工具运行时的真实加载效果 | 本机沙箱无法启动各工具客户端；已验证的是**文件布局、格式与完整性**，工具实际发现行为需在真实客户端中人工确认 |
| 9 | 第一版不含 Agent 编排系统 | `agents/` 只是角色契约，无运行时；符合"稳定、可理解、易扩展"的第一版目标 |

---

## 9. 后续版本建议

按优先级排序：

1. **真实客户端冒烟验证**：在装有 Codex / Claude Code / Cursor / Copilot 的机器上
   各跑一次"输入触发词 → 确认 Skill 被加载"，把第 8 节的待验证项转为已验证。
2. **集成官方 `skills-ref`**（可选开关）：提供 `--use-skills-ref` 作为补充校验，
   不破坏零依赖默认路径，并对比自建校验的差异。
3. **用户级安装作用域**：`--scope user`，为四个工具的 home 目录安装 Skills，
   需要更严格的冲突检测与备份策略。
4. **`uninstall` / `prune`**：基于 manifest 的显式卸载，带 dry-run 与确认，
   严格限定只删除托管文件。
5. **更多 Skills 与语言**：`database-migration`、`security-review`、`release-notes`；
   `go.md` / `java.md` / `rust.md` 等语言规范。
6. **规则冲突的语义检查**：目前 `validate.py` 只查重复文件与链接，
   可增加"同一主题出现在多个 core/standards 文件"的启发式检测。
7. **清单签名与来源追溯**：为 `manifest.json` 提供可选的校验和签名，
   便于在团队中审计规范版本。
8. **CI 模板**：提供可直接复用的 GitHub Actions / 流水线片段，
   把 `validate.py` 与 `check.py` 作为门禁。
