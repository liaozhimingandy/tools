# 发布前检查清单

> 这份清单是发版人的**操作核对表**，把机器能判定的与必须人工确认的分开。
> 机器部分由 `release_check.py` 执行，人工部分须逐项签字确认后才能推 Tag。
> 流程全貌见 [发布流程](release-process.md)，版本号规则见
> [发布视角的版本管理](versioning.md)。

---

## 1. 检查项状态语义

`release_check.py` 的每个检查项只有四种状态，理解它们是读懂结论的前提：

| 状态 | 含义 | 对发布的影响 |
| --- | --- | --- |
| `[通过]` PASS | 该项已实际执行且通过 | 计入通过 |
| `[失败]` FAIL | 该项已执行但有明确问题 | 阻断发布（退出码 1） |
| `[无法执行]` UNVERIFIABLE | 当前环境无法执行（如非 Git 仓库下核对 Tag） | **不计为通过**，须人工/CI 补验 |
| `[未执行]` SKIPPED | 未要求执行（如未加 `--run-tests`） | 须补跑后才能确认 |

结论分三态：有失败项为"不可发布"；可执行项全过但含无法执行项为
"可执行项全部通过，但存在无法执行项——须补验后方可发布"；全部通过才是"可发布"。
`release_check` 刻意**不把无法执行项伪装成通过**，这是发布诚信的底线。

---

## 2. 机器检查项（自动）

```bash
python tooling/scripts/release_check.py --strict --version X.Y.Z --run-tests
```

该命令会逐项输出并汇总，覆盖：

- **版本专项**：`VERSION` 为合法 SemVer、CHANGELOG 含当前版本段、
  安装器版本双源一致、README badge 与 `VERSION` 一致、`--version` 与 `VERSION` 一致。
- **五组质量门禁**：公共规范结构/Markdown/引用/core 六段、Skills 规范、
  全部工具（现为五种）适配器一致性、安装器版本/清单/计划可生成、版本来源一致
  （严格模式下 WARNING 按白名单升级为 ERROR，规则单一来源）。
- **发布产物完整**：`REQUIRED_FILES` / 目录 / Skills / 适配器源文件齐全
  （`check_release_files`，单一来源清单）。
- **全量自动化测试**：`--run-tests` 真实执行 `unittest discover`，全绿才通过。
- **Git Tag 一致性**：在已打 Tag 的环境核对 Tag ↔ `VERSION`；否则标 `UNVERIFIABLE`。

### 2.1 归档自校验

```bash
python tooling/scripts/build_release_artifact.py --output dist/ai-engineering-standards-X.Y.Z.zip
python tooling/scripts/build_release_artifact.py --check dist/ai-engineering-standards-X.Y.Z.zip --expect-version X.Y.Z
```

确认归档能构建、必需文件齐全、内含版本与期望一致、文件数与 `RELEASE-MANIFEST.json`
自洽。构建与核对共用 `release_file_list` 单一来源清单。

---

## 3. 人工确认项（须逐项核对）

机器无法替你判断以下事项，发布前需人工确认并在发布记录中留痕：

### 3.1 版本与变更说明

- [ ] `VERSION`、`CHANGELOG` 当前版本段、README badge、Tag 四者号一致。
- [ ] CHANGELOG 已列全本次新增/变更/移除/修复/安全项，无遗漏。
- [ ] 若为 MAJOR，已逐条写明破坏性变更与迁移步骤。
- [ ] 被废弃项已遵守"先保留至少一个 MINOR 周期"的约定。

### 3.2 安装与升级安全

- [ ] 用全新临时目录真实装一次，并跑 `check.py` 无 ERROR。
- [ ] 若涉及安装器变更，在临时 home / target 上验证过升级不覆盖用户文件
      （见 [安装器升级兼容性测试](../quality/compatibility-testing.md)）。
- [ ] 确认 manifest schema 未破坏性变更；若变了，已说明对存量用户的影响。

### 3.3 适配器与官方依据

- [ ] 若改动了工具适配器，已按 [工具适配能力表](../architecture/tool-compatibility.md)
      重新核实官方文档并记录核实日期。
- [ ] `UNVERIFIED` / `PARTIAL` 项没有被误写成完全支持。

### 3.4 运行时与平台

- [ ] 在至少一个真实 AI 客户端加载验证 Skills 与入口指令可见。
- [ ] 关注 CI 三平台矩阵（Windows / Linux / macOS × Python 3.10 / 3.12）是否全绿。
- [ ] 本地未覆盖的平台组合与真实客户端行为，登记到验收报告的需人工验证清单。

---

## 4. 推 Tag 前的最终闸门

满足以下全部条件才允许推 Tag（推 Tag 即授权发版）：

1. §2 机器检查全部 `[通过]`，无 `[失败]`、无遗留 `[无法执行]` / `[未执行]`；
2. §3 人工确认项逐项已核对；
3. 发布归档已构建并通过自校验；
4. 确认该版本 Tag 的 Release 尚不存在（workflow 也会再查一次并拒绝覆盖）。

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

---

## 5. 发布后核验

推送后关注 `release.yml` 运行日志，确认：

- 派生版本、发布检查、构建、自校验、拒绝覆盖检查依次通过；
- GitHub Release 已创建，归档 asset 可下载；
- 抽样下载归档，确认能解开、版本文件正确、关键规范与 Skills 齐全。

若 workflow 失败，按失败步骤定位：版本/门禁问题回 §2，归档问题回 §2.1，
权限或重发问题见 [发布流程的失败处理](release-process.md)。修复后**改用新 Tag**
重新发布，不要删除或覆盖已存在的 Release。

---

## 6. 相关文档

- [发布流程](release-process.md)：端到端步骤与 workflow 细节。
- [发布视角的版本管理](versioning.md)：版本事实来源与一致性校验。
- [统一质量门禁](../quality/quality-gates.md)：五组门禁与 strict 分级。
- [跨模块回归测试](../quality/regression-testing.md)：门禁自身的有效性验证。
