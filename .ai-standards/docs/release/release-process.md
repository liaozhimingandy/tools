# 发布流程

> 本文描述从"准备发版"到"GitHub Release 生成"的端到端流程。
> 发布治理工具（`release_check.py`、`build_release_artifact.py`）与 GitHub Actions
> 发布 workflow 是流程的执行者；版本号判定规则见
> [发布视角的版本管理](versioning.md) 与权威源
> [docs/versioning.md](../versioning.md)。

---

## 1. 触发模型：推 Tag 即授权

发布流程由**推送符合 `vX.Y.Z` 的 Git Tag** 触发，见
`../../.github/workflows/release.yml`。

- 普通 push 与 PR **不会**发版，它们只走 CI 质量门禁（`../../.github/workflows/ci.yml`）。
- workflow 的 `on.push.tags` glob 为 `v*.*.*`，只做粗筛；严格的 `v<MAJOR.MINOR.PATCH>`
  校验由 `version_validator.version_from_tag` 完成（规则单一来源、已单测）。
- 推 Tag 本身是显式的发布授权动作，因此必须在本地跑完全部检查、确认无误后再打 Tag。

---

## 2. 发布前本地检查

打 Tag 之前，在仓库根目录依次执行：

```bash
# 1. 规范自检 + 一致性检查
python tooling/scripts/validate.py --strict
python tooling/scripts/check.py --all

# 2. 统一质量门禁（五组全过）
python tooling/scripts/quality_gate.py --strict

# 3. 发布前检查（含全量测试；--version 锁定本次发版号）
python tooling/scripts/release_check.py --strict --version X.Y.Z --run-tests

# 4. 真实安装验收（可选但推荐）：用全新临时目录装一次再检查
python tooling/scripts/install.py --all --target /tmp/aes-release-check
python tooling/scripts/check.py --target /tmp/aes-release-check
```

`release_check.py --strict` 会复用质量门禁结果，并叠加版本专项、发布产物完整性、
测试与 Tag 核对，是发版前最重要的单一判定点。逐项含义见
[发布前检查清单](release-checklist.md)。

---

## 3. 版本号与记录对齐

确保以下来源一致（由发布检查自动核对）：

- `VERSION` 为本次要发的合法 SemVer；
- `CHANGELOG.md` 顶部有 `## [X.Y.Z]` 已发版段；
- `README.md` badge 为 `version-X.Y.Z`；
- 安装器版本双源一致；
- 若有不兼容变更，CHANGELOG 已写明迁移步骤。

步骤细节与 MAJOR 变更处理见 [发布视角的版本管理](versioning.md)。

---

## 4. 更新版本并发布

对齐后提交、打 Tag、推送：

```bash
git add -A
git commit -m "chore(release): X.Y.Z"
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z     # 这一下触发发布 workflow
```

> 如果你的仓库默认分支不是 `main`，按实际分支名推送。Tag 一旦推送即视为授权，
> 请确认 §2 的检查全部通过。

---

## 5. workflow 做了什么

`release.yml` 在 `ubuntu-latest` / Python 3.12 上按顺序执行，任一失败即终止、不创建 Release：

### 5.1 从 Tag 派生版本

校验 `GITHUB_REF_NAME` 必须以 `v` 开头，再调用 `version_from_tag` 得到严格版本号，
写入 workflow outputs 供后续步骤复用。非法 Tag 直接失败。

### 5.2 发布前检查

运行 `release_check.py --strict --version <版本> --run-tests`：门禁严格模式 +
CHANGELOG/Tag/版本三者一致 + 全量 unittest 真实执行，全部通过才继续。

### 5.3 构建发布归档

用 `build_release_artifact.py --output dist/ai-engineering-standards-<版本>.zip`
打包。清单来自 `version_validator.release_file_list`（**单一来源**，与发布检查核对的
必需文件一致），归档内额外写入 `RELEASE-MANIFEST.json` 记录版本与文件索引。
打包用标准库 `zipfile`，排除 `__pycache__`、`*.pyc`、`dist`、`.git`、
`.ai-standards` 镜像等。

### 5.4 归档自校验

用 `build_release_artifact.py --check <归档> --expect-version <版本>` 重新校验：
必需文件齐全、归档内版本与 Tag 一致、文件数与索引自洽。

### 5.5 拒绝覆盖已有 Release

在创建前用 `gh release view <Tag>` 检查同名 Release：若已存在则**直接失败**，
不 `--clobber`、不删除用户资产。需要重发时须人工删除旧 Release 或改用新版本号。

### 5.6 创建 Release 并上传

通过后用 `gh release create <Tag> <归档> --title <Tag> --generate-notes`
创建 Release 并附上归档。workflow 仅需 `contents: write` 权限，其余只读。

---

## 6. 权限与安全边界

- workflow 只在 Tag 推送时运行，不监听所有 push，避免误发。
- 只有创建 Release / 上传 asset 需要写权限，且用 runner 预装的 `gh` CLI，
  不引入第三方部署平台或密钥。
- 发布产物清单是单一来源，`release_check` 核对的必需文件与 `build` 打包的文件
  不会各写一份而漂移。
- 不自动覆盖已有 Release，把"是否重发"的决定权留给人工。

---

## 7. 已知限制与人工环节

- `release_check.py` 在非 Git 仓库或尚未打 Tag 时，Tag 一致性项标 `UNVERIFIABLE`
  （无法执行、未计为通过）。只有在已打 Tag 的 CI 环境里才会真正核对 Tag ↔ VERSION。
- 本仓库不宣称已在 GitHub runner 三平台实跑；本地已验证等价命令与归档自校验，
  首次真实发布仍建议人工巡检 workflow 日志。
- 真实 AI 客户端运行时加载、Cursor / Copilot 的 PARTIAL 生效范围等属于工具侧行为，
  不在发布 workflow 覆盖内，见
  [工具适配能力表](../architecture/tool-compatibility.md) 与
  [验收报告的需人工验证清单](../acceptance-report.md)。
