# 模板：Claude Code `.claude/rules/` 叠加规则

> **用途**：作为 `.claude/rules/ai-engineering-standards.md` 的内容参考——一份**可叠加、无 frontmatter**、启动时加载的常驻规则。
> 它保证即使入口 `CLAUDE.md` 被用户自有文件占用，通用红线仍进入上下文。
> **不含归属标记，不是安装产物**；安装器会生成带标记的正式文件，本文仅供维护者参考结构。
> 官方依据：`https://code.claude.com/docs/en/memory`（[A]，查阅 2026-11-11）：`.claude/rules/*.md` 递归发现，无 `paths` 的规则启动时加载。

---

<!-- 以下为文件正文参考：开始 -->

# AI 工程规范 · 常驻检查表

本文件是可叠加通道：与用户自有 `CLAUDE.md` / `.claude/rules/` 文件并存，不覆盖任何用户配置。
完整规范在 `.ai-standards/`，按需读取；本文件只保留每次动手前的必查项与路由。

## 每次动手前的必查

1. 已实际读取项目结构与相关实现，没有假设文件、接口、字段或依赖。
2. 改动范围已限定；不含无关格式化、重命名、重构或依赖升级。
3. 重构 / 换栈 / 新依赖 / 删功能 / 改公共契约 / 覆盖用户文件已获明确授权。
4. 数据库结构变更具备迁移、回滚、旧数据兼容、回填与验证方案。
5. 每个接口在服务端做对象级授权；多租户隔离在数据访问层强制。
6. 输入校验在边界完成；日志与错误信息已脱敏。
7. 正常、边界、异常、回归四类测试已考虑；缺陷修复有「先失败」用例。
8. 静态检查、类型检查、测试、构建将**实际运行**，结果如实区分三种状态。
9. 不明确或高风险需求已澄清，未靠猜测推进。
10. 汇报包含修改内容、验证结果、风险与未决项、后续动作。

## 规范路由（按需读取，不一次载入）

| 任务 | 先读 |
| --- | --- |
| 接手陌生项目 | `.claude/skills/project-analysis/` |
| 需求模糊 | `.claude/skills/requirements-analysis/` |
| 架构选型 / 边界调整 | `.claude/skills/architecture-design/` |
| 实施编码 | `.claude/skills/software-development/` + `.ai-standards/core/ai-behavior.md` |
| 提交前审查 | `.claude/skills/code-review/` |
| 安全相关 | `.ai-standards/core/security-principles.md` |
| 语言 / 框架细则 | `.ai-standards/standards/` 对应分组 |
| 文档写作 | `.ai-standards/core/documentation-principles.md` |

Skills 位于 `.claude/skills/`（官方项目级路径）；规范版本与文件哈希见 `.ai-standards/manifest.json`。

> 边界说明：`CLAUDE.md` 与 `.claude/rules/` 是上下文注入而非强制配置，冲突时 Claude 可能任选其一。
> 需要硬性阻断时使用 hook 或 managed settings，不要依赖规则优先级。

<!-- 以上为文件正文参考：结束 -->

---

## 维护说明（不要复制进规则文件）

1. **不加 frontmatter**：加 `paths` 会把它变成路径触发规则，失去"常驻"效果；其它字段会被官方忽略。
2. **不复制规范正文**：这里只有红线摘要与路由；完整正文在 `.ai-standards/`，避免双源。
3. **文件名唯一**：用 `ai-engineering-standards.md` 这类带项目前缀的名字，天然不与用户规则同名。
4. **技术栈级规则的扩展位**：若要按路径生效（如 Python 规则只用于 `**/*.py`），另建带 `paths: ["**/*.py"]` frontmatter 的**独立**文件，不要污染本常驻文件。
