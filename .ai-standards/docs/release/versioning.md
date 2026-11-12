# 发布视角的版本管理

> 本文是**发布操作的版本入口**，只讲"发版时版本号怎么流转、由谁校验"。
> 版本号的判定规则（SemVer 三级表、兼容性承诺、废弃策略）唯一权威源是
> [docs/versioning.md](../versioning.md)，本文不重复定义、不与之矛盾；两者冲突时以权威源为准。

---

## 1. 版本事实来源层级

版本号散落在多个文件里，必须明确谁说了算。事实来源**只上不下**：

| 层级 | 文件 / 常量 | 角色 |
| --- | --- | --- |
| 权威 | `VERSION` | 规范版本唯一事实来源，单行 `MAJOR.MINOR.PATCH` |
| 导出快照 | `tooling/config/targets.json` 的 `installer_version` ↔ `targets.INSTALLER_VERSION` | 安装器版本双源，必须一致 |
| 对外展示 | `README.md` 的 `version-X.Y.Z` badge | 必须与 `VERSION` 一致 |
| 发布记录 | `CHANGELOG.md` 的 `## [X.Y.Z]` 段 | 发版时必须有当前版本段 |
| 分发标记 | Git Tag `vX.Y.Z` | 与 `VERSION` 一致，由 workflow 严格解析 |

规范版本与安装器版本**分线管理**：两者可以不同号，但各自必须合法，且安装器版本
在代码与配置两处必须相等（不一致直接 ERROR）。

---

## 2. 谁在校验一致性

一致性由 `tooling/validators/version_validator.py` 统一采集与核对，
`validate.py`、`quality_gate.py`、`release_check.py` 都复用它，不各写一套：

- `VERSION` 是否为合法 SemVer（并拒绝把 `shields.io` 的 `-blue.svg` 颜色段误当版本号）；
- 安装器版本双源是否一致、是否合法；
- README badge 是否与 `VERSION` 一致；
- CHANGELOG 是否含当前版本段（日常校验给 WARNING，发布前 `--strict` 升为失败）；
- Git Tag 与 `VERSION` 是否一致（无 Git / 无 Tag 时标 `UNVERIFIABLE`，不伪装通过）。

Tag 解析统一走 `version_validator.version_from_tag`，workflow 的 `on.push.tags`
glob 只做粗筛，避免"正则一套、glob 一套"的规则漂移。

---

## 3. 发版时版本号怎么流转

一次发版按以下顺序推进版本号，每一步都有机器校验兜底：

1. **定版本**：按 [版本规则](../versioning.md) 的三级判定表确定 `X.Y.Z`，修改 `VERSION`。
2. **写记录**：在 `CHANGELOG.md` 顶部新增 `## [X.Y.Z]` 已发版段，列出新增/变更/移除
   与迁移步骤。
3. **对齐展示**：更新 `README.md` 的 version badge 为 `version-X.Y.Z`。
4. **对齐安装器**：若安装器有变更，同步 `targets.INSTALLER_VERSION` 与
   `config/targets.json.installer_version`（或明确维持不变）。
5. **跑门禁**：`quality_gate.py --strict` 与 `release_check.py --strict --version X.Y.Z`
   确认全部来源一致、发布产物完整。
6. **打 Tag**：提交后打 `vX.Y.Z` 并推送，触发发布 workflow。

任一来源没对齐，`release_check.py --strict` 就会在对应项标 `[失败]`，不会让
"版本号对不上"的包进入 Release。

---

## 4. 处理不兼容（MAJOR）变更

MAJOR 变更（删除/改写红线规则、重命名 Skill、改变安装路径、改 manifest schema、
提高最低 Python 版本等）不能只改号了事，还需：

- 在 `CHANGELOG.md` 的该版本段写明**破坏性变更清单**与**逐条迁移步骤**；
- 按 [版本规则](../versioning.md) 的废弃策略，被废弃项先保留至少一个 MINOR 周期；
- 若改了 manifest schema，说明对已安装用户的影响与升级方式；
- 发布说明里显式提示用户升级前先读迁移段落，再执行升级。

具体的发布执行步骤（构建归档、创建 GitHub Release、不覆盖已有版本）见
[发布流程](release-process.md)；发版前的逐项核对见
[发布前检查清单](release-checklist.md)。
