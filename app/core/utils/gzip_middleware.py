# -*- coding: utf-8 -*-
"""
WSGI Gzip middleware.

Werkzeug 3.x 已移除 werkzeug.middleware.gzip，因此这里提供一个轻量实现：
- 仅在客户端支持 gzip 且响应可压缩时启用
- 默认仅压缩文本类（HTML/CSS/JS/JSON/SVG/XML）
- 避免压缩 SSE（text/event-stream）与已编码响应
"""

from __future__ import annotations

import gzip
from io import BytesIO
from typing import Callable, Iterable, List, Optional, Tuple


StartResponse = Callable[[str, List[Tuple[str, str]], Optional[BaseException]], Callable[[bytes], None]]


def _header_get(headers: List[Tuple[str, str]], name: str) -> Optional[str]:
    name_lower = name.lower()
    for k, v in headers:
        if k.lower() == name_lower:
            return v
    return None


def _header_del(headers: List[Tuple[str, str]], name: str) -> None:
    name_lower = name.lower()
    headers[:] = [(k, v) for (k, v) in headers if k.lower() != name_lower]


def _vary_add(headers: List[Tuple[str, str]], token: str) -> None:
    existing = _header_get(headers, "Vary")
    if not existing:
        headers.append(("Vary", token))
        return

    parts = [p.strip() for p in existing.split(",") if p.strip()]
    if token not in parts:
        parts.append(token)
        _header_del(headers, "Vary")
        headers.append(("Vary", ", ".join(parts)))


class GzipMiddleware:
    def __init__(
        self,
        app,
        *,
        compresslevel: int = 6,
        minimum_size: int = 500,
    ) -> None:
        self.app = app
        self.compresslevel = int(compresslevel)
        self.minimum_size = int(minimum_size)

    def __call__(self, environ, start_response: StartResponse):  # type: ignore[no-untyped-def]
        accept_encoding = (environ.get("HTTP_ACCEPT_ENCODING") or "").lower()
        if "gzip" not in accept_encoding:
            return self.app(environ, start_response)

        if (environ.get("REQUEST_METHOD") or "").upper() == "HEAD":
            return self.app(environ, start_response)

        captured: List[object] = []
        buffered: List[bytes] = []

        def _capture_start_response(status: str, response_headers: List[Tuple[str, str]], exc_info=None):
            captured[:] = [status, list(response_headers), exc_info]

            def write(data: bytes) -> None:
                if data:
                    buffered.append(data)

            return write

        app_iter = self.app(environ, _capture_start_response)

        if len(captured) != 3:
            return app_iter

        status = str(captured[0])
        response_headers: List[Tuple[str, str]] = list(captured[1])  # type: ignore[assignment]
        exc_info = captured[2]

        try:
            status_code = int(status.split(" ", 1)[0])
        except Exception:
            status_code = 200

        if status_code < 200 or status_code in (204, 304):
            return self._passthrough(start_response, status, response_headers, exc_info, buffered, app_iter)

        if _header_get(response_headers, "Content-Encoding"):
            return self._passthrough(start_response, status, response_headers, exc_info, buffered, app_iter)

        content_type = (_header_get(response_headers, "Content-Type") or "").split(";", 1)[0].strip().lower()
        if not self._is_compressible_content_type(content_type):
            return self._passthrough(start_response, status, response_headers, exc_info, buffered, app_iter)

        content_length = _header_get(response_headers, "Content-Length")
        if content_length:
            try:
                if int(content_length) < self.minimum_size:
                    return self._passthrough(start_response, status, response_headers, exc_info, buffered, app_iter)
            except Exception:
                pass

        body = self._read_body(buffered, app_iter)
        if len(body) < self.minimum_size:
            return self._passthrough(start_response, status, response_headers, exc_info, [body], [])

        gz_body = self._gzip(body)

        _header_del(response_headers, "Content-Length")
        _header_del(response_headers, "ETag")
        response_headers.append(("Content-Encoding", "gzip"))
        response_headers.append(("Content-Length", str(len(gz_body))))
        _vary_add(response_headers, "Accept-Encoding")

        start_response(status, response_headers, exc_info)
        return [gz_body]

    @staticmethod
    def _is_compressible_content_type(content_type: str) -> bool:
        if not content_type:
            return False
        if content_type.startswith("text/"):
            return content_type != "text/event-stream"
        return content_type in {
            "application/json",
            "application/javascript",
            "application/x-javascript",
            "application/xml",
            "image/svg+xml",
        }

    def _gzip(self, data: bytes) -> bytes:
        buf = BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=self.compresslevel) as gz:
            gz.write(data)
        return buf.getvalue()

    @staticmethod
    def _read_body(buffered: List[bytes], app_iter: Iterable[bytes]) -> bytes:
        chunks: List[bytes] = []
        if buffered:
            chunks.extend(buffered)

        try:
            for item in app_iter:
                if item:
                    chunks.append(item)
        finally:
            close = getattr(app_iter, "close", None)
            if callable(close):
                close()

        return b"".join(chunks)

    @staticmethod
    def _passthrough(
        start_response: StartResponse,
        status: str,
        response_headers: List[Tuple[str, str]],
        exc_info,
        buffered: List[bytes],
        app_iter: Iterable[bytes],
    ):
        start_response(status, response_headers, exc_info)

        if not buffered:
            return app_iter

        def _gen():
            try:
                for item in buffered:
                    yield item
                for item in app_iter:
                    yield item
            finally:
                close = getattr(app_iter, "close", None)
                if callable(close):
                    close()

        return _gen()

