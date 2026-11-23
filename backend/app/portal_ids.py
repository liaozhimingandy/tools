"""Also Apps 门户：UUIDv7 主键生成与 UTC 时间工具。

Python 3.13 尚未内置 uuid.uuid7()（3.14 才有），这里按 RFC 9562 自行实现，
与 sql/004_apps_portal.sql 的 PG uuidv7() server_default 双保险：
应用侧先生成时间有序 UUID，DB 侧仅在应用未给值时兜底。

时间约定：数据库一律 TIMESTAMPTZ（UTC 时刻）；Python 侧用 aware UTC，
对外 JSON 以 'Z' 结尾；前端展示时转本地时区。
"""

from __future__ import annotations

import os
import secrets
import threading
import time
import uuid
from datetime import datetime, timezone

_LOCK = threading.Lock()
_last_ms = 0
_seq = 0
_SEQ_MAX = 0xFFF  # rand_a 12 位
_TS_MASK = (1 << 48) - 1
_RAND_B_MASK = (1 << 62) - 1


def uuid7() -> uuid.UUID:
    """生成 RFC 9562 UUIDv7：前 48 位毫秒时间戳，同毫秒内 12 位计数器保序。"""
    global _last_ms, _seq
    with _LOCK:
        now_ms = int(time.time() * 1000)
        if now_ms > _last_ms:
            _last_ms, _seq = now_ms, 0
        else:
            _seq += 1
            if _seq > _SEQ_MAX:
                _last_ms += 1
                _seq = 0
        ts_ms, seq = _last_ms, _seq
    rand_b = int.from_bytes(os.urandom(8), "big") & _RAND_B_MASK
    value = (ts_ms & _TS_MASK) << 80
    value |= 0x7 << 76          # version 7
    value |= seq << 64          # rand_a
    value |= 0b10 << 62         # RFC 4122 variant
    value |= rand_b
    return uuid.UUID(int=value)


def utcnow() -> datetime:
    """返回 tz-aware UTC 时间；禁止 datetime.now() 的 naive 歧义。"""
    return datetime.now(timezone.utc)


def iso_utc(value: datetime | None) -> str | None:
    """序列化为带 Z 的 UTC ISO 字符串；None 原样返回。"""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def new_id_str() -> str:
    """字符串形式的 UUIDv7，便于 dataclass 与 JSON 直接传递。"""
    return str(uuid7())


def random_token(nbytes: int = 16) -> str:
    """生成不可预测的令牌（目前供种子/测试补全占位，不用于认证）。"""
    return secrets.token_urlsafe(nbytes)
