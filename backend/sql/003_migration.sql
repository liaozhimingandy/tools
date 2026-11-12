-- 增量迁移：v0.2 → v0.3（工具注册表 + 两个新列）
-- 供「已用 001 旧版建过表」的库升级；全新库直接用 001 即可，无需本文件。
-- 全部使用 IF NOT EXISTS / ADD COLUMN IF NOT EXISTS，可重复执行。
--
-- 用法：psql "$TOOLS_ADMIN_DSN" -f sql/003_migration.sql
--       （随后用管理员账号调整 tools 种子配额/启用状态；应用角色只有读权限）

-- 1) 工具注册表（若全新库 001 已建则跳过）
CREATE TABLE IF NOT EXISTS tools (
    tool_id                 TEXT        PRIMARY KEY,
    name                    TEXT        NOT NULL,
    icon                    TEXT        NOT NULL DEFAULT '',
    description             TEXT        NOT NULL DEFAULT '',
    enabled                 BOOLEAN     NOT NULL DEFAULT TRUE,
    sort_order              INTEGER     NOT NULL DEFAULT 0,
    default_max_keys        INTEGER,
    default_max_value_bytes INTEGER,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_tools_defaults_nonneg CHECK (
        (default_max_keys IS NULL OR default_max_keys > 0) AND
        (default_max_value_bytes IS NULL OR default_max_value_bytes > 0)
    )
);
CREATE INDEX IF NOT EXISTS ix_tools_enabled_order
    ON tools (sort_order, tool_id) WHERE enabled;
INSERT INTO tools (tool_id, name, icon, description, enabled, sort_order)
VALUES ('safekeep', '锦囊', 'lock-on', '零知识在线密码保险库', TRUE, 10)
ON CONFLICT (tool_id) DO NOTHING;

-- 2) tool_configs 增列（老行回填默认值：schema_version=1，device=NULL）
ALTER TABLE tool_configs
    ADD COLUMN IF NOT EXISTS schema_version INTEGER NOT NULL DEFAULT 1 CHECK (schema_version >= 1);
ALTER TABLE tool_configs
    ADD COLUMN IF NOT EXISTS updated_by_device TEXT;

COMMENT ON COLUMN tool_configs.schema_version IS 'value 内部结构版本（前端演进用），与 revision 并发版本正交';
COMMENT ON COLUMN tool_configs.updated_by_device IS '最近写入设备/客户端标识；明文元数据，非用户密钥，可选';
COMMENT ON TABLE tools IS '工具注册表：全局元数据，不含用户数据；tool_id 校验以此为准';

-- 3) 应用角色只读 tools（若 002 未授予，这里补上，保持迁移自包含）
GRANT SELECT ON tools TO tools_app;
