"""工具注册表存储层（全局元数据，非用户数据）。

与 store.py 的公共配置表分工：
  - tools（本文件）：有哪些工具、显示名/图标/启用态/默认配额。全局共享、不敏感、
    无需 RLS（所有已认证用户可读启用清单）。应用只读，管理走管理员 DSN。
  - tool_configs（store.py）：某用户某工具下的密文配置，RLS 行级隔离。

设计：依赖倒置，与 ConfigRepository 同构。
  - ToolRepository 协议：get / list / exists_enabled。
  - MemoryToolRepository：默认/测试，内置种子（safekeep）。
  - PostgresToolRepository：psycopg3 参数化查询 tools 表。
  - build_repository()：工厂，按 TOOLS_STORE 切换。

配额语义：default_max_keys / default_max_value_bytes 为 None 表示沿用全局
config 默认；非 None 且 > 0 表示该工具的覆盖值。API 层据此解析最终配额。

为什么不做物理外键：tool_configs 可能落在 memory 后端（无 tools 表），且保留软引用
可让「历史 tool_id（已下线工具）」的配置仍可被管理员读取，不强制级联。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolRecord:
    """一条工具注册信息。不含任何用户数据。"""

    tool_id: str
    name: str
    icon: str
    description: str
    enabled: bool
    sort_order: int
    default_max_keys: int | None
    default_max_value_bytes: int | None
    created_at: str
    updated_at: str

    def to_public(self) -> dict[str, Any]:
        """对外形状：工具元信息，可安全下发给已认证前端。"""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "enabled": self.enabled,
            "sort_order": self.sort_order,
            "default_max_keys": self.default_max_keys,
            "default_max_value_bytes": self.default_max_value_bytes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# 种子：锦囊。生产环境应通过管理员 DSN 维护本表，此处仅保证开箱即用与测试可复现。
# 定义必须晚于 ToolRecord（否则 NameError）。
DEFAULT_TOOLS: tuple[ToolRecord, ...] = (
    ToolRecord(
        tool_id="safekeep",
        name="锦囊",
        icon="lock-on",
        description="零知识在线密码保险库",
        enabled=True,
        sort_order=10,
        default_max_keys=None,
        default_max_value_bytes=None,
        created_at="seed",
        updated_at="seed",
    ),
)


class ToolRepository(Protocol):
    """只读工具注册表契约。所有方法都不涉及用户身份。"""

    def get(self, tool_id: str) -> ToolRecord | None:
        """按 id 取工具（含已禁用，便于管理端区分 404 与 410）。"""
        ...

    def list(self, *, enabled_only: bool = True) -> list[ToolRecord]:
        """列出工具，默认只返回启用项，按 sort_order 排序。"""
        ...

    def exists_enabled(self, tool_id: str) -> bool:
        """工具存在且启用——写配置的准入判定。"""
        ...


class MemoryToolRepository:
    """进程内实现：默认与测试用。可用 seed() 注入自定义工具。"""

    def __init__(self, tools: tuple[ToolRecord, ...] | list[ToolRecord] = DEFAULT_TOOLS) -> None:
        self._data: dict[str, ToolRecord] = {t.tool_id: t for t in tools}

    def seed(self, *tools: ToolRecord) -> None:
        """测试/启动期注入或覆盖工具记录。"""
        for t in tools:
            self._data[t.tool_id] = t

    def get(self, tool_id: str) -> ToolRecord | None:
        return self._data.get(tool_id)

    def list(self, *, enabled_only: bool = True) -> list[ToolRecord]:
        rows = [t for t in self._data.values() if (t.enabled or not enabled_only)]
        return sorted(rows, key=lambda t: (t.sort_order, t.tool_id))

    def exists_enabled(self, tool_id: str) -> bool:
        t = self._data.get(tool_id)
        return bool(t and t.enabled)


class PostgresToolRepository:
    """psycopg3 实现：查询 tools 表。延迟导入驱动，保持可选依赖语义。"""

    _COLS = (
        "tool_id, name, icon, description, enabled, sort_order, "
        "default_max_keys, default_max_value_bytes, created_at, updated_at"
    )

    def __init__(self, dsn: str) -> None:
        from psycopg_pool import ConnectionPool  # type: ignore[import-not-found]
        from . import config

        # 与 store.PostgresRepository 同构：PgBouncer(6432) 事务池下禁用自动 prepare。
        self._pool = ConnectionPool(
            dsn,
            min_size=1,
            max_size=config.pg_pool_max_size(4),
            open=True,
            kwargs=config.pg_connect_kwargs(),
        )

    @staticmethod
    def _iso(v: Any) -> str:
        return v.isoformat() if hasattr(v, "isoformat") else str(v)

    def _row(self, row: tuple[Any, ...]) -> ToolRecord:
        (
            tool_id, name, icon, description, enabled, sort_order,
            default_max_keys, default_max_value_bytes, created_at, updated_at,
        ) = row
        return ToolRecord(
            tool_id=tool_id, name=name, icon=icon, description=description,
            enabled=bool(enabled), sort_order=int(sort_order),
            default_max_keys=default_max_keys, default_max_value_bytes=default_max_value_bytes,
            created_at=self._iso(created_at), updated_at=self._iso(updated_at),
        )

    def get(self, tool_id: str) -> ToolRecord | None:
        sql = f"SELECT {self._COLS} FROM tools WHERE tool_id = %s"
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (tool_id,))
                row = cur.fetchone()
        return self._row(row) if row is not None else None

    def list(self, *, enabled_only: bool = True) -> list[ToolRecord]:
        where = "WHERE enabled" if enabled_only else ""
        sql = f"SELECT {self._COLS} FROM tools {where} ORDER BY sort_order, tool_id"
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
        return [self._row(r) for r in rows]

    def exists_enabled(self, tool_id: str) -> bool:
        sql = "SELECT EXISTS (SELECT 1 FROM tools WHERE tool_id = %s AND enabled)"
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (tool_id,))
                row = cur.fetchone()
        return bool(row and row[0])

    def close(self) -> None:
        self._pool.close()


def build_repository(dsn: str | None) -> ToolRepository:
    """工厂：有 postgres DSN 用真实表，否则用内存种子。

    注意：store_backend=postgres 时必须传 DSN；dev/memory 模式传 None 用种子。
    """
    if dsn:
        return PostgresToolRepository(dsn)
    return MemoryToolRepository()
