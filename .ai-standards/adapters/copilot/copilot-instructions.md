<!-- AI-ENGINEERING-STANDARDS:MANAGED version=1.0.0 tool=copilot source=adapters/copilot/copilot-instructions.md -->
<!-- 本文件由 ai-engineering-standards 安装器生成。请勿手工编辑；下次 --force 会被覆盖。 -->
<!-- 项目自有规则请写在你自己的 .github/copilot-instructions.md 或路径级 .instructions.md 中。 -->

# AI 工程规范（GitHub Copilot 适配层 · 仓库级）

本文件是**薄适配层**：只放必须常驻的红线与索引。完整规范在 `.ai-standards/`，
按需读取，不要把整个规范库一次性载入上下文。

- 规范本体：`.ai-standards/core/`、`.ai-standards/standards/`、`.ai-standards/agents/`
- 路径级叠加指令：`.github/instructions/ai-engineering-standards.instructions.md`
- Skills：`.github/skills/`（Copilot 官方项目级路径之一）
- 版本：`.ai-standards/VERSION`；文件清单与哈希：`.ai-standards/manifest.json`

## 必须遵守的红线

1. 修改代码前先理解现有项目；不得凭空假设文件、接口、数据库字段或依赖。
2. 未经明确授权，不得大规模重构、更换技术栈/框架、新增第三方依赖、
   删除既有功能、修改公共 API 契约、覆盖用户已有文件。
3. 改动范围以完成需求并通过验收为上限；不顺手做无关格式化、重命名或重构。
4. 数据库结构变更必须同时给出迁移、回滚、旧数据兼容、回填/双写、
   影响评估与验证方式；缺任一项不得实施。
5. 认证与授权分离；每个接口在服务端做对象级授权；多租户隔离在数据访问层强制。
6. 不得伪造测试结果，不得把未验证的代码描述为已完成；
   区分「已验证通过 / 已运行但失败 / 未运行（原因）」。
7. 遇到不明确或高风险需求先澄清，澄清期间只做只读调研。
8. 完成后必须汇报：修改内容、验证结果、风险与未决项、后续动作。
9. 不把 lint / 类型检查 / 构建结果当作测试结果；不跳过检查来让套件变绿。
10. 不写不存在的配置项；不确定工具能力时标注「待验证」。

完整红线见 `.ai-standards/core/ai-behavior.md`；安全细则见
`.ai-standards/core/security-principles.md`。

## 按需加载索引

| 场景 | 读取 |
| --- | --- |
| 通用设计/编码/测试原则 | `.ai-standards/core/engineering-principles.md`、`coding-principles.md`、`testing-principles.md` |
| 架构设计或边界调整 | `.ai-standards/core/architecture-principles.md` |
| 涉及输入输出、权限、密钥 | `.ai-standards/core/security-principles.md` |
| Python / TypeScript / JavaScript | `.ai-standards/standards/languages/` |
| API / 数据库 / 认证 | `.ai-standards/standards/backend/` |
| Vue / 组件 / UI | `.ai-standards/standards/frontend/` |
| Docker / Git / CI | `.ai-standards/standards/devops/` |
| 文档写作 | `.ai-standards/core/documentation-principles.md` |

## Skills（按需触发）

| Skill | 触发 |
| --- | --- |
| `project-analysis` | 接手陌生项目、需要现状调研（只读） |
| `requirements-analysis` | 需求模糊、需要验收标准与待确认清单 |
| `architecture-design` | 新增模块、边界调整、技术选型 |
| `software-development` | 需求明确后实施最小修改 |
| `code-review` | 提交前自检、PR 审查 |

Copilot 由 Agent 按 `description` 自动发现、按需加载技能。

## GitHub Copilot 能力边界（已核实 2026-11-11）

- 仓库级自定义指令位置为 `.github/copilot-instructions.md`，纯 Markdown，
  作用于仓库上下文中的所有请求；本文件即安装到该位置。
- 路径级自定义指令为 `.github/instructions/**/*.instructions.md`，
  **必须**含 `applyTo` frontmatter；本仓库另装一份带 `applyTo: "**"` 的叠加文件。
- **在 GitHub.com 上，路径级指令目前仅由 Copilot cloud agent 与
  Copilot code review 支持**；IDE 支持矩阵随产品与版本而不同
  （VS Code / JetBrains / Xcode / Eclipse / CLI 各不相同）。
  因此本仓库同时提供仓库级与路径级两份，避免单一通道不生效。
- 指令优先级：Personal > Repository > Organization；相关指令会同时提供，
  因此本文件只写不与项目自有规则冲突的通用红线。
- Agent Skills 项目级路径：`.github/skills/`、`.claude/skills/`、`.agents/skills/`；
  个人级 `~/.copilot/skills/`、`~/.agents/skills/`。
- Copilot code review 从 **head branch** 读取指令与 Skills，不是 base branch。
- ⚠️ **待验证**：路径级指令在每一个 IDE 版本中的实际读取行为，
  以及 `excludeAgent` 在 CLI / IDE 中是否被忽略。本仓库不设置 `excludeAgent`。

依据与完整能力差异表：`.ai-standards/docs/tool-adapters.md`。
