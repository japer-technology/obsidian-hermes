"""Loopback-only HTTP transport for the read-only control-room contract."""

from __future__ import annotations

import hmac
import ipaddress
import json
import os
import socket
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from .ports import JsonObject
from .snapshot import ControlRoomSnapshotAssembler


class ResponseTooLargeError(RuntimeError):
    """Raised before a response can exceed its configured byte budget."""


class ControlRoomApi:
    """Serialize bounded v1 DTOs independently of the HTTP adapter."""

    def __init__(
        self,
        assembler: ControlRoomSnapshotAssembler,
        *,
        bearer_token: str | None = None,
    ) -> None:
        if bearer_token is not None:
            if not bearer_token or len(bearer_token) > 4_096:
                raise ValueError("bearer token must contain between 1 and 4096 characters")
            if any(ord(character) < 0x20 or ord(character) == 0x7F for character in bearer_token):
                raise ValueError("bearer token must not contain control characters")
        self._assembler = assembler
        self._bearer_token = bearer_token

    @property
    def auth_required(self) -> bool:
        return self._bearer_token is not None

    def authorized(self, authorization: str | None) -> bool:
        if self._bearer_token is None:
            return True
        if authorization is None:
            return False
        scheme, separator, supplied = authorization.partition(" ")
        if not separator or scheme.casefold() != "bearer":
            return False
        return hmac.compare_digest(supplied, self._bearer_token)

    def _encode(self, value: JsonObject) -> bytes:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > self._assembler.limits.max_response_bytes:
            raise ResponseTooLargeError("control-room response exceeded its byte budget")
        return encoded

    def snapshot(self) -> bytes:
        return self._encode(self._assembler.assemble())

    def health(self) -> bytes:
        return self._encode(self._assembler.health(auth_required=self.auth_required))


class _ControlRoomRequestHandler(BaseHTTPRequestHandler):
    server_version = "ObsidianHermesControlRoom/1"
    sys_version = ""

    @property
    def api(self) -> ControlRoomApi:
        server = self.server
        if not isinstance(server, ControlRoomServer):
            raise RuntimeError("control-room handler requires ControlRoomServer")
        return server.control_room_api

    def log_message(self, format: str, *args: Any) -> None:
        # Avoid leaking bearer tokens or vault-derived paths through the
        # standard library's request logger. Host applications can add a
        # structured, redacted audit sink around the server.
        return

    def _send_json(self, status: HTTPStatus, body: bytes, *, include_body: bool = True) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    @staticmethod
    def _error(code: str, message: str) -> bytes:
        return json.dumps(
            {"error": {"code": code, "message": message}}, separators=(",", ":")
        ).encode("utf-8")

    def _read(self, *, include_body: bool) -> None:
        if not self.api.authorized(self.headers.get("Authorization")):
            self._send_json(
                HTTPStatus.UNAUTHORIZED,
                self._error("unauthorized", "a valid bearer token is required"),
                include_body=include_body,
            )
            return

        target = urlsplit(self.path)
        if target.query or target.fragment:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                self._error("invalid_target", "query strings and fragments are not supported"),
                include_body=include_body,
            )
            return
        try:
            if target.path == "/api/v1/health":
                body = self.api.health()
            elif target.path == "/api/v1/snapshot":
                body = self.api.snapshot()
            else:
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    self._error("not_found", "endpoint not found"),
                    include_body=include_body,
                )
                return
        except ResponseTooLargeError:
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                self._error("response_too_large", "snapshot exceeds the configured response limit"),
                include_body=include_body,
            )
            return
        except (OSError, RuntimeError, ValueError):
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                self._error("snapshot_unavailable", "control-room snapshot is unavailable"),
                include_body=include_body,
            )
            return
        self._send_json(HTTPStatus.OK, body, include_body=include_body)

    def do_GET(self) -> None:
        self._read(include_body=True)

    def do_HEAD(self) -> None:
        self._read(include_body=False)

    def _reject_mutation(self) -> None:
        if not self.api.authorized(self.headers.get("Authorization")):
            self._send_json(
                HTTPStatus.UNAUTHORIZED,
                self._error("unauthorized", "a valid bearer token is required"),
            )
            return
        self._send_json(
            HTTPStatus.METHOD_NOT_ALLOWED,
            self._error("read_only", "the control-room API does not accept mutations"),
        )

    def do_POST(self) -> None:
        self._reject_mutation()

    def do_PUT(self) -> None:
        self._reject_mutation()

    def do_PATCH(self) -> None:
        self._reject_mutation()

    def do_DELETE(self) -> None:
        self._reject_mutation()

    def do_OPTIONS(self) -> None:
        self._reject_mutation()


class ControlRoomServer(ThreadingHTTPServer):
    """HTTP server carrying only a read-only control-room API instance."""

    daemon_threads = True
    allow_reuse_address = False

    def __init__(
        self,
        server_address: tuple[str, int],
        api: ControlRoomApi,
        *,
        address_family: socket.AddressFamily = socket.AF_INET,
    ) -> None:
        self.address_family = address_family
        self.control_room_api = api
        super().__init__(server_address, _ControlRoomRequestHandler)


def _loopback_address(host: str) -> tuple[str, socket.AddressFamily]:
    try:
        address = ipaddress.ip_address(host)
    except ValueError as error:
        raise ValueError("control-room host must be a literal loopback IP address") from error
    if not address.is_loopback:
        raise ValueError("control-room API may only bind to a loopback address")
    family = socket.AF_INET6 if address.version == 6 else socket.AF_INET
    return str(address), family


def create_server(
    api: ControlRoomApi,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
) -> ControlRoomServer:
    """Create, but do not start, a server bound to a literal loopback IP."""

    if not 0 <= port <= 65_535:
        raise ValueError("port must be between 0 and 65535")
    bind_host, family = _loopback_address(host)
    return ControlRoomServer((bind_host, port), api, address_family=family)


def bearer_token_from_environment(
    variable: str = "OBSIDIAN_HERMES_CONTROL_ROOM_TOKEN",
) -> str | None:
    """Load an optional token at process start without adding it to config DTOs."""

    token = os.environ.get(variable)
    return token if token else None
