# 贡献指南

本仓库自身必须遵守它定义的规范。贡献前请先读
[core/engineering-principles.md](core/engineering-principles.md) 与
[core/documentation-principles.md](core/documentation-principles.md)。

---

## 1. 一条规则只活在一个地方

这是本仓库最重要的维护约定。

- 通用原则 → `core/engineering-principles.md`（或其他 `core/` 文件）
- 某个语言/框架的具体做法 → `standards/<group>/<name>.md`
- 某个工作流的执行步骤 → `skills/<name>/SKILL.md`
- 某个工具的加载方式 → `adapters/<tool>/` 与 `docs/tool-adapters.md`

**禁止**把同一条规则复制进多个文件。需要复用时写相对链接，例如
`[最小必要修改](core/engineering-principles.md#4-最小必要修改)`。
`validate.py` 会检测内容完全相同的重复文件并报警。

---

## 2. 提交前必须跑的检查

```bash
python tooling/scripts/validate.py                    # 必须 0 个 ERROR
python -m unittest discover -s tooling/tests -v       # 全部通过
python tooling/scripts/install.py --all --dry-run     # 计划中不应出现 ERROR
```

若改动了 `install.py`，还必须在临时目录里做一次真实安装并跑 `check.py`：

```bash
python tooling/scripts/install.py --all --target /tmp/aes-sandbox
python tooling/scripts/check.py --target /tmp/aes-sandbox
```

不要在没有执行测试的情况下宣称测试通过。

---

## 3. 各类改动的额外要求

| 改动类型 | 额外要求 |
| --- | --- |
| 新增 / 修改 `core/` 规则 | 说明是否可自动化检查；能检查的必须同时加检查项 |
| 修改 `core/ai-behavior.md`、`core/security-principles.md` | 属高风险变更：列出影响到的 Skills 与适配器，并说明是否需要同步改索引 |
| 新增 `standards/` 文件 | 在 `docs/standards-guide.md` 的清单中登记，并写明触发读取的场景 |
| 新增 / 修改 Skill | 必须跑 `validate.py`；Frontmatter 只用规范 6 字段；正文 < 500 行；见 [docs/skills-guide.md](docs/skills-guide.md) |
| 新增 / 修改适配器 | 必须附官方来源链接与核实日期；无法确认的写「待验证」，见 [docs/tool-adapters.md](docs/tool-adapters.md) |
| 修改安装目标路径 | 只改 `tooling/validators/targets.py`，并补一条安装测试 |
| 修改脚本 | 保持仅用 Python 3.10+ 标准库；新增函数要有对应测试 |

---

## 4. 版本与变更日志

每次对外发布：

1. 按 [docs/versioning.md](docs/versioning.md) 更新 `VERSION`；
2. 在 `CHANGELOG.md` 顶部增加对应版本段落，写清 `新增/变更/修复/移除`；
3. 若存在破坏性变更，必须在 `docs/versioning.md` 中登记迁移步骤；
4. 保证 `README.md` 中 badges 与命令示例仍与实际一致。

---

## 5. 文档写作约定

- 使用简体中文；标题层级不超过 4 级；表格用于并列事实，正文用于解释因果。
- 明确区分**事实**（附官方来源）与**本仓库的设计选择**（说明理由）。
- 不写空泛口号，不写"待补充"占位符，不创建只有标题没有内容的文件。
- 相对链接必须能被 `validate.py` 解析；不允许指向不存在的文件。
- 代码块中的命令必须可直接复制执行，且路径使用 POSIX 风格相对路径。

---

## 6. 明确不接受的改动

- 引入第三方 Python 包、构建系统、Agent 编排框架或运行时服务。
- 把某个工具专有的 frontmatter 字段写进 `skills/` 或 `core/`。
- 在 `install.py` 中增加"自动清理用户文件"或"自动覆盖入口文件"的能力。
- 凭记忆添加官方文档中未确认的配置项或路径。
- 添加没有实际内容的占位文件。
