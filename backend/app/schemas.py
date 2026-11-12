"""API 契约 schema（Pydantic）。

契约优先：请求/响应形状在此固化，供接口与契约测试共同引用。
错误响应保持统一形状，不含堆栈、内部路径或敏感信息。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ServiceStatus(str, Enum):
    """服务健康状态。有限取值用 Enum，不用裸字符串。"""

    OK = "ok"
    DEGRADED = "degraded"


class HealthResponse(BaseModel):
    """GET /v1/health 的响应。"""

    status: ServiceStatus
    frontend_ready: bool = Field(
        description="前端构建产物（dist/index.html）是否存在且可读"
    )


class VersionResponse(BaseModel):
    """GET /v1/version 的响应。

    standards_version 来自 ai-engineering-standards 的 VERSION，用于跨空间统一记录规范版本；
    app_version 是本工具集版本。后端不读取也不返回任何用户数据。
    """

    app_version: str
    standards_version: str
    zero_knowledge: bool = Field(
        default=True,
        description="标识后端从不接触明文、密钥或密文；恒为 true",
    )


class ErrorResponse(BaseModel):
    """统一错误响应形状。"""

    error: str = Field(description="机器可读错误码")
    message: str = Field(description="可读信息，不含内部细节")
    request_id: str | None = Field(default=None, description="可选请求关联 ID")


# HTTP 状态码 → 机器可读错误码（用于 FastAPI 默认异常的兜底摊平）
APP_ERROR_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


# --------------------------------------------------------------------------- #
# 公共配置表契约（多工具共享）
# 注意：这里没有 user_id 字段。身份只来自鉴权层，客户端无法指定归属用户，
# 从根本上杜绝越权写入/读取他人配置。
# --------------------------------------------------------------------------- #

TOOL_ID_PATTERN = r"^[a-z][a-z0-9_-]{0,63}$"
KEY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"


class ConfigPutRequest(BaseModel):
    """PUT /v1/configs/{tool_id}/{key} 请求体。

    value 是不透明密文 blob（后端不解析、不解密、原样存取）。
    expected_revision：乐观锁期望版本；首次创建用 0，更新用当前 revision。
    schema_version：value 内部结构的版本（前端演进用），与 revision 正交；默认 1。
    updated_by_device：最近写入的设备/客户端标识，明文元数据，可选。
    """

    value: object = Field(description="不透明 JSON 值，通常为前端加密后的密文 blob")
    expected_revision: int = Field(ge=0, description="乐观锁期望版本；首次写入为 0")
    schema_version: int = Field(default=1, ge=1, description="value 内部结构版本，默认 1")
    updated_by_device: str | None = Field(
        default=None, max_length=128, description="最近写入设备标识（明文元数据，可选）"
    )


class ConfigRecordResponse(BaseModel):
    """单条配置响应。"""

    tool_id: str
    key: str
    value: object
    revision: int = Field(ge=1, description="当前并发版本，供下次 CAS 使用")
    schema_version: int = Field(default=1, ge=1, description="value 内部结构版本，与 revision 正交")
    updated_by_device: str | None = None
    created_at: str
    updated_at: str
    deleted_at: str | None = None
    etag: str = Field(description="形如 W/\"<revision>\"，用于 If-Match")


# --------------------------------------------------------------------------- #
# 工具注册表契约（全局元数据，非用户数据）
# --------------------------------------------------------------------------- #


class ToolRecordResponse(BaseModel):
    """单个工具的注册信息，可安全下发给已认证前端。"""

    tool_id: str
    name: str
    icon: str
    description: str
    enabled: bool
    sort_order: int
    default_max_keys: int | None = Field(default=None, description="NULL 表示沿用全局默认")
    default_max_value_bytes: int | None = Field(default=None, description="NULL 表示沿用全局默认")
    created_at: str
    updated_at: str


class ToolListResponse(BaseModel):
    """工具清单响应。"""

    items: list[ToolRecordResponse]
    count: int


class ConfigListResponse(BaseModel):
    """列表响应。"""

    tool_id: str
    items: list[ConfigRecordResponse]
    count: int


class ConflictDetail(BaseModel):
    """409 冲突详情：告诉客户端当前版本，便于重试或提示用户。"""

    expected: int
    actual: int
    hint: str = "资源已被其他端更新，请拉取最新版本后重试"


class QuotaResponse(BaseModel):
    """单用户单工具配额使用情况。"""

    tool_id: str
    key_count: int
    max_keys: int
    max_value_bytes: int


class AuthModeResponse(BaseModel):
    """GET /v1/auth/mode：暴露当前鉴权模式与风险提示。"""

    mode: str
    secure: bool = Field(description="dev/stub 为 false；logto 且已配置为 true")
    logto_configured: bool
    warning: str | None = None
