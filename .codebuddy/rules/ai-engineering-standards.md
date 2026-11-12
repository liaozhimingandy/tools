<!-- AI-ENGINEERING-STANDARDS:MANAGED version=1.0.0 tool=workbuddy source=adapters/workbuddy/rules/ai-engineering-standards.md -->
<!-- 本文件是可叠加的项目级规则：与用户自有 CODEBUDDY.md / .codebuddy/rules/ 文件并存，不覆盖任何用户配置。 -->
<!-- 无 frontmatter：按 WorkBuddy 官方约定，项目级规则默认常驻注入（alwaysApply 取默认值 true）。 -->

# AI 工程规范 · 常驻检查表

本文件是可叠加通道：当项目已有自己的 `CODEBUDDY.md` 时，安装器不会覆盖它，
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
| 接手陌生项目 | `.codebuddy/skills/project-analysis/` |
| 需求模糊 | `requirements-analysis` |
| 架构选型 / 边界调整 | `architecture-design` |
| 实施编码 | `software-development` + `.ai-standards/core/ai-behavior.md` |
| 提交前审查 | `code-review` |
| 安全相关 | `.ai-standards/core/security-principles.md` |
| 语言/框架细则 | `.ai-standards/standards/` 对应分组 |

Skills 位于 `.codebuddy/skills/`（WorkBuddy 官方项目级发现路径）。
规范版本与文件哈希见 `.ai-standards/manifest.json`。

> 边界说明：本文件是**项目级代码开发规则**，仅在 `/<工作目录>/.codebuddy/rules/`
> 加载，不写用户级 `~/.codebuddy/rules/`，因此不会成为跨项目生效的全局规则。
> 不带 frontmatter 使其默认常驻；若要拆为按文件触发的条件规则，请另建带
> `alwaysApply` 与 `paths` 字段的**独立**文件，不要改动本常驻文件。
