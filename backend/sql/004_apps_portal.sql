-- Also Apps 统一应用门户：五张表 + RLS + 角色授权（幂等迁移）
--
-- 设计要点：
--   1. portal_apps 是「门户展示目录」，与 OAuth 应用注册信息完全无关；
--      身份认证应用表（如有）不在此脚本内，绝不覆盖。
--   2. id 使用 UUIDv7：PG18+ 内建 uuidv7()；旧版回退 gen_random_uuid()（pgcrypto）。
--      Python 侧仓储同样生成 uuid7，server_default 只是兜底双保险。
--   3. 时间一律 TIMESTAMPTZ（PostgreSQL 内部存 UTC），前端展示转本地时区。
--   4. 用户身份 = Logto sub（TEXT），本库不建 users 表、不存密码、不存重复用户资料。
--   5. 用户私有数据（收藏、最近访问）启用 RLS，应用角色必须 SET LOCAL app.user_sub。
--   6. open_mode/status/visibility/app_type 用 CHECK 枚举，越界值直接被数据库拒绝。
--   7. launch_url 只接受 http/https，CHECK 阻断 javascript:/data:/file: 等危险协议，
--      防开放重定向与 XSS；应用层再做一次更严格校验（双重防线）。
--   8. 删除应用：关联表带 FK ON DELETE CASCADE，不留孤立数据。
--
-- 用法：
--   psql "$TOOLS_ADMIN_DSN" -f sql/004_apps_portal.sql
--   psql "$TOOLS_ADMIN_DSN" -f sql/005_apps_portal_seed.sql   （初始化示例数据，幂等）
-- 回滚：psql "$TOOLS_ADMIN_DSN" -f sql/004_apps_portal_rollback.sql
-- 幂等：004/005 均可重复执行。

-- uuidv7() 在 PG18+ 内建；PG13~17 用 pgcrypto 的 gen_random_uuid() 兜底。
-- 注意：gen_random_uuid() 是 v4，仅作旧版兼容；正式部署建议 PG18+。
DO $$
BEGIN
  IF current_setting('server_version_num')::int < 180000 THEN
    CREATE EXTENSION IF NOT EXISTS pgcrypto;
  END IF;
END
$$;

CREATE OR REPLACE FUNCTION portal_new_id() RETURNS uuid
LANGUAGE plpgsql VOLATILE AS $$
BEGIN
  IF current_setting('server_version_num')::int >= 180000 THEN
    RETURN uuidv7();
  END IF;
  RETURN gen_random_uuid();
END
$$;
COMMENT ON FUNCTION portal_new_id() IS '门户主键默认值：PG18 用 uuidv7，旧版用 gen_random_uuid 兜底';

-- --------------------------------------------------------------------------- -- 分类表
CREATE TABLE IF NOT EXISTS app_categories (
    id           UUID        PRIMARY KEY DEFAULT portal_new_id(),
    code         VARCHAR(64) NOT NULL UNIQUE,
    name         VARCHAR(100) NOT NULL,
    description  TEXT        NOT NULL DEFAULT '',
    icon         VARCHAR(200) NOT NULL DEFAULT '',
    parent_id    UUID,
    sort_order   INTEGER     NOT NULL DEFAULT 0,
    status       VARCHAR(20) NOT NULL DEFAULT 'enabled'
                   CHECK (status IN ('enabled', 'disabled')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_app_categories_parent FOREIGN KEY (parent_id)
        REFERENCES app_categories(id) ON DELETE SET NULL
);
COMMENT ON TABLE app_categories IS '应用分类；支持 parent_id 预留二级分类，本期不实现无限级管理';
CREATE INDEX IF NOT EXISTS ix_app_categories_order ON app_categories (status, sort_order, code);

-- --------------------------------------------------------------------------- -- 应用主表
CREATE TABLE IF NOT EXISTS portal_apps (
    id            UUID         PRIMARY KEY DEFAULT portal_new_id(),
    code          VARCHAR(64)  NOT NULL UNIQUE,
    name          VARCHAR(100) NOT NULL,
    subtitle      VARCHAR(200) NOT NULL DEFAULT '',
    description   TEXT         NOT NULL DEFAULT '',
    detail        TEXT         NOT NULL DEFAULT '',
    icon_url      VARCHAR(500) NOT NULL DEFAULT '',
    cover_url     VARCHAR(500) NOT NULL DEFAULT '',
    launch_url    VARCHAR(1000) NOT NULL DEFAULT '',
    app_type      VARCHAR(32)  NOT NULL DEFAULT 'application'
                     CHECK (app_type IN ('application', 'tool', 'game', 'service')),
    open_mode     VARCHAR(20)  NOT NULL DEFAULT 'new_tab'
                     CHECK (open_mode IN ('same_tab', 'new_tab')),
    status        VARCHAR(20)  NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft', 'published', 'disabled')),
    visibility    VARCHAR(20)  NOT NULL DEFAULT 'public'
                     CHECK (visibility IN ('public', 'private')),
    auth_required BOOLEAN      NOT NULL DEFAULT FALSE,
    is_featured   BOOLEAN      NOT NULL DEFAULT FALSE,
    show_on_home  BOOLEAN      NOT NULL DEFAULT FALSE,
    is_new        BOOLEAN      NOT NULL DEFAULT FALSE,
    sort_order    INTEGER      NOT NULL DEFAULT 0,
    published_at  TIMESTAMPTZ,
    created_by    TEXT,  -- Logto sub；可空，不建 users 表
    updated_by    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_portal_apps_name CHECK (length(btrim(name)) > 0),
    -- launch_url 为空 = 草稿/开发中，允许；非空必须 http(s) 且带主机
    CONSTRAINT ck_portal_apps_launch_url CHECK (
        launch_url = '' OR launch_url ~* '^https?://[^/\s]+(/.*)?$'
    ),
    CONSTRAINT ck_portal_apps_published CHECK (
        status <> 'published' OR published_at IS NOT NULL
    )
);
COMMENT ON TABLE portal_apps IS 'Also Apps 门户应用目录；展示与导航数据唯一来源，不含业务授权';
COMMENT ON COLUMN portal_apps.visibility IS 'public=公开展示；private=仅授权用户可见。展示权限≠业务访问权限';
COMMENT ON COLUMN portal_apps.launch_url IS '仅允许 http/https 绝对地址；空串表示未部署（草稿）';
CREATE INDEX IF NOT EXISTS ix_portal_apps_listing
    ON portal_apps (status, visibility, sort_order, code);
CREATE INDEX IF NOT EXISTS ix_portal_apps_home
    ON portal_apps (show_on_home, is_featured) WHERE status = 'published';
CREATE INDEX IF NOT EXISTS ix_portal_apps_search
    ON portal_apps USING gin ((to_tsvector('simple', code || ' ' || name || ' ' || subtitle)));

-- --------------------------------------------------------------------------- -- 应用-分类关联
CREATE TABLE IF NOT EXISTS application_categories (
    app_id       UUID        NOT NULL REFERENCES portal_apps(id) ON DELETE CASCADE,
    category_id  UUID        NOT NULL REFERENCES app_categories(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (app_id, category_id)
);
COMMENT ON TABLE application_categories IS '应用与分类多对多关联；一个应用可属多个分类';
CREATE INDEX IF NOT EXISTS ix_app_categories_by_cat ON application_categories (category_id, app_id);

-- --------------------------------------------------------------------------- -- 用户收藏
CREATE TABLE IF NOT EXISTS user_app_favorites (
    id          UUID        PRIMARY KEY DEFAULT portal_new_id(),
    user_sub    TEXT        NOT NULL,  -- Logto sub，不建 users 表
    app_id      UUID        NOT NULL REFERENCES portal_apps(id) ON DELETE CASCADE,
    sort_order  INTEGER     NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_app_favorites UNIQUE (user_sub, app_id)
);
COMMENT ON TABLE user_app_favorites IS '用户收藏；user_sub 来自 Logto sub，客户端不可指定';
CREATE INDEX IF NOT EXISTS ix_user_app_favorites_order ON user_app_favorites (user_sub, sort_order, created_at);

-- --------------------------------------------------------------------------- -- 最近访问
CREATE TABLE IF NOT EXISTS user_app_recent_visits (
    id              UUID        PRIMARY KEY DEFAULT portal_new_id(),
    user_sub        TEXT        NOT NULL,
    app_id          UUID        NOT NULL REFERENCES portal_apps(id) ON DELETE CASCADE,
    last_visited_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    visit_count     INTEGER     NOT NULL DEFAULT 1 CHECK (visit_count > 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_app_recent_visits UNIQUE (user_sub, app_id)
);
COMMENT ON TABLE user_app_recent_visits IS '最近访问：每用户每应用一行，重复访问仅累加次数并刷新时间';
CREATE INDEX IF NOT EXISTS ix_user_app_recent_order ON user_app_recent_visits (user_sub, last_visited_at DESC);

-- --------------------------------------------------------------------------- -- RLS：仅用户私有表
ALTER TABLE user_app_favorites     ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_app_favorites     FORCE ROW LEVEL SECURITY;
ALTER TABLE user_app_recent_visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_app_recent_visits FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_user_app_favorites_isolate ON user_app_favorites;
CREATE POLICY p_user_app_favorites_isolate ON user_app_favorites
    USING     (user_sub = current_setting('app.user_sub', true))
    WITH CHECK (user_sub = current_setting('app.user_sub', true));

DROP POLICY IF EXISTS p_user_app_recent_isolate ON user_app_recent_visits;
CREATE POLICY p_user_app_recent_isolate ON user_app_recent_visits
    USING     (user_sub = current_setting('app.user_sub', true))
    WITH CHECK (user_sub = current_setting('app.user_sub', true));

-- 目录表（portal_apps / app_categories / application_categories）刻意不启用 RLS：
-- 全局元数据，匿名只读已发布公开项；管理端走独立管理员权限（非应用角色）。

-- --------------------------------------------------------------------------- -- 角色授权
-- 应用角色沿用 002_app_role.sql 创建的 tools_app（非特权、受 RLS 约束）。
GRANT SELECT ON portal_apps, app_categories, application_categories TO tools_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON user_app_favorites, user_app_recent_visits TO tools_app;

-- --------------------------------------------------------------------------- -- 自动维护 updated_at
CREATE OR REPLACE FUNCTION portal_touch_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS trg_portal_apps_updated ON portal_apps;
CREATE TRIGGER trg_portal_apps_updated BEFORE UPDATE ON portal_apps
    FOR EACH ROW EXECUTE FUNCTION portal_touch_updated_at();
DROP TRIGGER IF EXISTS trg_app_categories_updated ON app_categories;
CREATE TRIGGER trg_app_categories_updated BEFORE UPDATE ON app_categories
    FOR EACH ROW EXECUTE FUNCTION portal_touch_updated_at();
DROP TRIGGER IF EXISTS trg_recent_visits_updated ON user_app_recent_visits;
CREATE TRIGGER trg_recent_visits_updated BEFORE UPDATE ON user_app_recent_visits
    FOR EACH ROW EXECUTE FUNCTION portal_touch_updated_at();
