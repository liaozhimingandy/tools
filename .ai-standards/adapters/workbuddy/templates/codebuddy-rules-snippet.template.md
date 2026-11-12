# 模板：WorkBuddy `.codebuddy/rules/` 常驻规则片段

> **用途**：作为 `.codebuddy/rules/ai-engineering-standards.md` 的内容参考——一份**可叠加、无 frontmatter、默认常驻**的项目级规则。
> 它保证即使入口 `CODEBUDDY.md` 被用户自有文件占用，通用红线仍进入上下文。
> **不含归属标记，不是安装产物**；安装器会生成带标记的正式文件，本文仅供维护者参考结构。
> 官方依据：`https://www.workbuddy.cn/docs/cli/memory`（[A]，查阅 2026-11-11）：`.codebuddy/rules/*.md` 递归发现，默认 `alwaysApply: true` 常驻。

---

## 常驻规则（无 frontmatter）

一条常驻规则**不需要任何 frontmatter**，启动时自动注入上下文。以下是正文参考：

<!-- 以下为文件正文参考：开始 -->

# AI 工程规范 · 常驻检查表

本文件是可叠加通道：与用户自有 `CODEBUDDY.md` / `.codebuddy/rules/` 文件并存，不覆盖任何用户配置。
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
| 接手陌生项目 | `.codebuddy/skills/project-analysis/` |
| 需求模糊 | `.codebuddy/skills/requirements-analysis/` |
| 架构选型 / 边界调整 | `.codebuddy/skills/architecture-design/` |
| 实施编码 | `.codebuddy/skills/software-development/` + `.ai-standards/core/ai-behavior.md` |
| 提交前审查 | `.codebuddy/skills/code-review/` |
| 安全相关 | `.ai-standards/core/security-principles.md` |
| 语言 / 框架细则 | `.ai-standards/standards/` 对应分组 |

Skills 位于 `.codebuddy/skills/`（官方项目级路径）；规范版本与文件哈希见 `.ai-standards/manifest.json`。

<!-- 以上为文件正文参考：结束 -->

---

## 条件规则（未来扩展位）

若要让某规则**仅在处理特定文件时**生效，需另建**独立**文件，带 frontmatter：

```markdown
---
alwaysApply: false
paths: "**/*.py"
---

# Python 专项规则

- 类型注解必须完整
- 禁止裸 except
```

> 官方规则类型判定：`alwaysApply: true`（默认）→ 常驻；`alwaysApply: false` + `paths` → 条件触发；`alwaysApply: false` 且无 `paths` → 不加载。

---

## 维护说明（不要复制进规则文件）

1. **常驻规则不加 frontmatter**：默认 `alwaysApply: true`；写 `alwaysApply: false` 会改变加载行为。
2. **不复制规范正文**：这里只有红线摘要与路由；完整正文在 `.ai-standards/`，避免双源。
3. **文件名唯一**：用 `ai-engineering-standards.md` 这类带项目前缀的名字，天然不与用户规则同名。
4. **只做项目级**：放 `.codebuddy/rules/`，不写 `~/.codebuddy/rules/`（用户级全局规则）。
5. **技术栈规则用独立文件**：带 `paths` 的条件规则单独建文件，不污染常驻文件。

---

## 相关文档

- 映射总表：[`../mappings.md`](../mappings.md) · 官方参考：[`../references.md`](../references.md) · 正式产物：[`../rules/ai-engineering-standards.md`](../rules/ai-engineering-standards.md)
