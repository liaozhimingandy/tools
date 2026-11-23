"""PostgreSQL 门户仓储实现（psycopg3，依赖倒置的可选实现）。

与 store.PostgresRepository / tools_registry.PostgresToolRepository 同构：
  - 延迟导入 psycopg_pool，Optional 依赖缺席时内存实现照常工作；
  - 参数化 SQL，禁止字符串拼接用户输入；
  - 用户态读写在事务内 set_config('app.user_sub', sub, true)，RLS 兜底隔离；
  - 目录表无 RLS；管理写入由 API 层管理员权限控制。
"""

from __future__ import annotations

from typing import Any, Iterable

from .portal_ids import iso_utc, utcnow
from .portal_models import (
    AppRecord,
    CategoryRecord,
    ConflictError,
    FavoriteRecord,
    NotFoundError,
    RecentVisitRecord,
    ValidationError,
    with_updated,
)
from .portal_store import validate_launch_url

_APP_COLS = (
    "id, code, name, subtitle, description, detail, icon_url, cover_url, launch_url, "
    "app_type, open_mode, status, visibility, auth_required, is_featured, show_on_home, "
    "is_new, sort_order, published_at, created_by, updated_by, created_at, updated_at"
)

_CAT_COLS = (
    "id, code, name, description, icon, parent_id, sort_order, status, created_at, updated_at"
)


def _iso(v: Any) -> str | None:
    if v is None:
        return None
    return v.isoformat().replace("+00:00", "Z") if hasattr(v, "isoformat") else str(v)


class PostgresPortalRepository:
    """psycopg3 实现：门户五张表。"""

    def __init__(self, dsn: str) -> None:
        from psycopg_pool import ConnectionPool  # type: ignore[import-not-found]
        from . import config

        self._pool = ConnectionPool(
            dsn,
            min_size=1,
            max_size=config.pg_pool_max_size(4),
            open=True,
            kwargs=config.pg_connect_kwargs(),
        )

    def close(self) -> None:
        self._pool.close()

    # ------------------------------------------------------------------ 内部辅助
    def _rows(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())

    def _row(self, sql: str, params: tuple[Any, ...] = ()) -> tuple[Any, ...] | None:
        rows = self._rows(sql, params)
        return rows[0] if rows else None

    def _exec(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)

    def _user_rows(self, user_sub: str, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        """用户态查询：同一事务内声明 user_sub，RLS 强制隔离。"""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.user_sub', %s, true)", (user_sub,))
                cur.execute(sql, params)
                return list(cur.fetchall())

    def _user_exec(self, user_sub: str, sql: str, params: tuple[Any, ...] = ()) -> None:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.user_sub', %s, true)", (user_sub,))
                cur.execute(sql, params)

    def _categories_of(self, app_code: str) -> tuple[str, ...]:
        rows = self._rows(
            "SELECT c.code FROM application_categories ac "
            "JOIN app_categories c ON c.id = ac.category_id "
            "JOIN portal_apps a ON a.id = ac.app_id WHERE a.code = %s ORDER BY c.sort_order",
            (app_code,),
        )
        return tuple(str(r[0]) for r in rows)

    def _app_from_row(self, row: tuple[Any, ...]) -> AppRecord:
        (
            rid, code, name, subtitle, description, detail, icon_url, cover_url, launch_url,
            app_type, open_mode, status, visibility, auth_required, is_featured, show_on_home,
            is_new, sort_order, published_at, created_by, updated_by, created_at, updated_at,
        ) = row
        return AppRecord(
            id=str(rid), code=str(code), name=str(name), subtitle=str(subtitle or ""),
            description=str(description or ""), detail=str(detail or ""),
            icon_url=str(icon_url or ""), cover_url=str(cover_url or ""),
            launch_url=str(launch_url or ""), app_type=app_type, open_mode=open_mode,
            status=status, visibility=visibility, auth_required=bool(auth_required),
            is_featured=bool(is_featured), show_on_home=bool(show_on_home),
            is_new=bool(is_new), sort_order=int(sort_order), published_at=_iso(published_at),
            created_by=created_by, updated_by=updated_by,
            created_at=_iso(created_at) or "", updated_at=_iso(updated_at) or "",
            categories=self._categories_of(str(code)),
        )

    def _category_from_row(self, row: tuple[Any, ...]) -> CategoryRecord:
        rid, code, name, description, icon, parent_id, sort_order, status, created_at, updated_at = row
        return CategoryRecord(
            id=str(rid), code=str(code), name=str(name), description=str(description or ""),
            icon=str(icon or ""), parent_id=str(parent_id) if parent_id else None,
            sort_order=int(sort_order), status=status,
            created_at=_iso(created_at) or "", updated_at=_iso(updated_at) or "",
        )

    # ------------------------------------------------------------------ 目录
    def _app_filters(
        self,
        *,
        status: str | None,
        category: str | None,
        keyword: str,
        featured_only: bool,
        home_only: bool,
        include_private: bool,
    ) -> tuple[str, list[Any]]:
        where: list[str] = ["1=1"]
        params: list[Any] = []
        if status:
            where.append("a.status = %s")
            params.append(status)
        if not include_private:
            where.append("a.visibility = 'public'")
        if featured_only:
            where.append("a.is_featured")
        if home_only:
            where.append("a.show_on_home")
        if category and category != "all":
            where.append(
                "EXISTS (SELECT 1 FROM application_categories ac "
                "JOIN app_categories c ON c.id = ac.category_id "
                "WHERE ac.app_id = a.id AND c.code = %s)"
            )
            params.append(category)
        if keyword:
            where.append("(a.name ILIKE %s OR a.subtitle ILIKE %s OR a.code ILIKE %s OR a.description ILIKE %s)")
            like = f"%{keyword.strip()}%"
            params.extend([like, like, like, like])
        return " AND ".join(where), params

    def list_apps(self, **kwargs: Any) -> list[AppRecord]:
        clause, params = self._app_filters(
            status=kwargs.get("status"),
            category=kwargs.get("category"),
            keyword=str(kwargs.get("keyword", "")),
            featured_only=bool(kwargs.get("featured_only", False)),
            home_only=bool(kwargs.get("home_only", False)),
            include_private=bool(kwargs.get("include_private", False)),
        )
        sql = f"SELECT {_APP_COLS} FROM portal_apps a WHERE {clause} ORDER BY a.sort_order, a.code"
        limit = kwargs.get("limit")
        if limit is not None:
            sql += " LIMIT %s OFFSET %s"
            params.extend([int(limit), int(kwargs.get("offset", 0))])
        return [self._app_from_row(r) for r in self._rows(sql, tuple(params))]

    def count_apps(self, **kwargs: Any) -> int:
        clause, params = self._app_filters(
            status=kwargs.get("status"),
            category=kwargs.get("category"),
            keyword=str(kwargs.get("keyword", "")),
            featured_only=bool(kwargs.get("featured_only", False)),
            home_only=bool(kwargs.get("home_only", False)),
            include_private=bool(kwargs.get("include_private", False)),
        )
        row = self._row(f"SELECT count(*) FROM portal_apps a WHERE {clause}", tuple(params))
        return int(row[0]) if row else 0

    def get_app_by_code(self, code: str) -> AppRecord | None:
        row = self._row(f"SELECT {_APP_COLS} FROM portal_apps WHERE code = %s", (code.upper(),))
        return self._app_from_row(row) if row else None

    def get_app_by_id(self, app_id: str) -> AppRecord | None:
        row = self._row(f"SELECT {_APP_COLS} FROM portal_apps WHERE id = %s::uuid", (app_id,))
        return self._app_from_row(row) if row else None

    def create_app(self, app: AppRecord, category_codes: tuple[str, ...] = ()) -> AppRecord:
        if app.code.upper() in {a.code for a in self.list_apps(include_private=True, status=None)}:
            raise ValidationError("应用编码已存在")
        launch = validate_launch_url(app.launch_url)
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO portal_apps "
                    "(code, name, subtitle, description, detail, icon_url, cover_url, launch_url, "
                    "app_type, open_mode, status, visibility, auth_required, is_featured, "
                    "show_on_home, is_new, sort_order, published_at, created_by, updated_by) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    (
                        app.code.upper(), app.name, app.subtitle, app.description, app.detail,
                        app.icon_url, app.cover_url, launch, app.app_type, app.open_mode,
                        app.status, app.visibility, app.auth_required, app.is_featured,
                        app.show_on_home, app.is_new, app.sort_order, app.published_at,
                        app.created_by, app.updated_by,
                    ),
                )
                rid = str(cur.fetchone()[0])
                self._set_categories(cur, rid, category_codes)
        return self.get_app_by_id(rid)  # type: ignore[return-value]

    def _set_categories(self, cur: Any, app_id: str, codes: Iterable[str]) -> None:
        cur.execute("DELETE FROM application_categories WHERE app_id = %s::uuid", (app_id,))
        for code in dict.fromkeys(codes):
            cur.execute("SELECT id FROM app_categories WHERE code = %s", (code,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "INSERT INTO application_categories (app_id, category_id) VALUES (%s::uuid, %s)",
                    (app_id, row[0]),
                )

    def update_app(self, app_id: str, **changes: Any) -> AppRecord:
        existing = self.get_app_by_id(app_id)
        if not existing:
            raise NotFoundError("应用不存在")
        if "launch_url" in changes:
            changes["launch_url"] = validate_launch_url(str(changes["launch_url"]))
        allowed = {
            "name", "subtitle", "description", "detail", "icon_url", "cover_url", "launch_url",
            "app_type", "open_mode", "status", "visibility", "auth_required", "is_featured",
            "show_on_home", "is_new", "sort_order", "updated_by",
        }
        sets, params = [], []
        for key, value in changes.items():
            if key in allowed:
                sets.append(f"{key} = %s")
                params.append(value)
        if "status" in changes:
            if changes["status"] == "published":
                sets.append("published_at = COALESCE(published_at, now())")
            else:
                sets.append("published_at = NULL")
        if not sets:
            return existing
        sets.append("updated_at = now()")
        params.append(app_id)
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE portal_apps SET {', '.join(sets)} WHERE id = %s::uuid", tuple(params)
                )
        return self.get_app_by_id(app_id)  # type: ignore[return-value]

    def delete_app(self, app_id: str) -> None:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM portal_apps WHERE id = %s::uuid", (app_id,))
                if cur.rowcount == 0:
                    raise NotFoundError("应用不存在")

    def set_app_categories(self, app_id: str, category_codes: tuple[str, ...]) -> AppRecord:
        if not self.get_app_by_id(app_id):
            raise NotFoundError("应用不存在")
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                self._set_categories(cur, app_id, category_codes)
        return self.get_app_by_id(app_id)  # type: ignore[return-value]

    # ------------------------------------------------------------------ 分类
    def list_categories(self, *, enabled_only: bool = True) -> list[CategoryRecord]:
        where = "WHERE status = 'enabled'" if enabled_only else ""
        return [
            self._category_from_row(r)
            for r in self._rows(f"SELECT {_CAT_COLS} FROM app_categories {where} ORDER BY sort_order, code")
        ]

    def get_category_by_code(self, code: str) -> CategoryRecord | None:
        row = self._row(f"SELECT {_CAT_COLS} FROM app_categories WHERE code = %s", (code,))
        return self._category_from_row(row) if row else None

    def get_category_by_id(self, category_id: str) -> CategoryRecord | None:
        row = self._row(f"SELECT {_CAT_COLS} FROM app_categories WHERE id = %s::uuid", (category_id,))
        return self._category_from_row(row) if row else None

    def create_category(self, category: CategoryRecord) -> CategoryRecord:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO app_categories (code, name, description, icon, parent_id, sort_order, status) "
                    "VALUES (%s,%s,%s,%s,%s::uuid,%s,%s) RETURNING id",
                    (
                        category.code, category.name, category.description, category.icon,
                        category.parent_id, category.sort_order, category.status,
                    ),
                )
                return self.get_category_by_id(str(cur.fetchone()[0]))  # type: ignore[return-value]

    def update_category(self, category_id: str, **changes: Any) -> CategoryRecord:
        if not self.get_category_by_id(category_id):
            raise NotFoundError("分类不存在")
        allowed = {"name", "description", "icon", "parent_id", "sort_order", "status"}
        sets, params = [], []
        for key, value in changes.items():
            if key in allowed:
                sets.append(f"{key} = %s")
                params.append(value)
        if not sets:
            return self.get_category_by_id(category_id)  # type: ignore[return-value]
        sets.append("updated_at = now()")
        params.append(category_id)
        self._exec(
            f"UPDATE app_categories SET {', '.join(sets)} WHERE id = %s::uuid", tuple(params)
        )
        return self.get_category_by_id(category_id)  # type: ignore[return-value]

    def delete_category(self, category_id: str) -> None:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM app_categories WHERE id = %s::uuid", (category_id,))
                if cur.rowcount == 0:
                    raise NotFoundError("分类不存在")

    # ------------------------------------------------------------------ 收藏
    def list_favorites(self, user_sub: str) -> list[FavoriteRecord]:
        rows = self._user_rows(
            user_sub,
            "SELECT id, app_id, sort_order, created_at FROM user_app_favorites "
            "WHERE user_sub = %s ORDER BY sort_order, created_at",
            (user_sub,),
        )
        return [
            FavoriteRecord(
                id=str(r[0]), user_sub=user_sub, app_id=str(r[1]),
                sort_order=int(r[2]), created_at=_iso(r[3]) or "",
            )
            for r in rows
        ]

    def add_favorite(self, user_sub: str, app_id: str, sort_order: int = 0) -> FavoriteRecord:
        existing = next((f for f in self.list_favorites(user_sub) if f.app_id == app_id), None)
        if existing:
            raise ConflictError("已收藏该应用")
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT set_config('app.user_sub', %s, true)", (user_sub,)
                )
                cur.execute(
                    "INSERT INTO user_app_favorites (user_sub, app_id, sort_order) "
                    "VALUES (%s, %s::uuid, %s) RETURNING id, created_at",
                    (user_sub, app_id, sort_order),
                )
                row = cur.fetchone()
        return FavoriteRecord(
            id=str(row[0]), user_sub=user_sub, app_id=app_id,
            sort_order=sort_order, created_at=_iso(row[1]) or "",
        )

    def remove_favorite(self, user_sub: str, app_id: str) -> None:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.user_sub', %s, true)", (user_sub,))
                cur.execute(
                    "DELETE FROM user_app_favorites WHERE user_sub = %s AND app_id = %s::uuid",
                    (user_sub, app_id),
                )
                if cur.rowcount == 0:
                    raise NotFoundError("收藏记录不存在")

    def reorder_favorites(self, user_sub: str, app_ids: list[str]) -> list[FavoriteRecord]:
        order = {aid: i for i, aid in enumerate(app_ids)}
        for aid, idx in order.items():
            self._user_exec(
                user_sub,
                "UPDATE user_app_favorites SET sort_order = %s WHERE user_sub = %s AND app_id = %s::uuid",
                (idx, user_sub, aid),
            )
        return self.list_favorites(user_sub)

    # ------------------------------------------------------------------ 最近访问
    def list_recent(self, user_sub: str, limit: int = 10) -> list[RecentVisitRecord]:
        rows = self._user_rows(
            user_sub,
            "SELECT id, app_id, last_visited_at, visit_count, created_at, updated_at "
            "FROM user_app_recent_visits WHERE user_sub = %s "
            "ORDER BY last_visited_at DESC LIMIT %s",
            (user_sub, max(1, min(int(limit), 100))),
        )
        return [
            RecentVisitRecord(
                id=str(r[0]), user_sub=user_sub, app_id=str(r[1]),
                last_visited_at=_iso(r[2]) or "", visit_count=int(r[3]),
                created_at=_iso(r[4]) or "", updated_at=_iso(r[5]) or "",
            )
            for r in rows
        ]

    def record_visit(self, user_sub: str, app_id: str) -> RecentVisitRecord:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.user_sub', %s, true)", (user_sub,))
                cur.execute(
                    "INSERT INTO user_app_recent_visits (user_sub, app_id, last_visited_at, visit_count) "
                    "VALUES (%s, %s::uuid, now(), 1) "
                    "ON CONFLICT (user_sub, app_id) DO UPDATE SET "
                    "visit_count = user_app_recent_visits.visit_count + 1, "
                    "last_visited_at = now(), updated_at = now() "
                    "RETURNING id, last_visited_at, visit_count, created_at, updated_at",
                    (user_sub, app_id),
                )
                row = cur.fetchone()
        return RecentVisitRecord(
            id=str(row[0]), user_sub=user_sub, app_id=app_id,
            last_visited_at=_iso(row[1]) or "", visit_count=int(row[2]),
            created_at=_iso(row[3]) or "", updated_at=_iso(row[4]) or "",
        )
