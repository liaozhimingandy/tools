<!-- AI-ENGINEERING-STANDARDS:MANAGED version=1.0.0 tool=codex source=adapters/codex/AGENTS.md -->
<!-- 本文件由 ai-engineering-standards 安装器生成。请勿手工编辑；下次 --force 会被覆盖。 -->
<!-- 项目自有规则请写在你自己的 AGENTS.md 段落或子目录 AGENTS.md 中。 -->

# AI 工程规范（Codex 适配层）

本文件是**薄适配层**：只放必须常驻的红线与索引。完整规范在 `.ai-standards/`，
按需读取，不要一次性把全部文档载入上下文。

- 规范本体：`.ai-standards/core/`、`.ai-standards/standards/`、`.ai-standards/agents/`
- Skills：`.agents/skills/`（Codex 官方 REPO 作用域）
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

Codex 中可用 `/skills` 查看，或输入 `$project-analysis` 显式调用；
也可由 `description` 隐式匹配。技能正文只在被选中时加载。

## Codex 能力边界（已核实 2026-11-11）

- 本文件按官方 AGENTS.md 约定放在项目根；Codex 从项目根向下遍历到当前工作目录，
  每层取一个文件，越靠近工作目录优先级越高；全局文件在 `~/.codex/AGENTS.md`。
- `AGENTS.override.md` 会覆盖同层 `AGENTS.md`；`CODEX_HOME` 可改变全局目录。
- Skills 官方项目级路径为 `.agents/skills/`；用户级为 `$HOME/.agents/skills/`；
  管理员级为 `/etc/codex/skills`。
- Codex 的初始技能列表有上下文预算，会优先缩短 `description`，
  因此描述把关键触发词前置。
- ⚠️ **待验证**：Codex 是否读取 `.codex/skills/` 兼容路径、
  以及 `name`/`description` 的单独长度上限。本仓库只依赖官方明确给出的路径。

依据与完整能力差异表：`.ai-standards/docs/tool-adapters.md`
（安装器会把 docs 一并放入 `.ai-standards/docs/`）。
