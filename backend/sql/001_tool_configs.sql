-- 公共配置表 + 工具注册表（多工具共享，全新库一次到位）
-- 设计要点：
--   1. 单表 + (user_sub, tool_id, key) 三元组分区，新增工具零迁移成本。
--   2. value 是 JSONB，但后端把内容当「不透明密文 blob」，不解析、不解密、不索引内部结构。
--      历史教训：绝不对 value 建 GIN 索引或表达式索引去“读”内容，那会破坏零知识边界。
--   3. revision 乐观锁：应用侧用 UPDATE ... WHERE revision = %s 做行级 CAS，防多端丢失更新。
--   4. schema_version 是 value 内部结构的版本（供前端加密格式演进），与 revision（整行并发版本）
--      是两个正交概念，互不干扰。后端不解析 value，仅原样存取该版本号。
--   5. updated_by_device 是最近一次写入的设备/客户端标识（明文元数据，非用户数据）；
--      供多端同步排障。零知识约束只保护 value 内容，设备标识属可选观测字段，前端可填空。
--   6. deleted_at 软删除：保留同步墓碑，避免已删除条目在另一端“复活”。
--   7. RLS 行级安全：即使应用出 bug 忘了带 user_sub，数据库层也兜底隔离租户。
--   8. tools 是「全局元数据」（不含用户数据、不敏感），无需 RLS；与 tool_configs 仅软引用
--      （不建物理外键，保持存储实现解耦、支持 memory/pg 双后端一致语义）。
--   9. 不建 users 表：user_sub 即 Logto 的 sub claim；用户展示信息由前端从 Logto 取，不落库。
--
-- 用法：psql "$TOOLS_ADMIN_DSN" -f sql/001_tool_configs.sql
--       psql "$TOOLS_ADMIN_DSN" -f sql/002_app_role.sql   （创建最小权限应用角色）
-- 已有库升级（缺列缺表）：psql "$TOOLS_ADMIN_DSN" -f sql/003_migration.sql
-- 幂等：本文件与 003 均可重复执行。
--
-- ⚠️ 实测确认的安全要点：RLS 只对「非特权角色」生效。
--    postgres 超级用户带 BYPASSRLS，即便 FORCE ROW LEVEL SECURITY 也会绕过全部策略，
--    无 GUC 时可读到全表。因此应用连接的 DSN 必须是 002_app_role.sql 建的最小权限角色，
--    绝不能用超级用户。集成自检 tests/pg_integration_check.py 覆盖此行为。

-- --------------------------------------------------------------------------- -- 工具注册表（全局元数据，应用只读）
CREATE TABLE IF NOT EXISTS tools (
    tool_id                TEXT        PRIMARY KEY,
    name                   TEXT        NOT NULL,          -- 显示名，如 '锦囊'
    icon                   TEXT        NOT NULL DEFAULT '',-- 图标标识，供前端映射
    description            TEXT        NOT NULL DEFAULT '',
    enabled                BOOLEAN     NOT NULL DEFAULT TRUE,
    sort_order             INTEGER     NOT NULL DEFAULT 0,
    default_max_keys       INTEGER,                       -- NULL = 用全局 config 默认
    default_max_value_bytes INTEGER,                      -- NULL = 用全局 config 默认
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_tools_defaults_nonneg CHECK (
        (default_max_keys IS NULL OR default_max_keys > 0) AND
        (default_max_value_bytes IS NULL OR default_max_value_bytes > 0)
    )
);

COMMENT ON TABLE tools IS '工具注册表：全局元数据，不含用户数据；tool_id 校验以此为准';
COMMENT ON COLUMN tools.default_max_keys IS '该工具单用户 key 配额；NULL 表示沿用 TOOLS_MAX_KEYS';
COMMENT ON COLUMN tools.default_max_value_bytes IS '该工具单条 value 上限；NULL 表示沿用 TOOLS_MAX_VALUE_BYTES';
CREATE INDEX IF NOT EXISTS ix_tools_enabled_order
    ON tools (sort_order, tool_id) WHERE enabled;

-- 种子：锦囊 SafeKeep。启用状态/配额可用 UPDATE 调整，无需改代码。
INSERT INTO tools (tool_id, name, icon, description, enabled, sort_order)
VALUES ('safekeep', '锦囊', 'lock-on', '零知识在线密码保险库', TRUE, 10)
ON CONFLICT (tool_id) DO NOTHING;

-- --------------------------------------------------------------------------- -- 公共配置表（用户数据，RLS 隔离）
CREATE TABLE IF NOT EXISTS tool_configs (
    id                  BIGSERIAL PRIMARY KEY,
    user_sub            TEXT        NOT NULL,          -- Logto sub；唯一可信用户标识，无外键（用户不在本库）
    tool_id             TEXT        NOT NULL,          -- 工具 id，软引用 tools(tool_id)
    key                 TEXT        NOT NULL,          -- 工具内配置键
    value               JSONB       NOT NULL,          -- 不透明密文 blob；后端不解析内容
    schema_version      INTEGER     NOT NULL DEFAULT 1 CHECK (schema_version >= 1),
    updated_by_device   TEXT,                          -- 最近写入设备标识（明文元数据，可选）
    revision            BIGINT      NOT NULL DEFAULT 1 CHECK (revision >= 1),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    CONSTRAINT uq_tool_configs UNIQUE (user_sub, tool_id, key)
);

COMMENT ON TABLE  tool_configs IS '多工具共享的公共配置表；value 为不透明密文，用户身份来自 Logto sub';
COMMENT ON COLUMN tool_configs.value IS '零知识：不透明密文 blob，服务端不解析、不解密、不记录明文';
COMMENT ON COLUMN tool_configs.user_sub IS 'Logto sub claim；本库不建 users 表';
COMMENT ON COLUMN tool_configs.schema_version IS 'value 内部结构版本（前端演进用），与 revision 并发版本正交';
COMMENT ON COLUMN tool_configs.updated_by_device IS '最近写入设备/客户端标识；明文元数据，非用户密钥，可选';
COMMENT ON COLUMN tool_configs.tool_id IS '软引用 tools(tool_id)，不建物理外键以支持 memory/pg 一致语义';

-- 列表查询走 (user_sub, tool_id)；活跃行（未删除）过滤器用得到 deleted_at
CREATE INDEX IF NOT EXISTS ix_tool_configs_scope
    ON tool_configs (user_sub, tool_id)
    WHERE deleted_at IS NULL;

-- --------------------------------------------------------------------------- -- 行级安全（RLS）—— 仅 tool_configs 需要
-- 应用层通过 SET LOCAL app.user_sub = '<sub>' 注入当前用户；RLS 强制所有读写只能碰自己的行。
-- tools 是全局元数据，故意不启用 RLS：所有已认证用户都可读取启用中的工具清单。
ALTER TABLE tool_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_configs FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_tool_configs_isolate ON tool_configs;
CREATE POLICY p_tool_configs_isolate ON tool_configs
    USING     (user_sub = current_setting('app.user_sub', true))
    WITH CHECK (user_sub = current_setting('app.user_sub', true));
