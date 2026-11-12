---
applyTo: "**"
---

<!-- AI-ENGINEERING-STANDARDS:MANAGED version=1.0.0 tool=copilot source=adapters/copilot/instructions.md -->
<!-- 安装目标：.github/instructions/ai-engineering-standards.instructions.md -->
<!-- 本文件是路径级叠加指令，与用户自有 .instructions.md 并存，不覆盖仓库级指令。 -->

# AI 工程规范 · 路径级叠加指令

本文件是 GitHub Copilot 的**路径级**自定义指令，带官方要求的 `applyTo` frontmatter。
它提供可叠加通道：即使项目已有自己的 `.github/copilot-instructions.md`，
本文件也能让通用规范生效。完整规范在 `.ai-standards/`，按需读取。

## 动手前必查（精简红线）

1. 已实际读取项目结构与相关实现，没有假设文件、接口、字段或依赖。
2. 改动范围已限定；不含无关格式化、重命名、重构或依赖升级。
3. 重构 / 换栈 / 新依赖 / 删功能 / 改公共契约 / 覆盖用户文件已获明确授权。
4. 数据库结构变更具备迁移、回滚、旧数据兼容、回填与验证方案。
5. 每个接口在服务端做对象级授权；多租户隔离在数据访问层强制。
6. 输入校验在边界完成；日志与错误信息已脱敏。
7. 正常、边界、异常、回归四类测试已考虑。
8. 静态检查、类型检查、测试、构建将**实际运行**；结果如实区分三种状态。
9. 不明确或高风险需求已澄清，未靠猜测推进。
10. 汇报将包含修改内容、验证结果、风险与未决项、后续动作。

完整红线：`.ai-standards/core/ai-behavior.md`；
安全细则：`.ai-standards/core/security-principles.md`。

## 路由

| 任务 | 先读 / 先用 |
| --- | --- |
| 接手陌生项目 | `.github/skills/project-analysis/` |
| 需求模糊 | `.github/skills/requirements-analysis/` |
| 架构选型 / 边界调整 | `.github/skills/architecture-design/` |
| 实施编码 | `.github/skills/software-development/` |
| 提交前审查 | `.github/skills/code-review/` |
| 语言/框架细则 | `.ai-standards/standards/` 对应分组 |
| 文档写作 | `.ai-standards/core/documentation-principles.md` |

规范版本与文件哈希见 `.ai-standards/manifest.json`。

> **能力边界**：在 GitHub.com 上，路径级自定义指令目前仅由 Copilot cloud agent
> 与 Copilot code review 支持；IDE 支持随产品与版本而不同。
> 本仓库同时提供仓库级 `.github/copilot-instructions.md`，两者不互相替代。
> ⚠️ 待验证：各 IDE 版本对路径级指令的实际读取行为。
