# Also Apps 门户 — API 清单 / 路由 / 权限 / 部署 / 测试

## 1. 后端 API 清单（统一 `/v1` 前缀）

统一响应：成功返回业务 JSON；错误统一 `{error, message, request_id?}`，由 `main.py` 异常处理器摊平。

### 公开目录（匿名可读）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/v1/portal/apps` | 应用列表；`category/keyword/featured/home/page/page_size`，条件保留在 URL |
| GET | `/v1/portal/apps/featured` | 推荐应用 |
| GET | `/v1/portal/apps/search` | 搜索（名称/副标题/简介/编码）；`q` + `category` |
| GET | `/v1/portal/apps/{code}` | 应用详情（含当前用户 `favorited` 状态） |
| GET | `/v1/portal/categories` | 启用的分类列表 |

### 用户功能（需登录，身份只来自 auth provider）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/v1/portal/me/favorites` | 我的收藏 |
| POST | `/v1/portal/me/favorites/{app_id}` | 收藏 |
| DELETE | `/v1/portal/me/favorites/{app_id}` | 取消收藏 |
| PUT | `/v1/portal/me/favorites/order` | 收藏排序 `{app_ids:[]}` |
| GET | `/v1/portal/me/recent?limit=10` | 最近访问（默认 10，上限 100） |
| POST | `/v1/portal/me/recent/{app_id}` | 记录访问（同应用仅一行，visit_count 自增） |
| POST | `/v1/portal/apps/{code}/launch` | 启动前服务端二次校验（见权限流程） |

### 后台管理（管理员白名单强校验）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET / POST | `/v1/portal/admin/apps` | 应用列表（含草稿/私有）/ 新增 |
| GET / PUT / DELETE | `/v1/portal/admin/apps/{id}` | 详情 / 编辑 / 删除（级联清理关联） |
| POST | `/v1/portal/admin/apps/{id}/publish` | 发布 |
| POST | `/v1/portal/admin/apps/{id}/disable` | 下架 |
| GET / POST | `/v1/portal/admin/categories` | 分类列表（含停用）/ 新增 |
| PUT / DELETE | `/v1/portal/admin/categories/{id}` | 编辑 / 删除（解绑应用关联） |
| PUT | `/v1/portal/admin/homepage` | 批量配置首页推荐/展示/排序 |
| GET | `/v1/portal/admin/visits` | 访问统计（不返回 user_sub） |

## 2. 前端路由与页面结构

采用 hash 路由（GitHub Pages 兼容 + Logto 回调落在站点根）：

| 路由 | 页面 | 说明 |
|---|---|---|
| `/#/` | `AppsHomeView` | **Also Apps 首页**：欢迎区/全局搜索/收藏/最近/推荐/分类展示 |
| `/#/apps` | `AppsCenterView` | 应用中心：分类导航/搜索/收藏/最近 Tab，URL 保留 `q/category/view` |
| `/#/apps/:code` | `AppDetailView` | 应用详情：图标/封面/介绍/分类/状态/立即使用/收藏 |
| `/#/admin/apps` | `AdminAppsView` | 管理后台：应用列表/分类管理/首页展示，编辑抽屉含实时预览 |
| `/#/tools-home` | `HomeView` | **原工具集首页**（保留 SafeKeep 入口，不破坏既有功能） |
| `/#/safekeep` | `SafeKeepView` | 原有零知识密码库，未改动 |

组件：`AppCard`（卡片）、`AppLauncher`（Google Apps 风格启动器）、`PortalHeader`（统一顶栏）、`CopyRight`（页脚）。
数据层：`services/portal/api.ts`（请求）、`store.ts`（reactive 单例缓存）、`adminApi.ts`（管理）、`launchIntent.ts`（登录后回跳）、`useAppLaunch.ts`（启动流程）。

**所有展示数据来自 `/v1/portal/*` API，前端零硬编码应用列表——管理员新增应用后无需重新构建前端。**

## 3. 权限校验流程

```
用户点击「立即使用」
   │
   ▼
POST /v1/portal/apps/{code}/launch   ← 服务端二次校验（前端隐藏不算权限控制）
   │
   ├─ 应用不存在 / 非 published ──────────────► 404 APP_NOT_FOUND
   ├─ visibility=private ─────────────────────► 403 APP_FORBIDDEN
   ├─ auth_required 且未登录 ─────────────────► 200 {allowed:false, reason:LOGIN_REQUIRED}
   │                                              前端记 launchIntent → 跳 Logto
   │                                              回调后 resumeAfterLogin 自动续做
   ├─ launch_url 为空（未部署） ───────────────► 200 {allowed:false, reason:NOT_DEPLOYED}
   └─ 全部通过 ──► 记录最近访问 → 按 open_mode 打开
                   ⚠️ 业务权限仍由目标应用后端负责；门户可见 ≠ 有业务权限
```

关键安全约束：

1. **唯一身份来源**：`user_sub` 只由 auth provider 从 Bearer token / 受控头解析；body/path/query 中的用户标识一律忽略（有测试覆盖）。
2. **管理员 fail-closed**：`PORTAL_ADMIN_SUBS` 为空时拒绝所有管理请求，绝不「人人为管理员」。
3. **公开目录过滤**：只返回 `published + public`；私有/草稿应用详情返回 404，不泄露存在性。
4. **URL 安全**：`launch_url` 仅允许 http/https 绝对地址、禁 userinfo、禁控制字符；SQL CHECK + 应用层双重校验，防开放重定向与危险协议。
5. **RLS 兜底**：用户私有表启用行级安全，应用角色用非特权 `tools_app` 连接；即使应用漏写 WHERE 也读不到他人数据。
6. **不重复造轮子**：不建 users 表、不存密码；身份来自 Logto `sub`，展示信息由前端从 id_token 读取。

## 4. 部署配置说明

### 环境变量

后端（`.env` / 容器 env）：

```env
TOOLS_STORE=postgres
TOOLS_DATABASE_URL=postgresql://tools_app:<密码>@<host>:5432/tools
TOOLS_AUTH_MODE=logto                 # 生产必须 logto；passthrough 仅为过渡态
LOGTO_ISSUER=https://account.alsoapp.com/oidc
LOGTO_AUDIENCE=<在 Logto 控制台为门户 API 配置的 resource 标识>
LOGTO_JWKS_URL=https://account.alsoapp.com/oidc/.well-known/jwks.json
PORTAL_ADMIN_SUBS=<管理员 Logto sub,逗号分隔>
TOOLS_CORS_ORIGINS=https://www.alsoapp.com
TOOLS_PUBLIC_PATH=/tools/
```

前端（构建期 VITE_*）：

```env
VITE_API_BASE_URL=https://api-tools.alsoapp.com
VITE_LOGTO_ENDPOINT=https://account.alsoapp.com
VITE_LOGTO_APP_ID=plu65e7c0nypndqg7s4hp
VITE_PUBLIC_PATH=/tools/
```

> Logto appId 是公开客户端标识（PKCE，无 secret），内联默认值非密钥。**需要在 Logto 控制台为 `plu65e7c0nypndqg7s4hp` 配置 redirect_uri 白名单**（站点根 `https://www.alsoapp.com/tools/`）与 API resource/audience。

### 部署步骤

1. 执行数据库迁移：`psql "$TOOLS_ADMIN_DSN" -f backend/sql/004_apps_portal.sql`
2. 执行初始化：`psql "$TOOLS_ADMIN_DSN" -f backend/sql/005_apps_portal_seed.sql`
3. 确认 `tools_app` 角色权限已由 `002_app_role.sql` 授予（004 已追加门户表授权）
4. 构建前端：`cd frontend && npm ci && npm run build`
5. 启动后端：`cd backend && python -m app.main`（FastAPI 托管 dist，SPA 回退）
6. 首次登录管理后台：用 `PORTAL_ADMIN_SUBS` 中的账号登录 Logto，访问 `/tools/#/admin/apps`

⚠️ 未执行 004 迁移时，postgres 模式启动会因缺表报错（fail-closed，符合预期）。

## 5. 后台操作说明

- **新增应用**：管理后台 → 应用列表 → 新增应用 → 填基本信息/展示信息/访问配置/发布设置 → 右侧实时预览卡片 → 保存。保存后为草稿，需点「发布」才对普通用户可见。
- **编辑/删除**：列表操作列；删除会级联清理收藏与访问记录，有二次确认。
- **发布/下架**：操作列按钮，即时生效。
- **排序**：排序列的上下箭头（±1）或首页展示页的 ±10。
- **分类管理**：新增/改名/启停/删除；删除分类只解绑应用关联，不删应用。
- **首页展示管理**：星标切换推荐、开关切换首页展示、±10 调序，保存后前端刷新即生效。

## 6. 测试结果

### 已验证通过（实际运行）

| 检查 | 命令 | 结果 |
|---|---|---|
| 后端全量测试 | `python -m pytest tests/ -q` | **95 passed**（22 新增门户用例 + 73 原有，无回归） |
| 前端类型检查 | `npm run typecheck` | 通过（0 error） |
| 前端测试 | `npm test` | **71 passed**（原有测试无回归） |
| 前端构建 | `npm run build` | 通过，`✓ built in 4.17s` |

测试覆盖验收项：新增/编辑/删除应用、发布下架、首页推荐、分类筛选、关键词搜索、收藏/取消、最近访问、匿名/登录浏览、私有应用拦截、无权限拦截、非法 URL 校验、越权防护（body 指定 user_sub 无效）、管理员白名单 fail-closed、删除级联、UUIDv7 有序性、迁移脚本幂等（SQL `IF NOT EXISTS` 语义 + 重复执行种子不重复插入）。

### 未运行（原因 + 人工验证清单）

| 项 | 原因 | 人工验证命令 / 步骤 |
|---|---|---|
| PostgreSQL 集成 | 本地无可用 DSN / 未执行 004 迁移 | 在有 PG18 的环境执行 004/005 两次确认幂等；用 `tools_app` 角色连接后测试 RLS：`SET ROLE tools_app; SET app.user_sub='a'; SELECT * FROM user_app_favorites;` 只能看到 a 的行 |
| Logto 真实登录 | 需要控制台 redirect_uri / resource 配置 | 在 Logto 控制台配置后，浏览器访问 `/tools/#/`，点登录→回调→应回到门户且头像出现；点需登录应用→应跳登录并自动续做启动 |
| 手机端真机适配 | 无真机环境 | Chrome DevTools 切 iPhone/Android 视口，检查首页/应用中心/启动器/管理页布局无横向溢出 |
| 端到端部署 | 未发布到生产 | 按第 4 节部署后访问 `https://www.alsoapp.com/tools/` 验证 |

## 7. 技术偏差说明（严格遵循工程红线）

任务模板指定 SQLModel/Alembic/Pinia，但**目标工程 `D:/Git/tools` 现有架构**为 psycopg3 原生 SQL + 幂等 SQL 迁移 + 模块级 reactive 状态（无 Pinia）。按工程 `CODEBUDDY.md` 红线「未经授权不新增第三方依赖、不换技术栈、复用现有架构」，本实现沿用工程现有技术：

| 任务要求 | 本实现 | 等价能力 |
|---|---|---|
| SQLModel / SQLAlchemy | dataclass 领域模型 + psycopg3 参数化 SQL | 类型化模型 + 完整 CRUD，依赖倒置双实现 |
| Alembic | `sql/004`+`005`+回滚脚本（`IF NOT EXISTS` 幂等） | 可重复执行的迁移 + 回滚 + 兼容方案 |
| Pinia | 模块级 `reactive` 单例 store | 跨组件共享缓存，零新增依赖 |
| PostgreSQL | ✅ 已支持（PG 仓储实现） | 与内存实现同接口，切 env 即用 |

所有 UUIDv7、UTC 存储/本地展示、统一响应、校验/异常/日志、服务端授权、RLS 均已落实。
