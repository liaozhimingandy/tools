"""公共配置表 API（多工具共享，零知识密文同步）。

路由：
  GET    /api/v1/tools                           列出启用工具（注册表）
  GET    /api/v1/tools/{tool_id}                 单个工具元信息
  GET    /api/v1/configs/{tool_id}              列出该工具下当前用户全部配置
  GET    /api/v1/configs/{tool_id}/{key}        取单条（返回 ETag）
  PUT    /api/v1/configs/{tool_id}/{key}        UPSERT（乐观锁 CAS）
  DELETE /api/v1/configs/{tool_id}/{key}        软删除（乐观锁 CAS）
  GET    /api/v1/configs/{tool_id}/_quota       配额使用情况（工具覆盖值优先）
  GET    /api/auth/mode                         当前鉴权模式与风险提示

安全契约（贯穿本文件）：
  1. user_sub 只来自 request.state.principal.sub（鉴权层注入），
     任何 path/query/body 里的用户标识一律忽略。
  2. value 是不透明 blob：本层只做「大小上限」与 JSON 可序列化校验，
     不解析结构、不解密、不记录内容，日志里也不出现 value。
  3. 乐观锁用 expected_revision 做 CAS，防多端同步的丢失更新。
"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response

from . import config
from .auth import AuthProvider, Principal, UnauthorizedError
from .schemas import (
    AuthModeResponse,
    ConfigListResponse,
    ConfigPutRequest,
    ConfigRecordResponse,
    ConflictDetail,
    KEY_PATTERN,
    QuotaResponse,
    TOOL_ID_PATTERN,
    ToolListResponse,
    ToolRecordResponse,
)
from .store import ConflictError, ConfigRepository, NotFoundError
from .tools_registry import ToolRepository

router = APIRouter()

_TOOL_RE = re.compile(TOOL_ID_PATTERN)
_KEY_RE = re.compile(KEY_PATTERN)
_RESERVED_KEYS = {"_quota"}


# --------------------------------------------------------------------------- #
# 依赖：从 app.state 取运行期装配的 provider / repository（便于测试替换）
# --------------------------------------------------------------------------- #


def _state(request: Request) -> Any:
    return request.app.state


def get_principal(request: Request) -> Principal:
    """唯一可信身份入口。鉴权失败 → 401，携带规范错误码。"""
    provider: AuthProvider = _state(request).auth_provider
    headers = {k: v for k, v in request.headers.items()}
    try:
        return provider.authenticate(headers=headers)
    except UnauthorizedError as exc:
        # 用 JSONResponse 直接返回，避免依赖 HTTPException 的默认 HTML/detail 形状
        raise _api_error(401, exc.code, str(exc)) from None


def get_repository(request: Request) -> ConfigRepository:
    return _state(request).repository


def get_tool_repository(request: Request) -> ToolRepository:
    """工具注册表（全局元数据，非用户数据）。"""
    return _state(request).tool_repository


def _api_error(status: int, code: str, message: str, **extra: Any) -> Exception:
    """构造统一错误响应。用 HTTPException 的子类以兼容 FastAPI 异常链。"""
    from fastapi import HTTPException

    detail: dict[str, Any] = {"error": code, "message": message}
    detail.update(extra)
    return HTTPException(status_code=status, detail=detail)


def _validate_ids(
    tool_id: str,
    key: str | None = None,
    registry: ToolRepository | None = None,
) -> None:
    """校验 tool_id/key 形状 + 工具准入。

    工具准入为双重门（AND）：
      1) 注册表：tool_id 必须存在且 enabled（数据源权威）；
      2) 环境变量白名单 TOOLS_TOOL_IDS：若配置，还必须在其中（部署级硬限制）。
    registry 为 None 时跳过注册表门（仅测试兼容用，正常路由都会注入）。
    """
    if not _TOOL_RE.match(tool_id):
        raise _api_error(400, "INVALID_TOOL_ID", "tool_id 形状非法")
    if registry is not None and not registry.exists_enabled(tool_id):
        # 不区分「不存在」与「已禁用」，避免泄露下线工具的存在性
        raise _api_error(404, "TOOL_NOT_FOUND", "工具不存在或未启用")
    allowed = config.allowed_tool_ids()
    if allowed and tool_id not in allowed:
        raise _api_error(404, "TOOL_NOT_FOUND", "工具不存在")
    if key is not None:
        if not _KEY_RE.match(key) or key in _RESERVED_KEYS:
            raise _api_error(400, "INVALID_KEY", "key 形状非法或为保留字")


def _resolve_quota(tool_id: str, registry: ToolRepository | None) -> tuple[int, int]:
    """解析最终配额：工具注册表的非 NULL 覆盖值优先，否则全局 config 默认。"""
    max_keys = config.max_keys_per_user_tool()
    max_bytes = config.max_value_bytes()
    tool = registry.get(tool_id) if registry is not None else None
    if tool is not None:
        if tool.default_max_keys is not None and tool.default_max_keys > 0:
            max_keys = tool.default_max_keys
        if tool.default_max_value_bytes is not None and tool.default_max_value_bytes > 0:
            max_bytes = tool.default_max_value_bytes
    return max_keys, max_bytes


def _validate_value(value: Any) -> str:
    """零知识边界内的最小校验：可 JSON 序列化 + 大小上限。绝不解析业务语义。"""
    try:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        raise _api_error(422, "INVALID_VALUE", "value 必须是可 JSON 序列化的值") from None
    if len(text.encode("utf-8")) > config.max_value_bytes():
        raise _api_error(413, "VALUE_TOO_LARGE", "value 超过大小上限")
    return text


def _to_response(rec: Any) -> ConfigRecordResponse:
    rev = rec.revision
    return ConfigRecordResponse(
        tool_id=rec.tool_id,
        key=rec.key,
        value=rec.value,
        revision=rev,
        schema_version=getattr(rec, "schema_version", 1),
        updated_by_device=getattr(rec, "updated_by_device", None),
        created_at=rec.created_at,
        updated_at=rec.updated_at,
        deleted_at=rec.deleted_at,
        etag=f'W/"{rev}"',
    )


# --------------------------------------------------------------------------- #
# 路由
# --------------------------------------------------------------------------- #


@router.get("/api/auth/mode", response_model=AuthModeResponse, tags=["configs"])
def auth_mode_endpoint(request: Request) -> AuthModeResponse:
    """暴露鉴权模式，便于前端/运维识别 passthrough/dev/stub 的不安全状态。"""
    provider: AuthProvider = _state(request).auth_provider
    secure = provider.mode == "logto" and bool(_state(request).logto_configured)
    warning = None
    if provider.mode == "passthrough":
        warning = (
            "暂时不鉴权：服务端信任客户端声明的 X-User-Sub，任何人可伪造身份读写云端密文；"
            "value 为零知识密文无法被解密，但可被覆盖/删除。正式上线前请切 TOOLS_AUTH_MODE=logto"
        )
    elif provider.mode == "dev":
        warning = "开发鉴权模式：X-User-Sub 头被信任，切勿用于生产"
    elif provider.mode == "stub":
        warning = "测试桩鉴权模式：所有请求共用固定身份"
    elif provider.mode == "logto" and not secure:
        warning = "Logto 未配置完整，所有请求将被拒绝（fail-closed）"
    return AuthModeResponse(
        mode=provider.mode,
        secure=secure,
        logto_configured=bool(_state(request).logto_configured),
        warning=warning,
    )


@router.get("/api/v1/tools", response_model=ToolListResponse, tags=["tools"])
def list_tools(
    principal: Principal = Depends(get_principal),
    registry: ToolRepository = Depends(get_tool_repository),
) -> ToolListResponse:
    """列出启用中的工具（注册表）。需鉴权，但不含任何用户数据。"""
    items = [ToolRecordResponse(**t.to_public()) for t in registry.list(enabled_only=True)]
    return ToolListResponse(items=items, count=len(items))


@router.get("/api/v1/tools/{tool_id}", response_model=ToolRecordResponse, tags=["tools"])
def get_tool(
    tool_id: str,
    principal: Principal = Depends(get_principal),
    registry: ToolRepository = Depends(get_tool_repository),
) -> ToolRecordResponse:
    """单个工具元信息。已禁用工具返回 404（不泄露存在性）。"""
    t = registry.get(tool_id)
    if t is None or not t.enabled:
        raise _api_error(404, "TOOL_NOT_FOUND", "工具不存在或未启用")
    return ToolRecordResponse(**t.to_public())


@router.get("/api/v1/configs/{tool_id}/_quota", response_model=QuotaResponse, tags=["configs"])
def quota(
    tool_id: str,
    principal: Principal = Depends(get_principal),
    repo: ConfigRepository = Depends(get_repository),
    registry: ToolRepository = Depends(get_tool_repository),
) -> QuotaResponse:
    _validate_ids(tool_id, registry=registry)
    rows = repo.list(principal.sub, tool_id)
    max_keys, max_bytes = _resolve_quota(tool_id, registry)
    return QuotaResponse(
        tool_id=tool_id,
        key_count=len(rows),
        max_keys=max_keys,
        max_value_bytes=max_bytes,
    )


@router.get("/api/v1/configs/{tool_id}", response_model=ConfigListResponse, tags=["configs"])
def list_configs(
    tool_id: str,
    include_deleted: bool = False,
    principal: Principal = Depends(get_principal),
    repo: ConfigRepository = Depends(get_repository),
    registry: ToolRepository = Depends(get_tool_repository),
) -> ConfigListResponse:
    _validate_ids(tool_id, registry=registry)
    rows = repo.list(principal.sub, tool_id, include_deleted=include_deleted)
    items = [_to_response(r) for r in rows]
    return ConfigListResponse(tool_id=tool_id, items=items, count=len(items))


@router.get("/api/v1/configs/{tool_id}/{key}", response_model=ConfigRecordResponse, tags=["configs"])
def get_config(
    tool_id: str,
    key: str,
    response: Response,
    principal: Principal = Depends(get_principal),
    repo: ConfigRepository = Depends(get_repository),
    registry: ToolRepository = Depends(get_tool_repository),
) -> ConfigRecordResponse:
    _validate_ids(tool_id, key, registry=registry)
    try:
        rec = repo.get(principal.sub, tool_id, key)
    except NotFoundError:
        raise _api_error(404, "NOT_FOUND", "配置不存在") from None
    resp = _to_response(rec)
    # ETag 走响应头也放一份，供标准 If-Match 客户端使用
    response.headers["ETag"] = resp.etag
    return resp


@router.put("/api/v1/configs/{tool_id}/{key}", response_model=ConfigRecordResponse, tags=["configs"])
def put_config(
    tool_id: str,
    key: str,
    body: ConfigPutRequest,
    response: Response,
    principal: Principal = Depends(get_principal),
    repo: ConfigRepository = Depends(get_repository),
    registry: ToolRepository = Depends(get_tool_repository),
) -> ConfigRecordResponse:
    _validate_ids(tool_id, key, registry=registry)
    _validate_value(body.value)  # 只校验可序列化与大小，不解析语义
    max_keys, max_bytes = _resolve_quota(tool_id, registry)
    # 单条 value 大小也要用工具覆盖后的上限复核（不解析内容，只量字节）
    if len(json.dumps(body.value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) > max_bytes:
        raise _api_error(413, "VALUE_TOO_LARGE", "value 超过该工具的大小上限")

    # 首次创建检查配额
    if body.expected_revision == 0:
        existing_keys = {r.key for r in repo.list(principal.sub, tool_id)}
        if key not in existing_keys and len(existing_keys) >= max_keys:
            raise _api_error(409, "QUOTA_EXCEEDED", "该工具下配置数量已达上限")

    try:
        rec = repo.put(
            principal.sub,
            tool_id,
            key,
            body.value,
            expected_revision=body.expected_revision,
            schema_version=body.schema_version,
            updated_by_device=body.updated_by_device,
        )
    except ConflictError as exc:
        raise _api_error(
            409,
            "REVISION_CONFLICT",
            "版本冲突：资源已被其他端更新",
            detail=ConflictDetail(expected=exc.expected, actual=exc.actual).model_dump(),
        ) from None
    resp = _to_response(rec)
    response.headers["ETag"] = resp.etag
    return resp


@router.delete("/api/v1/configs/{tool_id}/{key}", response_model=ConfigRecordResponse, tags=["configs"])
def delete_config(
    tool_id: str,
    key: str,
    expected_revision: int = Query(..., ge=1, description="乐观锁期望版本（当前 revision）"),
    principal: Principal = Depends(get_principal),
    repo: ConfigRepository = Depends(get_repository),
    registry: ToolRepository = Depends(get_tool_repository),
) -> ConfigRecordResponse:
    _validate_ids(tool_id, key, registry=registry)
    try:
        rec = repo.delete(principal.sub, tool_id, key, expected_revision=expected_revision)
    except ConflictError as exc:
        raise _api_error(
            409,
            "REVISION_CONFLICT",
            "版本冲突：资源已被其他端更新",
            detail=ConflictDetail(expected=exc.expected, actual=exc.actual).model_dump(),
        ) from None
    except NotFoundError:
        raise _api_error(404, "NOT_FOUND", "配置不存在或已删除") from None
    return _to_response(rec)
