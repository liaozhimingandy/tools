<!-- AI-ENGINEERING-STANDARDS:MANAGED version=1.0.0 tool=workbuddy source=adapters/workbuddy/CODEBUDDY.md -->
<!-- 本文件由 ai-engineering-standards 安装器生成。请勿手工编辑；下次 --force 会被覆盖。 -->
<!-- 项目自有指令请写在你自己的 CODEBUDDY.md 段落、CODEBUDDY.local.md，或 .codebuddy/ 下你自己的文件中。 -->

# AI 工程规范（腾讯 WorkBuddy 适配层）

本文件是**薄适配层**：只放必须常驻的红线与索引。完整规范在 `.ai-standards/`，
按需读取，不要一次性把全部文档载入上下文。

- 规范本体：`.ai-standards/core/`、`.ai-standards/standards/`、`.ai-standards/agents/`
- 可叠加规则：`.codebuddy/rules/ai-engineering-standards.md`（与用户自有规则并存）
- Skills：`.codebuddy/skills/`（WorkBuddy 官方项目级发现路径）
- 版本：`.ai-standards/VERSION`；文件清单与哈希：`.ai-standards/manifest.json`

> 定位说明：本文件是**项目级记忆入口**（提供项目上下文与规范索引），
> `.codebuddy/rules/` 是**项目级代码开发规则**（随项目版本控制，仅在本项目工作目录生效）。
> 二者都不是用户级全局规则；本仓库安装时**不写入** `~/.codebuddy/`。

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

WorkBuddy 中可用 `/<skill-name>` 显式调用，或由 `description` 隐式匹配；
技能正文只在被选中时加载，长参考资料按需读取。

## WorkBuddy 能力边界（已核实 2026-11-11）

- 项目级记忆入口可用项目根 `CODEBUDDY.md` 或 `.codebuddy/CODEBUDDY.md`，二者等效；
  与 `AGENTS.md` 兼容，且 `CODEBUDDY.md` 优先加载，从工作目录向上递归查找。
- 项目级规则位于 `.codebuddy/rules/*.md`，所有 `.md` 自动递归加载；
  不带 frontmatter 时默认常驻注入（等价于 `alwaysApply` 取默认值 `true`）。
- 项目级规则**仅**从当前工作目录的 `.codebuddy/rules/` 加载，不加载父目录规则；
  用户级规则在 `~/.codebuddy/rules/`。本仓库只装项目级，不创建用户级全局规则。
- 条件规则需把 `alwaysApply` 设为 `false` 并提供 `paths` glob 才按文件操作触发；
  本仓库的常驻规则刻意不带 frontmatter，避免被降级为条件规则。
- Skills 项目级路径为 `.codebuddy/skills/<name>/SKILL.md`，支持一级
  `references/` / `assets/` / `scripts/`；本仓库 5 个 Skill 逐字节复制。
- Agents 官方支持 `.codebuddy/agents/*.md`（YAML frontmatter + 正文即 system prompt）；
  本仓库按公共角色契约提供映射模板，**不生成**可执行 agent 文件。
- Commands 官方支持 `.codebuddy/commands/*.md`；本仓库 5 个 Skill 已覆盖工作流，
  **不重复生成** Commands。
- ⚠️ **待验证**：桌面端实际读取 `.codebuddy/` 还是 `.workbuddy/`、以及真实客户端
  是否按预期自动发现规则与 Skills，须在真实 WorkBuddy 中用 `/memory` 与 Skills 列表核对。

依据与完整能力差异表：`.ai-standards/docs/tool-adapters.md` 与
`.ai-standards/docs/architecture/tool-compatibility.md`。
