#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Serve one exact candidate documentation tree over loopback TLS.

This helper deliberately has a narrow surface: it exposes files below the
supplied documentation root only below ``/qik-vrt/``.  It is intended for a
candidate-local browser observation, not for publication or deployment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import pathlib
import shutil
import ssl
import urllib.parse
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Sequence


URL_PREFIX = "/qik-vrt/"
HEALTH_PATH = "/qik-vrt/__qikvrt_candidate_health__"
LOOPBACK_BIND = "127.0.0.1"
STARTUP_RECEIPT_MAX_BYTES = 2048


@dataclass(frozen=True)
class CandidateTlsConfiguration:
    """Validated, non-secret configuration for the loopback server."""

    docs_root: pathlib.Path
    certificate: pathlib.Path
    key: pathlib.Path
    bind: str
    port: int
    startup_receipt: pathlib.Path | None


def parse_port(value: str) -> int:
    try:
        port = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be in 0..65535")
    return port


def parse_loopback_bind(value: str) -> str:
    if value != LOOPBACK_BIND:
        raise argparse.ArgumentTypeError(
            "only the loopback bind 127.0.0.1 is permitted"
        )
    return value


def _require_directory(value: pathlib.Path, label: str) -> pathlib.Path:
    try:
        resolved = value.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"{label} does not exist: {value}") from exc
    if not resolved.is_dir():
        raise ValueError(f"{label} is not a directory: {value}")
    return resolved


def _require_regular_file(value: pathlib.Path, label: str) -> pathlib.Path:
    try:
        resolved = value.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"{label} does not exist: {value}") from exc
    if not resolved.is_file():
        raise ValueError(f"{label} is not a regular file: {value}")
    return resolved


def validate_configuration(args: argparse.Namespace) -> CandidateTlsConfiguration:
    """Resolve and fail closed on the filesystem inputs before listening."""

    return CandidateTlsConfiguration(
        docs_root=_require_directory(args.docs_root, "docs root"),
        certificate=_require_regular_file(args.certificate, "certificate"),
        key=_require_regular_file(args.key, "key"),
        bind=parse_loopback_bind(args.bind),
        port=parse_port(str(args.port)),
        startup_receipt=(
            pathlib.Path(args.startup_receipt).resolve()
            if args.startup_receipt is not None
            else None
        ),
    )


def _candidate_segments(request_target: str) -> tuple[str, ...] | None:
    """Return a safe candidate-relative path, or ``None`` for every denial.

    The URL is decoded exactly once.  This prevents the filesystem layer from
    accidentally interpreting a second encoded traversal after validation.
    """

    parsed = urllib.parse.urlsplit(request_target)
    if not parsed.path.startswith(URL_PREFIX):
        return None
    encoded_relative = parsed.path[len(URL_PREFIX) :]
    try:
        relative = urllib.parse.unquote(
            encoded_relative, encoding="utf-8", errors="strict"
        )
    except UnicodeDecodeError:
        return None
    if "\x00" in relative or "\\" in relative or relative.startswith("/"):
        return None
    if not relative:
        return ("index.html",)
    pieces = relative.split("/")
    if pieces[-1] == "":
        pieces[-1] = "index.html"
    if any(piece in ("", ".", "..") for piece in pieces):
        return None
    return tuple(pieces)


def map_candidate_path(
    docs_root: pathlib.Path, request_target: str
) -> pathlib.Path | None:
    """Map a request target to one regular file below ``docs_root`` only."""

    segments = _candidate_segments(request_target)
    if segments is None:
        return None
    try:
        root = docs_root.resolve(strict=True)
        candidate = root.joinpath(*segments).resolve(strict=False)
        candidate.relative_to(root)
    except (OSError, ValueError):
        return None
    if not candidate.is_file():
        return None
    return candidate


def health_payload() -> dict[str, object]:
    """Return the fixed health marker without candidate-specific data."""

    return {
        "schema": "qikvrt_candidate_tls_health_v1",
        "state": "READY",
        "url_prefix": URL_PREFIX,
        "effect_ack_done": False,
        "deployment": False,
        "external_effect": "NONE",
    }


def _certificate_sha256(certificate: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with certificate.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def startup_receipt(
    configuration: CandidateTlsConfiguration, actual_port: int
) -> dict[str, object]:
    """Create a bounded, non-secret listener receipt for a local observer."""

    return {
        "schema": "qikvrt_candidate_tls_startup_receipt_v1",
        "state": "LISTENING",
        "bind": configuration.bind,
        "port": actual_port,
        "url_prefix": URL_PREFIX,
        "health_path": HEALTH_PATH,
        "docs_root": str(configuration.docs_root),
        "certificate_sha256": _certificate_sha256(configuration.certificate),
        "effect_ack_done": False,
        "deployment": False,
        "external_effect": "NONE",
    }


def serialize_bounded_receipt(receipt: dict[str, object]) -> bytes:
    """Serialize a receipt only when it stays within its explicit bound."""

    encoded = (
        json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")
    if len(encoded) > STARTUP_RECEIPT_MAX_BYTES:
        raise ValueError("startup receipt exceeds its fixed byte bound")
    return encoded


def write_startup_receipt(destination: pathlib.Path | None, receipt: dict[str, object]) -> bytes:
    """Write (when requested) and return the exact bounded receipt bytes."""

    encoded = serialize_bounded_receipt(receipt)
    if destination is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(encoded)
    return encoded


def make_handler(docs_root: pathlib.Path):
    """Create a static handler which cannot escape the candidate docs root."""

    class CandidateTlsHandler(BaseHTTPRequestHandler):
        server_version = "QIKVRT-Candidate-TLS"
        sys_version = ""

        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802 - HTTP method name
            self._serve(include_body=True)

        def do_HEAD(self) -> None:  # noqa: N802 - HTTP method name
            self._serve(include_body=False)

        def do_POST(self) -> None:  # noqa: N802 - HTTP method name
            self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)

        def _send_common_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")

        def _send_json(self, payload: dict[str, object], include_body: bool) -> None:
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
            self.send_response(HTTPStatus.OK)
            self._send_common_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            if include_body:
                self.wfile.write(encoded)

        def _serve(self, include_body: bool) -> None:
            parsed = urllib.parse.urlsplit(self.path)
            if parsed.path == HEALTH_PATH:
                self._send_json(health_payload(), include_body)
                return
            candidate = map_candidate_path(docs_root, self.path)
            if candidate is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                source = candidate.open("rb")
                source.seek(0, 2)
                size = source.tell()
                source.seek(0)
            except OSError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content_type = mimetypes.guess_type(candidate.name)[0]
            if content_type is None:
                content_type = "application/octet-stream"
            try:
                with source:
                    self.send_response(HTTPStatus.OK)
                    self._send_common_headers()
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(size))
                    self.end_headers()
                    if include_body:
                        shutil.copyfileobj(source, self.wfile)
            except (BrokenPipeError, ConnectionResetError):
                return
            except OSError:
                return

    return CandidateTlsHandler


class CandidateTlsServer(ThreadingHTTPServer):
    """A loopback-only TLS server with candidate-rooted static files."""

    allow_reuse_address = True
    daemon_threads = True


def create_server(configuration: CandidateTlsConfiguration) -> CandidateTlsServer:
    """Build the TLS listener.  The caller owns ``serve_forever`` and close."""

    handler = make_handler(configuration.docs_root)
    server = CandidateTlsServer((configuration.bind, configuration.port), handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(
        certfile=str(configuration.certificate), keyfile=str(configuration.key)
    )
    server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Serve exact candidate docs under /qik-vrt/ over loopback TLS."
    )
    parser.add_argument("--docs-root", required=True, type=pathlib.Path)
    parser.add_argument("--certificate", required=True, type=pathlib.Path)
    parser.add_argument("--key", required=True, type=pathlib.Path)
    parser.add_argument("--bind", default=LOOPBACK_BIND, type=parse_loopback_bind)
    parser.add_argument("--port", default=443, type=parse_port)
    parser.add_argument("--startup-receipt", type=pathlib.Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        configuration = validate_configuration(args)
        server = create_server(configuration)
    except (OSError, ValueError, ssl.SSLError) as exc:
        raise SystemExit(f"HOLD: candidate TLS server is not configured: {exc}") from exc

    receipt = startup_receipt(configuration, int(server.server_address[1]))
    encoded_receipt = write_startup_receipt(configuration.startup_receipt, receipt)
    print(encoded_receipt.decode("utf-8"), end="", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
