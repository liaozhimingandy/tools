# 统一质量门禁

> Phase 6 建立统一质量门禁，把 Phase 5 已有的验证器按职责编排成一个可复用入口，
> **只编排、不重造**：每个检查项都直接调用既有 validator 函数，不复制其校验逻辑。
> 入口：`tooling/scripts/quality_gate.py`。

---

## 1. 定位与原则

在 Phase 5 中，规范检查分散在 `validate.py`（仓库自检）、`check.py`（安装结果检查）
与五个 validator 中。Phase 6 不推翻它们，而是增加一层**聚合门禁**，让"这个版本能不能
进入发布流程"有一个单一判定点。

三条原则：

1. **单一来源**：严格模式的 WARNING→ERROR 升级规则只在
   `tooling/validators/quality_rules.py` 定义一次，`validate.py`、`quality_gate.py`、
   `release_check.py` 三者共用，避免三套规则漂移。
2. **读写分离**：门禁只做只读检查，不修改任何文件；写入始终由安装器负责。
3. **不伪装通过**：无法执行的检查（如非 Git 环境下的 Tag 核对）单独标注，不计入通过，
   也不冒充失败。

---

## 2. 五组门禁

门禁按报告顺序分五组，`--group` 的取值是这些分组的别名（见 §4）。

### 2.1 公共规范

覆盖结构完整性、Markdown 内容、内部引用、core 六段结构、core 映射完整性与重复文件。

- 调用 `common.check_required_structure`、`markdown_validator.validate_markdown`、
  `reference_validator.validate_references`、`consistency_validator.validate_core`、
  `check_core_mapping`、`scan_semantic_conflict_signals`、`common.check_duplicates`。
- 额外校验 `README.md` 的 12 个必需章节。
- `check_core_mapping` 会检查每一份 `core/*.md` 是否至少被一处索引、适配器或规范链接引用，
  防止新增 core 规范成为无人引用的孤儿。

### 2.2 Skills

覆盖 Agent Skills 开放规范的 frontmatter、命名、触发词、目录结构与一级资源引用。

- 调用 `skill_validator.validate_skills`、`validate_global_entry_sources`、
  `consistency_validator.validate_public_skill_sources`。
- 校验结果含已检查的 Skill 数量，便于确认不是空跑。

### 2.3 适配器

覆盖当前注册的全部五种工具（Codex、Claude Code、Cursor、GitHub Copilot、腾讯 WorkBuddy）的适配一致性与工具字段隔离。

- 调用 `adapter_validator.validate_adapters`、`validate_config_code_consistency`、
  `validate_no_tool_leakage`、`validate_standards_reference_core`、
  `consistency_validator.check_generated_freshness`。
- 复用 `targets.check_paths` 静态校验全部安装目标与源文件路径。

### 2.4 安装器

覆盖版本关系、安装计划可生成性与安全模块存在性（不实际安装、不写盘）。

- 调用 `version_validator.validate_versions` 校验版本来源。
- 对 `project` 与 `global` 两种作用域，分别用 `installer.resolver.build_plan`
  为当前注册的五种工具生成计划（project-only 工具在 global 分支按注册表跳过
  用户级产物），并逐项校验目标路径合法、源文件存在。
- 检查 `filesystem.py`、`backup.py`、`manifest.py`、`manager.py` 四个安全模块仍在，
  防止 Phase 5 已落地的事务、备份、归属能力被误删。

### 2.5 版本管理

覆盖 SemVer 合法性与各版本来源的一致性。

- 调用 `version_validator.validate_versions`：核对 `VERSION`、
  `targets.INSTALLER_VERSION` ↔ `config/targets.json.installer_version` 双源、
  README version badge、CHANGELOG 当前版本段。
- 版本规则的权威说明见 [docs/versioning.md](../versioning.md)，本组只做机器校验。

---

## 3. 强制检查与警告分级

### 3.1 分级语义

| 级别 | 含义 | 对退出码的影响 |
| --- | --- | --- |
| ERROR | 必须修复的结构性/一致性问题 | 门禁未通过，退出码 1 |
| WARNING | 建议修复，可能是有意的组织方式 | 默认不影响通过；`--strict` 下按白名单升级 |
| INFO | 检查已执行的事实记录 | 不影响通过 |

日常开发用普通模式即可；PR 合并与发布前必须用 `--strict`，把明确的"建议修复"
提升为"必须修复"。

### 3.2 strict 升级规则（单一来源）

`tooling/validators/quality_rules.py` 的 `STRICT_PROMOTIONS` 是唯一规则表，当前包含：
standards 未引用 `core/`、core 规范未引用 `core/README.md`、core 规范未被任何
索引/适配器/规范引用、Skill 描述过短、Skill 缺少明确触发词、标题层级跳跃、
内容完全相同的重复文件、非标准 Skill 资源目录、使用跨版本未验证字段
（`excludeAgent`）等。命中时把该条 WARNING 升为 ERROR，并附上升级原因。

需要调整分级时，只改这一处，并同步补充对应测试；不要在 `validate.py` 或
`release_check.py` 里另写一份。

---

## 4. 本地执行

在仓库根目录运行：

```bash
# 五组全部门禁（普通模式）
python tooling/scripts/quality_gate.py

# 严格模式：把白名单 WARNING 升为 ERROR（PR / 发布前必跑）
python tooling/scripts/quality_gate.py --strict

# 只跑指定分组，可重复；分组别名为 core/public、skills、adapters、installer、version/versions
python tooling/scripts/quality_gate.py --group skills --group version

# 机器可读输出（供 CI 或其他工具消费）
python tooling/scripts/quality_gate.py --strict --json

# 显式指定仓库根（默认由脚本自身位置解析）
python tooling/scripts/quality_gate.py --repo /path/to/ai-engineering-standards
```

`--strict` 会额外打印本次实际启用的升级规则清单，便于审计"到底加严了哪些项"。

---

## 5. 退出码与机器可读输出

| 退出码 | 含义 |
| --- | --- |
| 0 | 无 ERROR，门禁通过（WARNING 保留，除非已升级） |
| 1 | 存在 ERROR，门禁未通过，须修复 |
| 2 | 门禁工具自身执行失败（如无法定位仓库） |

`--json` 输出包含 `passed`、`errors`、`warnings`、`promoted`、各分组逐条
`issues`，以及版本关系快照，可用于生成检查报告或做门禁卡点的二次判定。

---

## 6. CI 中的位置

质量门禁在两处生效：

- 矩阵 job `validate-and-test`（Windows / Linux / macOS × Python 3.10 / 3.12）
  在逐项跑完 `validate.py --strict`、`check.py --all`、安装器 dry-run 与全量单元测试后，
  再执行一次 `quality_gate.py --strict` 做聚合判定。
- 汇总 job `quality-gate` 依赖矩阵全部通过，再跑一次聚合门禁与
  `release_check.py --strict`，作为 PR 可合并的最终门槛。

workflow 定义见 `../../.github/workflows/ci.yml`。本地命令与 CI 完全等价，
可在提交前自查，避免把可预见的失败推给 CI。

---

## 7. 门禁边界

质量门禁不覆盖以下内容，需按对应文档单独处理：

- **真实 AI 客户端运行时加载**：门禁只校验文件与引用，不启动 Codex / Claude Code /
  Cursor / Copilot，见 [工具适配能力表](../architecture/tool-compatibility.md)。
- **语义正确性**：`scan_semantic_conflict_signals` 只标记人工审查信号，不做语义判定。
- **安装后的目标项目**：本门禁针对规范仓库自身；安装结果检查用 `check.py`，
  见 [安装指南](../installation.md)。
- **发布专项判定**：Tag、CHANGELOG 发版段、归档完整性由
  [release_check.py](../release/release-checklist.md) 在门禁结果之上叠加。

---

## 8. 相关文档

- [跨模块回归测试](regression-testing.md)：如何用变异注入验证门禁确实能发现问题。
- [安装器升级兼容性测试](compatibility-testing.md)：升级路径下用户文件保护与回滚验证。
- [版本与兼容性规则](../versioning.md)：SemVer 判定与兼容性承诺的权威源。
- [发布流程](../release/release-process.md)：门禁通过后如何创建版本并发版。
