<!-- AI-ENGINEERING-STANDARDS:MANAGED version=1.0.0 tool=claude source=adapters/claude-code/CLAUDE.md -->
<!-- 本文件由 ai-engineering-standards 安装器生成。请勿手工编辑；下次 --force 会被覆盖。 -->
<!-- 项目自有规则请写在 CLAUDE.local.md 或 .claude/rules/ 下你自己的文件中。 -->

# AI 工程规范（Claude Code 适配层）

本文件是**薄适配层**：只放必须常驻的红线与索引。完整规范在 `.ai-standards/`，
按需读取，不要把整个规范库一次性载入上下文。

- 规范本体：`.ai-standards/core/`、`.ai-standards/standards/`、`.ai-standards/agents/`
- 可叠加规则：`.claude/rules/ai-engineering-standards.md`（与用户自有规则并存）
- Skills：`.claude/skills/`（Claude Code 官方项目级路径）
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

Claude Code 中可用 `/project-analysis` 等显式调用，也可由 `description`
隐式匹配。技能正文只在被选中时加载，长参考资料按需读取。

## Claude Code 能力边界（已核实 2026-11-11）

- `CLAUDE.md` 是**上下文注入，不是强制配置**；多个文件被拼接而非互相覆盖，
  冲突时 Claude 可能任选其一。需要硬性阻断应使用 `PreToolUse` hook 或 managed settings。
- 启动时加载当前目录及所有父目录的 `CLAUDE.md` / `CLAUDE.local.md`；
  子目录中的文件在被读写该子目录文件时按需加载。
- `.claude/rules/*.md` 递归发现；无 frontmatter 的规则在启动时加载，
  优先级与 `.claude/CLAUDE.md` 相同。`paths` 是规则 frontmatter 中唯一被读取的字段。
- Skills 项目级路径 `.claude/skills/<name>/SKILL.md`；个人级 `~/.claude/skills/`；
  插件级 `<plugin>/skills/`。`description` + `when_to_use` 合并文本在 1,536 字符处截断。
- 上传到 claude.ai / 走 Skills API 时，frontmatter 只允许 6 个标准字段；
  本仓库的 Skills 只使用这 6 个字段，不写 `paths` / `hooks` / `model` 等扩展字段。
- Cowork / cloud sessions **不读取**本机 `~/.claude/skills/`；项目 cloud threads 中
  `.claude/skills/` 也不可用。这不是本仓库能消除的限制。

依据与完整能力差异表：`.ai-standards/docs/tool-adapters.md`。
