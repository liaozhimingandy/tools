"""真实 PostgreSQL 集成自检（手动运行，不纳入 unittest discover）。

前置：docker run -d --name tools-pg-test -e POSTGRES_PASSWORD=testpass \
        -e POSTGRES_DB=tools_test -p 55432:5432 postgres:16-alpine
      并已执行 sql/001_tool_configs.sql 与 sql/002_app_role.sql
      （后者把密码设为 apppass 便于自检；生产用 CHANGE_ME 后 ALTER ROLE）。

运行：PYTHONPATH=.deps python tests/pg_integration_check.py

覆盖内存实现测不到的真实 SQL 层：行级 CAS、软删除、租户隔离、RLS 兜底、JSONB 原样存取、
schema_version/updated_by_device 新增列往返、tools 注册表的真实查询与软引用准入。

安全要点（本自检实测确认）：RLS 必须用「非特权应用角色」连接才生效。
postgres 超级用户带 BYPASSRLS，即便 FORCE ROW LEVEL SECURITY 也会绕过策略——
因此生产 DSN 必须是专用最小权限角色（见 sql/test_setup_role.sql 的授权清单）。
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.store import ConflictError, NotFoundError, PostgresRepository  # noqa: E402
from app.tools_registry import PostgresToolRepository  # noqa: E402

# 应用连接用非特权的 tools_app 角色，而非 postgres 超级用户（后者 BYPASSRLS）
DSN = os.environ.get(
    "TOOLS_TEST_DSN", "postgresql://tools_app:apppass@127.0.0.1:55432/tools_test"
)
ADMIN_DSN = os.environ.get(
    "TOOLS_TEST_ADMIN_DSN", "postgresql://postgres:testpass@127.0.0.1:55432/tools_test"
)
BLOB = {
    "account": {"salt": "c2FsdA==", "wrapped": {"iv": "aXY=", "ct": "Y3Q="}},
    "items": {"i1": {"iv": "AA==", "ct": "ZW5jcnlwdGVk", "deleted": False}},
    "rev": 1,
}


def check(name: str, cond: bool, detail: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f"  ({detail})" if detail else ""))
    if not cond:
        raise AssertionError(name)


def main() -> None:
    import psycopg

    repo = PostgresRepository(DSN)
    try:
        # 清理测试行（TRUNCATE 需较高权限，用管理员 DSN；日常应用无此权限）
        with psycopg.connect(ADMIN_DSN) as c:
            c.execute("TRUNCATE tool_configs")

        # 1. 首次创建（带 schema_version / updated_by_device）
        r1 = repo.put(
            "alice", "safekeep", "vault", BLOB, expected_revision=0,
            schema_version=5, updated_by_device="pg-test-device",
        )
        check("首次创建 revision=1", r1.revision == 1)
        got = repo.get("alice", "safekeep", "vault")
        check("JSONB 密文 blob 原样往返", got.value == BLOB, "零知识：未解析内部结构")
        check("schema_version 真实落库往返", got.schema_version == 5, f"sv={got.schema_version}")
        check("updated_by_device 真实落库往返", got.updated_by_device == "pg-test-device")

        # 2. 首次创建遇已存在 → 冲突（防误覆盖）
        try:
            repo.put("alice", "safekeep", "vault", {"evil": 1}, expected_revision=0)
            check("重复创建被拒", False)
        except ConflictError as e:
            check("重复创建被拒", e.actual == 1, f"actual={e.actual}")

        # 3. CAS 更新 + 旧版本冲突（同时改 schema_version/device）
        r2 = repo.put(
            "alice", "safekeep", "vault", {**BLOB, "rev": 2}, expected_revision=1,
            schema_version=6, updated_by_device="pg-test-device-2",
        )
        check("CAS 更新 revision=2", r2.revision == 2)
        check("CAS 更新时 schema_version/device 同步落库",
              r2.schema_version == 6 and r2.updated_by_device == "pg-test-device-2")
        try:
            repo.put("alice", "safekeep", "vault", {"stale": 1}, expected_revision=1)
            check("旧版本 CAS 冲突", False)
        except ConflictError as e:
            check("旧版本 CAS 冲突", e.actual == 2)

        # 4. 软删除
        repo.delete("alice", "safekeep", "vault", expected_revision=2)
        try:
            repo.get("alice", "safekeep", "vault")
            check("软删后不可读", False)
        except NotFoundError:
            check("软删后不可读", True)
        check("include_deleted 可见墓碑", len(repo.list("alice", "safekeep", include_deleted=True)) == 1)

        # 5. 租户隔离（应用层 + RLS）
        repo.put("alice", "safekeep", "k", {"who": "alice"}, expected_revision=0)
        repo.put("bob", "safekeep", "k", {"who": "bob"}, expected_revision=0)
        check("alice 只见自己", len(repo.list("alice", "safekeep")) == 1)
        check("alice 值正确", repo.get("alice", "safekeep", "k").value["who"] == "alice")
        check("bob 值正确", repo.get("bob", "safekeep", "k").value["who"] == "bob")

        # 6. RLS 纵深防御：用应用角色、故意不设 GUC，禁止读到任何行
        with psycopg.connect(DSN) as c:
            rows = c.execute("SELECT count(*) FROM tool_configs").fetchone()
        check("RLS 强制：无 GUC 时查询返回 0 行", rows[0] == 0, f"count={rows[0]}")

        # 7. RLS 纵深防御：设成 alice 的 GUC，只能读到 alice 的行
        with psycopg.connect(DSN) as c:
            c.execute("SELECT set_config('app.user_sub', %s, true)", ("alice",))
            rows = c.execute("SELECT count(*) FROM tool_configs").fetchone()
        check("RLS：设 alice GUC 只读到 alice 的行", rows[0] == 2, f"count={rows[0]}")

        # 8. 越权写入兜底：设 alice GUC 却尝试插入 bob 归属的行，应被 RLS WITH CHECK 拒绝
        try:
            with psycopg.connect(DSN) as c:
                c.execute("SELECT set_config('app.user_sub', %s, true)", ("alice",))
                c.execute(
                    "INSERT INTO tool_configs (user_sub, tool_id, key, value) VALUES (%s,%s,%s,%s::jsonb)",
                    ("bob", "safekeep", "evil", "{}"),
                )
            check("RLS 拒绝跨用户写入", False)
        except psycopg.Error as e:
            # psycopg 把 RLS WITH CHECK 违反归到 InsufficientPrivilege/检查类，
            # 关键判据是错误消息含 "row-level security"，而非具体异常子类。
            check("RLS 拒绝跨用户写入", "row-level security" in str(e).lower(), type(e).__name__)

        # 9. 工具注册表：真实查询 + 应用角色只读 + 准入语义
        treg = PostgresToolRepository(DSN)
        try:
            seed = treg.get("safekeep")
            check("tools 种子 safekeep 可读", seed is not None and seed.enabled)
            check("tools 是全局元数据：无 RLS（应用角色可见）", treg.exists_enabled("safekeep"))
            check("未注册工具不准入", not treg.exists_enabled("ghosttool"))
            # 管理员插一个禁用工具，验证 exists_enabled 过滤
            with psycopg.connect(ADMIN_DSN) as c:
                c.execute(
                    "INSERT INTO tools (tool_id, name, enabled) VALUES ('retired_pg','退役',FALSE) "
                    "ON CONFLICT (tool_id) DO UPDATE SET enabled=FALSE"
                )
            check("禁用工具 get 可见", treg.get("retired_pg") is not None)
            check("禁用工具不准入", not treg.exists_enabled("retired_pg"))
            check("list 默认过滤禁用工具", all(t.tool_id != "retired_pg" for t in treg.list()))
            check("list(enabled_only=False) 含禁用工具",
                  any(t.tool_id == "retired_pg" for t in treg.list(enabled_only=False)))
            # 应用角色对 tools 只读：写应被拒（002 未授 INSERT）
            denied = False
            try:
                with psycopg.connect(DSN) as c:
                    c.execute("INSERT INTO tools (tool_id, name) VALUES ('hack','x')")
            except psycopg.Error:
                denied = True
            check("应用角色无 tools 写权限（最小权限）", denied)
        finally:
            treg.close()

        print("\nALL_PG_INTEGRATION_CHECKS_PASSED")
    finally:
        repo.close()


if __name__ == "__main__":
    main()
