---
applyTo: "**/*.py, **/*.ts, **/*.js, **/*.vue"
---

<!--
  模板用途：演示"技术栈级规范"如何映射到 Copilot 路径级指令。
  - 这是示例模板，不是安装产物；正式安装的路径级指令用 applyTo: "**"（对所有文件生效）。
  - 官方依据：https://docs.github.com/en/copilot/reference/custom-instructions-support （[A]，查阅 2026-11-11）
  - 路径级指令必须以 .instructions.md 结尾，且 frontmatter 必须含 applyTo（glob）。
  - 本仓库不设置 excludeAgent（其跨 CLI/IDE 行为 UNVERIFIED）。
  - 覆盖提醒：GitHub.com 上路径级指令仅 cloud agent 与 code review 支持；IDE 支持随版本。
  - 不要把下方索引换成规范正文全文；只放索引，正文留只读镜像 .ai-standards/。
-->

# 技术栈规范 · 按需加载

当处理的文件匹配本指令 `applyTo` 时，按语言读取对应技术规范（位于只读镜像 `.ai-standards/`），
不要凭记忆假设框架 API 或项目约定。

## Python

| 场景 | 读取 |
| --- | --- |
| 通用编码 / 命名 | `.ai-standards/standards/languages/python.md` |
| API 设计 | `.ai-standards/standards/backend/api.md` |
| 数据库 | `.ai-standards/standards/backend/database.md` |
| 认证授权 | `.ai-standards/standards/backend/authentication.md` |

## TypeScript / JavaScript / Vue

| 场景 | 读取 |
| --- | --- |
| 语言约定 | `.ai-standards/standards/languages/typescript.md`、`javascript.md` |
| 前端组件 | `.ai-standards/standards/frontend/component.md` |
| UI / 样式 | `.ai-standards/standards/frontend/ui.md` |
| Vue 专属 | `.ai-standards/standards/frontend/vue.md` |

## 红线仍适用

本指令只补充技术栈细则；通用红线以仓库级 `.github/copilot-instructions.md`
及 `.ai-standards/core/ai-behavior.md` 为准，两者不冲突、不互相替代。
