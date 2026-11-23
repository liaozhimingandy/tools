-- Also Apps 门户迁移回滚：仅删除本模块新增对象，不触碰 tool_configs / tools 等既有表。
--
-- 用法：psql "$TOOLS_ADMIN_DSN" -f sql/004_apps_portal_rollback.sql
-- 注意：回滚会永久删除门户应用目录与用户收藏/访问记录，执行前请确认已备份。
-- 顺序：先删触发器/策略，再删表（外键依赖由 CASCADE 处理），最后删函数。

DROP TRIGGER IF EXISTS trg_recent_visits_updated ON user_app_recent_visits;
DROP TRIGGER IF EXISTS trg_app_categories_updated ON app_categories;
DROP TRIGGER IF EXISTS trg_portal_apps_updated ON portal_apps;

DROP TABLE IF EXISTS user_app_recent_visits CASCADE;
DROP TABLE IF EXISTS user_app_favorites CASCADE;
DROP TABLE IF EXISTS application_categories CASCADE;
DROP TABLE IF EXISTS portal_apps CASCADE;
DROP TABLE IF EXISTS app_categories CASCADE;

DROP FUNCTION IF EXISTS portal_touch_updated_at();
DROP FUNCTION IF EXISTS portal_new_id();

-- 授权随表删除自动回收；此处无需显式 REVOKE。
