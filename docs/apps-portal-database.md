# Also Apps 门户 — 数据库设计

## 1. ER 关系图

```
                        ┌──────────────────────────┐
                        │   Logto (外部身份服务)    │
                        │   account.alsoapp.com    │
                        │   sub = 统一用户 UUID     │
                        └────────────┬─────────────┘
                                     │ sub (不落库，仅作逻辑外键)
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
┌───────▼─────────┐          ┌───────▼─────────┐          ┌───────▼─────────┐
│ user_app_       │          │ user_app_recent │          │ (未来扩展:标签/  │
│ favorites       │          │ _visits         │          │  国际化/版本)    │
│ (RLS 隔离)      │          │ (RLS 隔离)      │          └─────────────────┘
└───────┬─────────┘          └───────┬─────────┘
        │ app_id                     │ app_id
        │                            │
        └────────────┬───────────────┘
                     │ N:1
             ┌───────▼─────────┐         ┌──────────────────┐
             │  portal_apps    │◄────────┤ application_     │
             │  (应用主表)      │  1:N    │ categories       │
             └─────────────────┘         └────────┬─────────┘
                     ▲                            │ N:1
                     │                            │
                     │                   ┌────────▼─────────┐
                     │                   │ app_categories   │
                     │                   │ (分类表,可自引用) │
                     │                   └──────────────────┘
                     │
        ┌────────────┴────────────┐
        │  tool_configs / tools   │  现有工程表，无关联，互不影响
        │  (原 tools 工程，保留)   │
        └─────────────────────────┘
```

- **实线外键**：数据库层 FK 约束，`portal_apps` 删除时级联清理关联表。
- **虚线逻辑关联**：`user_sub` 指向外部 Logto 用户，本库不建 `users` 表、不存密码、不缓存用户资料。
- **RLS**：仅两张用户私有表启用；目录表为全局元数据不启用。

## 2. 表结构说明

### 2.1 `portal_apps`（应用主表）

| 字段 | 类型 | 约束 / 说明 |
|---|---|---|
| `id` | UUID | PK，默认 `portal_new_id()`（PG18 → uuidv7，旧版 gen_random_uuid 兜底） |
| `code` | VARCHAR(64) | UNIQUE，全局应用编码 |
| `name` | VARCHAR(100) | NOT NULL，非空校验 |
| `subtitle` | VARCHAR(200) | 副标题 |
| `description` / `detail` | TEXT | 简介 / 详细介绍 |
| `icon_url` / `cover_url` | VARCHAR(500) | 图标 / 封面 |
| `launch_url` | VARCHAR(1000) | CHECK：空串（草稿）或 `^https?://[^/\s]+...$`，禁 userinfo |
| `app_type` | VARCHAR(32) | CHECK ∈ `application/tool/game/service` |
| `open_mode` | VARCHAR(20) | CHECK ∈ `same_tab/new_tab` |
| `status` | VARCHAR(20) | CHECK ∈ `draft/published/disabled` |
| `visibility` | VARCHAR(20) | CHECK ∈ `public/private`；展示范围 ≠ 业务授权 |
| `auth_required` | BOOLEAN | 是否要求登录 |
| `is_featured` / `show_on_home` / `is_new` | BOOLEAN | 推荐 / 首页展示 / 新品标识 |
| `sort_order` | INTEGER | 排序权重，越小越靠前 |
| `published_at` | TIMESTAMPTZ | 发布时刻；status≠published 时为 NULL |
| `created_by` / `updated_by` | TEXT | 审计用 Logto sub，可空 |
| `created_at` / `updated_at` | TIMESTAMPTZ | UTC；updated_at 由触发器维护 |

索引：`(status, visibility, sort_order, code)`、`(show_on_home, is_featured) WHERE status='published'`、全文 GIN（code/name/subtitle）。

### 2.2 `app_categories`（分类表）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` / `code` / `name` | UUID / VARCHAR(64) UNIQUE / VARCHAR(100) | 主键、唯一编码、名称 |
| `description` / `icon` | TEXT / VARCHAR(200) | 描述、图标标识 |
| `parent_id` | UUID | 自引用 FK，`ON DELETE SET NULL`；预留二级分类 |
| `sort_order` / `status` | INTEGER / VARCHAR(20) | 排序、启停（enabled/disabled） |
| `created_at` / `updated_at` | TIMESTAMPTZ | UTC |

初始 8 类：全部应用、AI 工具、效率工具、内容创作、游戏娱乐、金融投资、社交社区、其他服务。

### 2.3 `application_categories`（多对多关联）

PK = `(app_id, category_id)` 复合主键；两个 FK 均 `ON DELETE CASCADE`；`created_at` UTC。一个应用可属多个分类。

### 2.4 `user_app_favorites`（收藏，RLS）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | UUID | UUIDv7 |
| `user_sub` | TEXT | Logto sub；不建 users 表 |
| `app_id` | UUID | FK → portal_apps ON DELETE CASCADE |
| `sort_order` | INTEGER | 用户自定义收藏顺序 |
| `created_at` | TIMESTAMPTZ | UTC |

UNIQUE `(user_sub, app_id)`；RLS 策略 `user_sub = current_setting('app.user_sub', true)`。

### 2.5 `user_app_recent_visits`（最近访问，RLS）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` / `user_sub` / `app_id` | UUID / TEXT / UUID | 同上 |
| `last_visited_at` | TIMESTAMPTZ | 最近访问时刻 |
| `visit_count` | INTEGER | ≥1，重复访问自增 |
| `created_at` / `updated_at` | TIMESTAMPTZ | UTC |

UNIQUE `(user_sub, app_id)`；按 `last_visited_at DESC` 排序，API 默认只取 10 条，上限 100，不无限增长。

## 3. 迁移与回滚

| 脚本 | 作用 | 幂等 |
|---|---|---|
| `backend/sql/004_apps_portal.sql` | 建 5 表 + CHECK/唯一约束 + 索引 + RLS + 角色授权 + updated_at 触发器 | ✅ `IF NOT EXISTS` / `DO $$` |
| `backend/sql/004_apps_portal_rollback.sql` | 删触发器/策略/表/函数（不影响既有 tools 表） | ✅ `IF EXISTS` / `CASCADE` |
| `backend/sql/005_apps_portal_seed.sql` | 8 分类 + 7 示例应用 + 分类关联 | ✅ `ON CONFLICT DO NOTHING/UPDATE` |

- **旧数据兼容**：新表独立创建，不修改任何既有表结构；既有 `tools` / `tool_configs` 不受影响。
- **回填/双写**：无旧数据需回填（门户是新增模块）。
- **验证方式**：重复执行 004/005 不报错；`SELECT count(*)` 在重复执行后保持不变；RLS 自检见下。
- **安全前置**：应用连接必须使用 `002_app_role.sql` 创建的**非特权** `tools_app` 角色；postgres 超级用户带 BYPASSRLS 会绕过 RLS。

## 4. 初始化数据说明

7 个示例应用按任务清单落库。仅 **Also Account** 使用已确认的真实地址 `https://account.alsoapp.com/` 并标为 published；其余 6 个保持 `draft` + 空 `launch_url`，**不编造访问地址**，由管理员上线后在后台补齐。种子脚本重复执行只更新描述类字段，不覆盖管理员后续修改的 status / visibility / sort_order / launch_url。
