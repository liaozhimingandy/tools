"""公共配置表存储层（多工具共享一张表）。

零知识边界（安全契约，务必保持）：
  - value 是「不透明」密文 blob。后端把它当作普通 JSON 值存取，绝不解析内部结构、
    绝不解密、绝不记录明文，也绝不尝试理解 key/value 的业务语义。
  - 用户身份 user_sub 只由鉴权层注入（见 auth.py），存储层只接收它、不产生它。
    API 路由禁止从 body/path/query 读取 user_sub，防越权。

设计：依赖倒置。
  - ConfigRepository：最小存储契约（get/list/put/delete + 乐观锁）。
  - MemoryRepository：进程内实现，默认与测试使用，无外部依赖、无 PG 也能全量验证。
  - PostgresRepository：psycopg3 实现，参数化 SQL + 行级 CAS 乐观锁 + 软删除。
  - get_repository()：工厂，按配置在两者间切换（见 config.py）。

表是「公共」的：所有工具共用 tool_configs 一张表，用 (user_sub, tool_id, key)
三元组逻辑分区，而不是每工具建表。这样新增工具零迁移成本。
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, replace
from typing import Any, Protocol


class ConflictError(Exception):
    """乐观锁冲突：客户端带的 revision 与服务端当前版本不一致。"""

    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"revision conflict: expected {expected}, actual {actual}")


class NotFoundError(Exception):
    """配置记录不存在（或已软删除）。"""


@dataclass(frozen=True)
class ConfigRecord:
    """一条公共配置记录。value 为不透明 JSON 值（通常是密文 blob）。

    版本语义（两个正交概念，勿混）：
      - revision：整行的乐观锁/并发版本，每次写 +1，CAS 用；
      - schema_version：value 内部结构的版本，供前端加密格式演进，后端不解析仅透传。
    updated_by_device：最近写入的设备/客户端标识，明文元数据（非用户密钥），可选。
    """

    user_sub: str
    tool_id: str
    key: str
    value: Any
    revision: int
    created_at: str
    updated_at: str
    deleted_at: str | None = None
    schema_version: int = 1
    updated_by_device: str | None = None

    def to_public(self) -> dict[str, Any]:
        """对外形状：不含内部行 id 与归属 user_sub，含 soft-delete 标记。"""
        return {
            "tool_id": self.tool_id,
            "key": self.key,
            "value": self.value,
            "revision": self.revision,
            "schema_version": self.schema_version,
            "updated_by_device": self.updated_by_device,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deleted_at": self.deleted_at,
        }


class ConfigRepository(Protocol):
    """存储契约。所有方法都以 user_sub 为强制隔离维度。"""

    def get(self, user_sub: str, tool_id: str, key: str) -> ConfigRecord:
        """取单条（不含软删除）；不存在抛 NotFoundError。"""
        ...

    def list(self, user_sub: str, tool_id: str, *, include_deleted: bool = False) -> list[ConfigRecord]:
        """列出某工具下该用户全部配置。"""
        ...

    def put(
        self,
        user_sub: str,
        tool_id: str,
        key: str,
        value: Any,
        *,
        expected_revision: int | None,
        schema_version: int = 1,
        updated_by_device: str | None = None,
    ) -> ConfigRecord:
        """UPSERT。expected_revision=None/0 表示仅首次创建；否则按 revision 做 CAS。
        schema_version 与 updated_by_device 随写透传，后端不解析 value 内部结构。
        """
        ...

    def delete(self, user_sub: str, tool_id: str, key: str, *, expected_revision: int | None) -> ConfigRecord:
        """软删除。同样支持乐观锁。"""
        ...


# --------------------------------------------------------------------------- #
# 内存实现：默认 / 测试用
# --------------------------------------------------------------------------- #


class MemoryRepository:
    """进程内 KV，键为 (user_sub, tool_id, key)。线程安全，便于 TestClient 并发。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: dict[tuple[str, str, str], ConfigRecord] = {}
        self._clock = 0  # 单调递增的逻辑时间戳，保证测试不依赖真实时钟

    def _now(self) -> str:
        self._clock += 1
        return f"t{self._clock}"

    def get(self, user_sub: str, tool_id: str, key: str) -> ConfigRecord:
        with self._lock:
            rec = self._data.get((user_sub, tool_id, key))
            if rec is None or rec.deleted_at is not None:
                raise NotFoundError(f"{tool_id}/{key} not found")
            return rec

    def list(self, user_sub: str, tool_id: str, *, include_deleted: bool = False) -> list[ConfigRecord]:
        with self._lock:
            rows = [
                r
                for (u, t, _), r in self._data.items()
                if u == user_sub and t == tool_id and (include_deleted or r.deleted_at is None)
            ]
        return sorted(rows, key=lambda r: r.key)

    def put(
        self,
        user_sub: str,
        tool_id: str,
        key: str,
        value: Any,
        *,
        expected_revision: int | None,
        schema_version: int = 1,
        updated_by_device: str | None = None,
    ) -> ConfigRecord:
        k = (user_sub, tool_id, key)
        with self._lock:
            old = self._data.get(k)
            current = old.revision if old is not None else 0
            # CAS：客户端必须明确表达对当前版本的认知，防丢失更新
            if expected_revision != current:
                raise ConflictError(expected=expected_revision if expected_revision is not None else -1, actual=current)
            now = self._now()
            if old is None:
                rec = ConfigRecord(
                    user_sub, tool_id, key, value, 1, now, now, None,
                    schema_version, updated_by_device,
                )
            else:
                rec = ConfigRecord(
                    user_sub, tool_id, key, value, old.revision + 1, old.created_at, now, None,
                    schema_version, updated_by_device,
                )
            self._data[k] = rec
            return rec

    def delete(self, user_sub: str, tool_id: str, key: str, *, expected_revision: int | None) -> ConfigRecord:
        k = (user_sub, tool_id, key)
        with self._lock:
            old = self._data.get(k)
            if old is None or old.deleted_at is not None:
                raise NotFoundError(f"{tool_id}/{key} not found")
            if expected_revision != old.revision:
                raise ConflictError(expected=expected_revision if expected_revision is not None else -1, actual=old.revision)
            now = self._now()
            # 软删保留原 value 与元信息，仅打墓碑、+1 revision
            rec = ConfigRecord(
                user_sub, tool_id, key, old.value, old.revision + 1, old.created_at, now, now,
                old.schema_version, old.updated_by_device,
            )
            self._data[k] = rec
            return rec


# --------------------------------------------------------------------------- #
# PostgreSQL 实现：真实落库，运行期按需装配
# --------------------------------------------------------------------------- #


class PostgresRepository:
    """psycopg3 实现。延迟 import，保证无 PG / 未装驱动时应用与测试仍可启动。

    并发安全用「行级 CAS」：UPDATE ... WHERE revision = %s，受影响行数为 0 即冲突，
    不做「先读后写」，从根上避免多端同步的丢失更新。
    """

    def __init__(self, dsn: str, *, table: str = "tool_configs", rls: bool = True) -> None:
        import psycopg  # 延迟导入：可选依赖
        from psycopg_pool import ConnectionPool  # type: ignore[import-not-found]
        from . import config

        self._psycopg = psycopg
        # 表名来自配置常量，非用户输入；仍做一次白名单校验，防配置误写注入
        if not table.replace("_", "").isalnum():
            raise ValueError("illegal table name")
        self._table = table
        self._rls = rls
        # PgBouncer(6432) 事务池模式：关闭自动 prepared statement，否则间歇性
        # 报 `prepared statement "_pg3_x" does not exist`；见 config.pg_connect_kwargs。
        self._pool = ConnectionPool(
            dsn,
            min_size=1,
            max_size=config.pg_pool_max_size(8),
            open=True,
            kwargs=config.pg_connect_kwargs(),
        )

    def _cursor_for(self, conn: Any, user_sub: str) -> Any:
        """开启事务并注入 RLS 所需的 app.user_sub GUC。

        set_config 用参数化传值（不是字符串拼接），sub 里的特殊字符也无注入风险。
        RLS 是纵深防御的第二道闸：即便应用层漏了 WHERE，数据库也只放行本人行。

        ⚠️ 前提：连接 DSN 必须是非特权应用角色（见 sql/002_app_role.sql）。
        postgres 超级用户带 BYPASSRLS，会绕过该策略——集成自检已实测确认。
        """
        cur = conn.cursor()
        if self._rls:
            cur.execute("SELECT set_config('app.user_sub', %s, true)", (user_sub,))
        return cur

    # 统一列顺序：所有 SELECT/RETURNING 都按此清单取值，_row_to_record 对应解析。
    _COLS = "value, schema_version, updated_by_device, revision, created_at, updated_at, deleted_at"

    @staticmethod
    def _iso(v: Any) -> str | None:
        if v is None:
            return None
        return v.isoformat() if hasattr(v, "isoformat") else str(v)

    def _row_to_record(self, row: tuple[Any, ...]) -> ConfigRecord:
        # 列顺序严格对应 _COLS
        value, schema_version, updated_by_device, revision, created_at, updated_at, deleted_at = row
        return ConfigRecord(
            user_sub="",  # 由调用方上下文确定，不回显给用户面
            tool_id="",
            key="",
            value=value,
            revision=int(revision),
            created_at=self._iso(created_at) or "",
            updated_at=self._iso(updated_at) or "",
            deleted_at=self._iso(deleted_at),
            schema_version=int(schema_version),
            updated_by_device=updated_by_device,
        )

    def _fill(self, rec: ConfigRecord, user_sub: str, tool_id: str, key: str) -> ConfigRecord:
        """用调用方上下文补全身份三元组（replace 保留全部字段，避免位置参数漏列）。"""
        return replace(rec, user_sub=user_sub, tool_id=tool_id, key=key)

    def get(self, user_sub: str, tool_id: str, key: str) -> ConfigRecord:
        sql = f"""
            SELECT {self._COLS}
            FROM {self._table}
            WHERE user_sub = %s AND tool_id = %s AND key = %s AND deleted_at IS NULL
        """
        with self._pool.connection() as conn:
            with self._cursor_for(conn, user_sub) as cur:
                cur.execute(sql, (user_sub, tool_id, key))
                row = cur.fetchone()
        if row is None:
            raise NotFoundError(f"{tool_id}/{key} not found")
        return self._fill(self._row_to_record(row), user_sub, tool_id, key)

    def list(self, user_sub: str, tool_id: str, *, include_deleted: bool = False) -> list[ConfigRecord]:
        where = "user_sub = %s AND tool_id = %s"
        if not include_deleted:
            where += " AND deleted_at IS NULL"
        sql = f"""
            SELECT key, {self._COLS}
            FROM {self._table} WHERE {where} ORDER BY key
        """
        with self._pool.connection() as conn:
            with self._cursor_for(conn, user_sub) as cur:
                cur.execute(sql, (user_sub, tool_id))
                rows = cur.fetchall()
        return [
            self._fill(self._row_to_record(row[1:]), user_sub, tool_id, row[0])
            for row in rows
        ]

    def put(
        self,
        user_sub: str,
        tool_id: str,
        key: str,
        value: Any,
        *,
        expected_revision: int | None,
        schema_version: int = 1,
        updated_by_device: str | None = None,
    ) -> ConfigRecord:
        """UPSERT + CAS（与 MemoryRepository 语义一致）：
        - expected_revision in (None, 0) → 仅当记录不存在时创建（防误覆盖）；
        - expected_revision > 0 → 仅当当前 revision 匹配时更新（行级 CAS）。
        两条语句都用 WHERE 约束，受影响 0 行即判定冲突/已存在。
        """
        creating = expected_revision is None or expected_revision == 0
        value_json = json.dumps(value, ensure_ascii=False)
        if creating:
            sql = f"""
                INSERT INTO {self._table}
                    (user_sub, tool_id, key, value, schema_version, updated_by_device, revision, created_at, updated_at)
                VALUES (%s, %s, %s, %s::jsonb, %s, %s, 1, now(), now())
                ON CONFLICT (user_sub, tool_id, key) DO NOTHING
                RETURNING {self._COLS}
            """
            params: tuple[Any, ...] = (
                user_sub, tool_id, key, value_json, schema_version, updated_by_device,
            )
        else:
            sql = f"""
                UPDATE {self._table}
                SET value = %s::jsonb, schema_version = %s, updated_by_device = %s,
                    revision = revision + 1, updated_at = now()
                WHERE user_sub = %s AND tool_id = %s AND key = %s
                  AND revision = %s AND deleted_at IS NULL
                RETURNING {self._COLS}
            """
            params = (
                value_json, schema_version, updated_by_device,
                user_sub, tool_id, key, expected_revision,
            )
        with self._pool.connection() as conn:
            with self._cursor_for(conn, user_sub) as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                if row is None:
                    # 区分「冲突」与「已存在」，给客户端准确信号
                    cur.execute(
                        f"SELECT revision FROM {self._table} WHERE user_sub=%s AND tool_id=%s AND key=%s",
                        (user_sub, tool_id, key),
                    )
                    found = cur.fetchone()
                else:
                    found = None
        if row is not None:
            return self._fill(self._row_to_record(row), user_sub, tool_id, key)
        actual = int(found[0]) if found else 0
        raise ConflictError(expected=expected_revision if expected_revision is not None else 0, actual=actual)

    def delete(self, user_sub: str, tool_id: str, key: str, *, expected_revision: int | None) -> ConfigRecord:
        if expected_revision is None:
            raise ConflictError(expected=-1, actual=-1)  # 删除必须带期望版本
        sql = f"""
            UPDATE {self._table}
            SET deleted_at = now(), revision = revision + 1, updated_at = now()
            WHERE user_sub = %s AND tool_id = %s AND key = %s
              AND revision = %s AND deleted_at IS NULL
            RETURNING {self._COLS}
        """
        with self._pool.connection() as conn:
            with self._cursor_for(conn, user_sub) as cur:
                cur.execute(sql, (user_sub, tool_id, key, expected_revision))
                row = cur.fetchone()
                if row is None:
                    cur.execute(
                        f"SELECT revision FROM {self._table} WHERE user_sub=%s AND tool_id=%s AND key=%s AND deleted_at IS NOT NULL",
                        (user_sub, tool_id, key),
                    )
                    found = cur.fetchone()
        if row is not None:
            return self._fill(self._row_to_record(row), user_sub, tool_id, key)
        actual = int(found[0]) if found else -1
        raise NotFoundError(f"{tool_id}/{key} not found or already deleted (revision={actual})")

    def close(self) -> None:
        """释放连接池。由 lifespan 在关停时调用。"""
        self._pool.close()
