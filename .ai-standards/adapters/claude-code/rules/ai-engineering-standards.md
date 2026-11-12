<!-- AI-ENGINEERING-STANDARDS:MANAGED version=1.0.0 tool=claude source=adapters/claude-code/rules/ai-engineering-standards.md -->
<!-- 本文件是可叠加规则：与用户自有 CLAUDE.md / .claude/rules/ 文件并存，不覆盖任何用户配置。 -->
<!-- 无 frontmatter：按 Claude Code 官方约定，在启动时加载。 -->

# AI 工程规范 · 常驻检查表

本文件是可叠加通道：当项目已有自己的 `CLAUDE.md` 时，安装器不会覆盖它，
本规则保证通用红线仍然进入上下文。完整规范在 `.ai-standards/`，按需读取。

## 每次动手前的 10 条必查

1. 已实际读取项目结构与相关实现，没有假设文件、接口、字段或依赖。
2. 改动范围已限定；不含无关格式化、重命名、重构或依赖升级。
3. 需要授权的操作（重构 / 换栈 / 新依赖 / 删功能 / 改公共契约）已获得明确授权。
4. 数据库结构变更具备迁移、回滚、旧数据兼容、回填与验证方案。
5. 每个接口在服务端做对象级授权；多租户隔离在数据访问层强制。
6. 输入校验在边界完成；日志与错误信息已脱敏。
7. 正常、边界、异常、回归四类测试已考虑；缺陷修复有「先失败」的用例。
8. 静态检查、类型检查、测试、构建将**实际运行**；结果如实区分三种状态。
9. 不明确或高风险需求已澄清，未靠猜测推进。
10. 汇报将包含修改内容、验证结果、风险与未决项、后续动作。

## 路由

| 任务 | 先读 |
| --- | --- |
| 接手陌生项目 | `.claude/skills/project-analysis/` |
| 需求模糊 | `requirements-analysis` |
| 架构选型 / 边界调整 | `architecture-design` |
| 实施编码 | `software-development` + `.ai-standards/core/ai-behavior.md` |
| 提交前审查 | `code-review` |
| 安全相关 | `.ai-standards/core/security-principles.md` |
| 语言/框架细则 | `.ai-standards/standards/` 对应分组 |

Skills 位于 `.claude/skills/`（Claude Code 官方项目级路径）。
规范版本与文件哈希见 `.ai-standards/manifest.json`。

> 边界说明：`CLAUDE.md` 是上下文注入而非强制配置；冲突规则可能被任选其一。
> 需要硬性阻断时请使用 hook 或 managed settings，不要依赖规则优先级。
