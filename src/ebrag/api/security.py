from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from ebrag.settings import SecuritySettings, load_settings


def is_production_environment() -> bool:
    return load_settings().project.environment.lower() in {"prod", "production"}


def public_error_detail(detail: object, *, production_message: str) -> object:
    if is_production_environment():
        return production_message
    return detail


def _is_public_request(request: Request) -> bool:
    return request.method == "OPTIONS" or request.url.path == "/health"


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        api_key: str | None,
        header_name: str,
    ) -> None:
        super().__init__(app)
        self._api_key = api_key
        self._header_name = header_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if _is_public_request(request) or not self._api_key:
            return await call_next(request)

        supplied = request.headers.get(self._header_name, "")
        if not secrets.compare_digest(supplied, self._api_key):
            return JSONResponse(
                {"detail": "Missing or invalid API key"},
                status_code=401,
                headers={"WWW-Authenticate": "ApiKey"},
            )
        return await call_next(request)


@dataclass
class _RateBucket:
    started_at: float
    count: int


def _parse_limit(limit: str) -> tuple[int, float]:
    try:
        count_text, period_text = limit.split("/", 1)
        count = int(count_text)
    except ValueError as exc:
        msg = f"Invalid rate limit format: {limit!r}"
        raise ValueError(msg) from exc

    period = period_text.strip().lower()
    seconds_by_period = {
        "second": 1.0,
        "seconds": 1.0,
        "sec": 1.0,
        "s": 1.0,
        "minute": 60.0,
        "minutes": 60.0,
        "min": 60.0,
        "m": 60.0,
        "hour": 3600.0,
        "hours": 3600.0,
        "h": 3600.0,
        "day": 86400.0,
        "days": 86400.0,
        "d": 86400.0,
    }
    if count <= 0 or period not in seconds_by_period:
        msg = f"Invalid rate limit value: {limit!r}"
        raise ValueError(msg)
    return count, seconds_by_period[period]


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or "unknown"
    if request.client is None:
        return "unknown"
    return request.client.host


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, settings: SecuritySettings) -> None:
        super().__init__(app)
        self._enabled = settings.rate_limit_enabled
        self._limits = {
            "default": _parse_limit(settings.rate_limit_default),
            "query": _parse_limit(settings.rate_limit_query),
            "ingestion": _parse_limit(settings.rate_limit_ingestion),
            "admin": _parse_limit(settings.rate_limit_admin),
        }
        self._buckets: dict[tuple[str, str], _RateBucket] = {}
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._enabled or _is_public_request(request):
            return await call_next(request)

        bucket_name = self._bucket_name(request.url.path)
        limit_count, window_seconds = self._limits[bucket_name]
        key = (_client_key(request), bucket_name)
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None or now - bucket.started_at >= window_seconds:
                bucket = _RateBucket(started_at=now, count=0)
                self._buckets[key] = bucket
            bucket.count += 1
            retry_after = max(1, int(window_seconds - (now - bucket.started_at)))
            if bucket.count > limit_count:
                return JSONResponse(
                    {"detail": "Rate limit exceeded"},
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )

        return await call_next(request)

    @staticmethod
    def _bucket_name(path: str) -> str:
        if path.startswith("/query"):
            return "query"
        if path.startswith("/papers") or path.startswith("/extraction"):
            return "ingestion"
        if path.startswith("/index") or path.startswith("/eval"):
            return "admin"
        return "default"
