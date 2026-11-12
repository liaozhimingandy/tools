-- 应用连接专用角色（最小权限）——RLS 生效的前提，部署必备。
--
-- 为什么需要它：postgres 超级用户带 BYPASSRLS，会无视 001 里的全部 RLS 策略。
-- 应用必须用一个「非特权、非 BYPASSRLS」的角色连接，行级隔离才真正兜底。
-- 应用只能通过 set_config('app.user_sub', <sub>, true) 在事务内声明当前用户，
-- 且只能读写自己 user_sub 的行（见 001 的 POLICY）。
--
-- 用法：psql "$TOOLS_ADMIN_DSN" -f sql/002_app_role.sql
-- 然后把 TOOLS_DATABASE_URL 指向该角色：
--   postgresql://tools_app:<强密码>@<host>:5432/<db>
-- 幂等：可重复执行（只调授权，不改密码；改密码用 ALTER ROLE）。

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tools_app') THEN
    CREATE ROLE tools_app LOGIN PASSWORD 'CHANGE_ME';
    RAISE NOTICE 'role tools_app created with placeholder password — 请立即 ALTER ROLE 设置强密码';
  END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO tools_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON tool_configs TO tools_app;
GRANT USAGE, SELECT ON SEQUENCE tool_configs_id_seq TO tools_app;
-- 工具注册表是全局元数据：应用只需读取启用清单，无写权限；
-- 新增/修改工具由管理员用管理 DSN 执行（或跑 003 迁移的种子）。
GRANT SELECT ON tools TO tools_app;
-- 刻意不授予 TRUNCATE / DROP / 表结构变更权限，也不授予 tools 写权限。
