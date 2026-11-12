# 变更日志

本文件记录 `ai-engineering-standards` 的规范与工具变更。
版本号规则见 [docs/versioning.md](docs/versioning.md)。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
变更类型：`新增` / `变更` / `废弃` / `修复` / `移除` / `安全`。

---

## [Unreleased] - 腾讯 WorkBuddy 适配器（第 5 个工具）

> 本段记录新增腾讯 WorkBuddy 适配器的变更，尚未发版。按 [版本规则](docs/versioning.md)，
> 新增工具适配器属 `MINOR`；是否升版留待阶段审查裁决，本阶段不擅自改动 `VERSION`（仍为 `1.0.0`）。
> 本阶段严格复用 Phase 5 安装器与 Phase 6 门禁，只做注册表数据扩展 + 通用 project-only 守卫，
> 不重造公共机制、不改公共规范 `core/standards/skills/agents`。

### 新增

- **WorkBuddy 适配器** `adapters/workbuddy/`：四件套（`README.md` / `mappings.md` /
  `references.md` / `templates/`）+ 入口 `CODEBUDDY.md`（guarded）+ 叠加规则
  `rules/ai-engineering-standards.md`（additive，无 frontmatter 默认常驻）+ 两份映射模板
  （`agent-mapping.template.md` / `codebuddy-rules-snippet.template.md`）。官方依据 5 篇
  workbuddy.cn 文档逐能力核实（[A]，2026-11-11）。
- **project-only 通用能力**：`GlobalToolSpec.project_only` 字段，`build_plan()` 与
  `check.py` 统一守卫——`--scope global`（含 `--all`）时完全跳过该工具，不写 `~/.codebuddy/`。
  非硬编码工具名，其余四工具 global 行为不变。
- **专项测试** `tooling/tests/test_workbuddy_adapter.py`：20 项，覆盖注册表/双源一致、
  官方路径映射、Rules/CODEBUDDY.md 格式、Skills 逐字节单源、重复安装、用户自有保护、
  托管文件升级备份、manifest 版本归属、global 零写入、五工具并存不影响四工具。
- **文档**：WorkBuddy 适配说明/映射/官方参考；能力矩阵新增 §8；安装器文档新增 §4.6
  项目级安装；架构、统一映射架构、安装目标核实、global 集成说明、示例与 README 同步为五工具。

### 变更

- `tooling/validators/targets.py`：`TOOLS` 加 `workbuddy`（第 5 个工具）、
  `TOOL_SPECS` 加项目映射（`.codebuddy/skills` + `CODEBUDDY.md` + `.codebuddy/rules/`）、
  `GLOBAL_TOOL_SPECS` 加 `project_only` 项、别名 `codebuddy` / `tencent-workbuddy`、
  `check_paths` 加 project-only 护栏。
- `tooling/config/targets.json`：同步 `tools` / `project.workbuddy` / `global.workbuddy`，
  新增 `project_only` 可比字段；`adapter_validator` 增加 `tool_aliases` 与 `project_only`
  双源比对。
- `tooling/scripts/install.py`：CLI help/别名提示更新为五工具，docstring 说明 project-only。
- `tooling/validators/common.py`：`REQUIRED_FILES` 纳入 7 个 WorkBuddy 适配文件。
- 受影响的现有测试 docstring 由"四种工具"更新为"五种工具"（断言本就基于 `T.TOOLS`，无需改逻辑）。

### 明确不做（本阶段）

- 不生成可执行 `.codebuddy/agents/`（只给映射模板）、不生成 Commands（5 个 Skill 已覆盖）。
- 不写任何用户级全局规则 / 用户级 Skills（`project_only=True`）。
- 不升 `VERSION`、不改公共规范、不重造安装器/验证器架构、不扩展其他新功能。
- 真实客户端运行时加载无法在本环境证明，全部标为未验证，不宣称通过。

---

## [Unreleased] - Phase 6（质量治理与正式发布体系）

> 本段记录 Phase 6 变更，尚未发版。按 [版本规则](docs/versioning.md)，新增质量门禁、
> 发布检查与 CI 流程属 `MINOR`；是否升版留待阶段审查裁决，本阶段不擅自改动 `VERSION`
> （仍为 `1.0.0`）。Phase 6 严格复用 Phase 5 已有的安装器与验证器，不重造其检查逻辑。

### 新增

- **统一质量门禁** `tooling/scripts/quality_gate.py`：把 Phase 5 验证器按五组编排
  （公共规范 / Skills / 适配器 / 安装器 / 版本管理），支持 `--strict`、`--group`、
  `--json`、`--repo`；退出码 0/1/2。每个检查项直接调用既有 validator，只编排不重造。
- **严格规则单一来源** `tooling/validators/quality_rules.py`：`STRICT_PROMOTIONS`
  与 `apply_strict()` 集中定义 WARNING→ERROR 升级规则，`validate.py`、
  `quality_gate.py`、`release_check.py` 共用，消除三处漂移。
- **版本一致性校验** `tooling/validators/version_validator.py`：统一核对 `VERSION`、
  安装器版本双源、README badge、CHANGELOG 版本段与 Git Tag；提供发布产物清单
  `release_file_list()` 与 Tag 解析 `version_from_tag()` 两个单一来源函数。
- **发布前检查** `tooling/scripts/release_check.py`：叠加版本专项、五组门禁、发布产物
  完整性与全量测试；四态检查项（PASS/FAIL/UNVERIFIABLE/SKIPPED），不把无法执行项伪装通过。
- **发布归档工具** `tooling/scripts/build_release_artifact.py`：标准库 `zipfile` 构建 /
  校验归档，写入 `RELEASE-MANIFEST.json`，与发布检查共用清单单一来源。
- **发布 workflow** `.github/workflows/release.yml`：仅推送 `v*.*.*` Tag 触发，
  严格解析 Tag、跑发布检查、构建并校验归档、拒绝覆盖已有 Release，再创建 GitHub Release。
- **跨模块回归测试** `tooling/tests/test_regression.py`：七个变异场景 + 新增文件纳入验证
  + 干净副本反向保护，验证门禁确实能发现破坏。
- **升级兼容性测试** `tooling/tests/test_upgrade_compatibility.py`：九个场景覆盖旧→新升级、
  用户改过的托管文件默认保护 / `--force` 备份后覆盖、用户自有文件永不覆盖、新增文件安装、
  源文件删除不误删、失败回滚、manifest 终态、global 隔离升级、升级后仍过门禁。
- **质量与发布文档** 6 篇：`docs/quality/{quality-gates,regression-testing,
  compatibility-testing}.md`、`docs/release/{versioning,release-process,release-checklist}.md`；
  `docs/release/versioning.md` 为发布视角薄入口，版本规则权威源仍是 `docs/versioning.md`。

### 变更

- `tooling/scripts/validate.py` 删除本地 `STRICT_PROMOTIONS` / `apply_strict()`，改为从
  `quality_rules` 导入，行为不变（`--strict` 仍 0 ERROR / 0 WARNING）。
- `tooling/validators/consistency_validator.py` 新增 `check_core_mapping()`：检查每份 core
  规范是否被引用，补齐 Phase 5 只校验"链接目标存在"而不校验"规范是否被映射"的方向。
- `tooling/validators/common.py` 的 `REQUIRED_FILES` 纳入 Phase 6 脚本、workflow、
  两个新验证器与 6 篇文档，使结构门禁能发现关键文件缺失。
- `.github/workflows/ci.yml` 矩阵新增 `quality_gate.py --strict` 聚合门禁，并新增
  `quality-gate` 汇总 job（依赖矩阵通过，再跑严格门禁与发布检查）。
- `README.md` 目录结构补 Phase 6 脚本、workflow 与文档入口。

### 明确不做（本阶段）

- 不升 `VERSION`、不创建真实 GitHub Release（须推 Tag 由 workflow 执行）。
- 不重新实现 Phase 5 的安装器、验证器、一致性检查，只做编排与复用。
- 不引入任何框架、服务或第三方依赖；发布归档用标准库，CI 用 GitHub Actions。
- 不擅自进入 Phase 7。

---

## [Unreleased] - Phase 5（安装器、验证器与自动化质量检查）

> 本段记录 Phase 5 变更，尚未发版。按 [版本规则](docs/versioning.md)，新增安装器、
> 验证器、CI 与 CLI 参数属 `MINOR`；`--strict` 的错误分级与退出码语义变化需阶段审查
> 裁决。本阶段不擅自改动 `VERSION`（仍为 `1.0.0`）。

### 新增

- **安装核心** `tooling/installer/`（5 个模块 + `__init__`）：
  - `filesystem.py`：路径安全 `ensure_within`、原子写入 `atomic_write`、多文件事务
    `Transaction` 回滚（只回收本次创建/替换，不递归删除用户目录）。
  - `manifest.py`：manifest schema 1 读写；归属分类 `ABSENT`/`MANAGED`/`MODIFIED`/
    `USER`/`ORPHAN`；SHA-256 期望内容哈希登记与用户修改检测。
  - `backup.py`：`--force` 覆盖前备份，布局 `<管理目录>/backups/<run_id>/`。
  - `resolver.py`：`build_plan()` 双作用域安装计划、`render_global_entry()` 生成文件渲染。
  - `manager.py`：安装编排 `decide`/`print_plan`/`print_diff`/`print_list`/`summary`/`install`。
- **机器可读目标映射** `tooling/config/targets.json`：project/global 两套 entries、
  aliases、skills、global_integration；与 `validators/targets.py` 常量做一致性校验，
  防止双源漂移（该文件是代码常量的可校验导出快照，非第二事实来源）。
- **global 集成模板** `adapters/GLOBAL-INTEGRATION.template.md`；**global 入口模板** ×3
  （`adapters/{codex,claude-code,copilot}/global/ENTRY.md`）。Cursor 依据 Phase 4 官方
  核实结果无磁盘可写的全局规则路径，故不生成全局入口、不编造路径。
- **5 个新验证器** `tooling/validators/{markdown,reference,adapter,skill,consistency}_validator.py`：
  代码块闭合/标题层级、内部链接/图片/配置源、适配器格式/config 漂移/工具字段泄漏、
  Skill 规范/一级资源引用、core 六段/语义冲突人工审查信号/生成文件新鲜度。
- **6 个新测试文件**（71 项用例）：`test_installer`、`test_manifest`、`test_skill_validator`、
  `test_reference_validator`、`test_adapter_validator`、`test_consistency`，全部使用
  `tempfile` 隔离；global 场景以 `--home` 隔离，不触碰真实 home。
- **CI** `.github/workflows/ci.yml`：Windows/Linux/macOS × Python 3.10/3.12 矩阵，
  执行 `validate.py --strict`、`check.py --all`、install dry-run、`unittest discover`。
- **工具链说明** `tooling/README.md`、`tooling/pyproject.toml`（纯元数据、零第三方依赖、
  不声明 build-system，明确不是 pip 包）。

### 变更

- `tooling/scripts/install.py` 改为薄 CLI，委托 `installer.manager.install()`；保留
  `--tool/--all/--target/--dry-run/--force/--version`，新增
  `--scope project|global`、`--list`、`--home PATH`（逻辑 home 根，用于隔离测试/CI）。
- `tooling/scripts/validate.py` 重写：新增 `--skills`/`--core`/`--adapters`/`--strict`；
  `STRICT_PROMOTIONS` 定义 9 条 WARNING→ERROR 升级规则并逐条打印；退出码 0/1/2。
- `tooling/scripts/check.py` 升级为双职责：默认安装结果检查（含 global scope、manifest
  scope 推断、生成文件新鲜度）与 `--skills`/`--adapters`/`--all` 仓库一致性检查；六类报告
  「正常/缺失/过期/不一致/无法验证/需人工」，不把人工评审冒充自动通过。
- `tooling/validators/targets.py` 扩展 global 作用域、共享常量；生成版本 token 下沉为
  `GENERATED_VERSION_TOKEN`，使 validators 不再反向依赖 installer。
- `tooling/validators/common.py` 的 `check_version()` 改为按 `^##\s*\[VERSION\]` 正则
  在全文匹配，消除 Unreleased 段增长把 `[1.0.0]` 挤出前 2000 字符窗口的假 WARNING。
- 文档同步：`README.md`（Phase 5 架构/安装/安全/FAQ）、`docs/installation.md`
  （`--scope`/`--home`/`--list`、§4.5 global 安装、更新/备份/卸载）、
  `docs/skills-guide.md`、`docs/standards-guide.md`（检查清单与自动检查边界）。

### 安全

- 默认禁止覆盖任何已存在文件；`--force` 也**不覆盖用户自有文件**，仅允许覆盖经清单
  登记且未被修改的托管文件，或经用户 `--force` 明确授权的已修改托管文件（覆盖前备份）。
- 归属判定以清单登记为准、SHA-256 比对识别用户修改；归属标记
  `AI-ENGINEERING-STANDARDS:MANAGED` 仅作孤儿识别辅助证据（Skills/镜像逐字节复制，无标记）。
- 路径安全校验防路径穿越、绝对路径逃逸、符号链接逃逸；原子写入 + 多文件事务回滚保证
  中途失败不留半成品。
- manifest 只登记相对路径、SHA-256、source、category、generated、scope、时间戳等，
  不写绝对路径或敏感信息；schema 保持 1，只增字段、向后兼容。
- 生成文件（global 入口）以 `version=GENERATED` 为源模板标记，安装时渲染真实 VERSION；
  `check.py` 以同一函数重算新鲜度，避免模板与产物漂移。

### 明确不做（本阶段）

- 不升 `VERSION`、不擅自发版（留待阶段审查裁决）。
- 不做最终项目验收与真实业务项目集成（属 Phase 6）。
- 不集成官方 `skills-ref`，不宣称与官方参考实现完全等价。
- 不提供自动卸载；按 manifest 手工逐项删除，绝不误删用户文件。
- 不生成任何 Hooks 自动化或自定义 Agent 配置文件。

---

## [Unreleased] - Phase 4（工具适配层）

> 本段记录 Phase 4 变更，尚未发版。版本号是否升级（按 [版本规则](docs/versioning.md)，
> 新增适配器文档/映射属 `MINOR`；Phase 3 的 `code-review` 分级改写属破坏性变更）
> 留待阶段审查裁决，本阶段不擅自改动 `VERSION`。

### 新增

- **能力对照表** `docs/architecture/tool-compatibility.md`：四种工具 11 项能力的
  `SUPPORTED`/`PARTIAL`/`UNSUPPORTED`/`UNVERIFIED` 判定 + 五种适配方式 + 逐能力官方依据 +
  `UNVERIFIED` 清单。
- **统一映射架构** `adapters/README.md`：公共源→四工具映射清单、映射规则、公共规范引用
  处理（直接引用/薄入口/叠加副本/镜像）、符号链接 vs 复制跨平台评估、公共规范版本与
  工具适配版本分别管理。
- **四个适配器四件套**：`adapters/{codex,claude-code,cursor,copilot}/` 各补
  `README.md`、`mappings.md`、`references.md`、`templates/`。
- **模板**：Codex/Claude/Copilot 项目入口叠加片段、Cursor/Copilot 路径级规则模板、
  Claude/Cursor/Copilot 的 Agent 角色映射模板（字段全部来自官方，不虚构）。
- **官方参考** `references.md` ×4：逐条记录文档标题、URL、查阅日期（2026-11-11）、
  来源等级与逐能力依据。

### 变更

- `docs/tool-adapters.md`：顶部加 Phase 4 复核提示，补齐自定义 Agent / Hooks / MCP 三行，
  修正 Phase 1 未覆盖的能力（以新能力矩阵为权威来源）。
- `docs/architecture.md`：补能力对照表与统一映射文档的引用。
- 据官方最新文档确认（相对 Phase 1 结论的更新）：
  Copilot 支持 Agent Hooks 与 Custom Agents；Codex 支持 Hooks 与 `config.toml [agents]`；
  Cursor 支持 Hooks / Subagents / MCP。均只记录能力，不生成自动化配置。

### 明确不做（本阶段）

- 不开发正式安装器、完整验证器、自动化安装流程（属 Phase 5）。
- 不生成任何 Hooks 自动化或自定义 Agent 配置文件。
- 不升 `VERSION`、不改 `skills/` 与 `core/` 内容、不改 `targets.py`。

---

## [1.0.0] - 2026-11-11

首个稳定版本。目标：稳定、可理解、易扩展；不包含 Agent 编排系统。

### 新增

- **规范源层**
  - `core/` 7 份通用原则：工程、架构、编码、安全、测试、AI 行为、文档。
  - `standards/` 12 份技术规范，按 `languages / backend / frontend / devops` 分组。
  - `agents/` 4 个角色契约：architect / developer / reviewer / tester。
- **Skills**（遵循 Agent Skills 开放规范，唯一源在 `skills/`）
  - `project-analysis`、`requirements-analysis`、`architecture-design`、
    `software-development`、`code-review`。
- **工具适配层**
  - Codex：`AGENTS.md`；Claude Code：`CLAUDE.md` + `.claude/rules/*.md`；
    Cursor：`.cursor/rules/*.mdc`；Copilot：仓库级 + 路径级两份指令。
  - [docs/tool-adapters.md](docs/tool-adapters.md) 记录四条工具链的官方核实结果、
    来源等级、能力差异与待验证项。
- **安装与验证层**（仅 Python 3.10+ 标准库）
  - `install.py`：`--tool` / `--all` / `--dry-run` / `--force` / `--target`，
    跨平台路径、用户文件保护、差异展示、版本记录、安装后完整性校验、明确错误分级。
  - `validate.py`：仓库自检（目录、内容、Frontmatter、命名、引用、重复文件、
    安装目标合法性、适配器格式）。
  - `check.py`：目标项目安装结果自检（清单、哈希、版本、Skills、适配器）。
  - `tooling/tests/test_tooling.py`：自动化验收测试。
- **文档与示例**
  - README 12 个必需章节、`docs/` 7 份指南（含 1.0.0 验收报告）、
    `examples/` 两个真实接入示例、`tooling/templates/` 新 Skill / 新规范模板。

### 设计决策

- Skills 单源、按工具官方路径分别复制；不使用符号链接（Windows 可移植性）。
- 入口适配器 guarded、附加规则 additive；任何情况下不覆盖用户自有文件。
- `.ai-standards/manifest.json` 记录版本与 SHA-256，让"可验证"落地。
- Frontmatter 使用受约束的 YAML 子集解析，零第三方依赖。

### 已知限制

见 [README §12](README.md) 与最终验收报告。主要包括：
未集成官方 `skills-ref` 校验器；未实现用户级（home 目录）安装作用域；
Codex 的 `.codex/skills/` 兼容路径与 `name`/`description` 单独长度上限待官方确认；
Copilot 路径级指令在不同 IDE 版本的实际读取行为待验证。
