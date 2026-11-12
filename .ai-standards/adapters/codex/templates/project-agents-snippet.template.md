# 模板：项目自有 AGENTS.md 的规范叠加片段

> **用途**：当目标项目根目录**已有自己的 `AGENTS.md`**（用户资产，不可覆盖）时，把下面这段手工追加到自有文件末尾，
> 使 Codex 在不覆盖既有规则的前提下加载本仓库的公共规范与 Skills。
> **这不是安装产物**：不含归属标记，不会被安装器写入；仅作为人工合并的参考片段。
> 官方依据：`https://developers.openai.ac.cn/codex/guides/agents-md`（[B]，查阅 2026-11-11）。

---

<!-- 以下为可复制片段：开始 -->

## AI 工程规范（团队共享，只读）

以下规范由团队统一维护，位于 `.ai-standards/`（**只读镜像，请勿直接编辑**）。
遇到相关任务时按索引读取，不要一次性把全部文档载入上下文。

- 规范本体：`.ai-standards/core/`、`.ai-standards/standards/`、`.ai-standards/agents/`
- 版本与文件清单：`.ai-standards/VERSION`、`.ai-standards/manifest.json`
- Skills：`.agents/skills/`（官方 REPO 作用域，`/skills` 查看，`$name` 显式调用）

### 按需加载索引

| 场景 | 读取 |
| --- | --- |
| 通用设计 / 编码 / 测试原则 | `.ai-standards/core/engineering-principles.md`、`coding-principles.md`、`testing-principles.md` |
| 架构设计或边界调整 | `.ai-standards/core/architecture-principles.md` |
| 输入输出、权限、密钥 | `.ai-standards/core/security-principles.md` |
| 语言 / 后端 / 前端 / DevOps | `.ai-standards/standards/` 对应分组 |
| 完整红线 | `.ai-standards/core/ai-behavior.md` |

### 修改公共规范的入口

需要新增或修改团队规范时，改规范源仓库的 `core/`、`standards/`、`skills/`，
再重新安装同步镜像；不要直接改 `.ai-standards/` 里的副本（会被 `--force` 覆盖）。

<!-- 以上为可复制片段：结束 -->

---

## 使用说明（不要复制进 AGENTS.md）

1. 该片段只放**索引与路径**，不复制任何规范正文，避免与用户自有规则产生两份权威。
2. 路径均指向安装后的 `.ai-standards/` 与 `.agents/skills/`，是目标项目内的相对路径；Codex 按官方约定从项目根发现 `AGENTS.md`，读到此片段后再用自身工具打开索引文件。
3. 若自有 `AGENTS.md` 已存在同名章节，请合并而非重复添加，避免冲突指令。
4. 追加后可用 `codex --ask-for-approval never "Summarize the current instructions."` 验证指令链是否包含本片段（官方验证方法 [B]）。
5. 若希望规范对子目录生效，可在对应子目录放自有 `AGENTS.md` / `AGENTS.override.md` 并同样引用，但**本仓库不主动创建子目录文件**。
